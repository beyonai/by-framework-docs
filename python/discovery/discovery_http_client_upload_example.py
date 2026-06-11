import asyncio
import logging
import os
import tarfile
import tempfile
from pathlib import Path
from dotenv import load_dotenv

from by_framework.common.redis_client import init_redis
from by_framework.core.discovery import DiscoveryClient
from by_framework.util.discovery_http_client import DiscoveryHttpClient
from by_framework.util.http_client import RetryConfig

# 配置日志格式
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 1. 加载 .env 配置文件 (相对于脚本所在目录)
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    logger.info(f"加载配置文件: {env_path}")
    load_dotenv(env_path)
else:
    logger.warning(f"未找到配置文件: {env_path}, 将使用默认环境变量或系统变量")


async def run_http_discovery_upload_example():
    """演示使用 DiscoveryHttpClient 配合服务发现上传个人 Agent 压缩包文件 (.tar.gz)。"""

    # 2. 从环境变量读取 Redis 配置
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    redis_password = os.getenv("REDIS_PASSWORD")
    redis_username = os.getenv("REDIS_USERNAME")

    # 3. 读取 Agent 上传需要的环境变量配置
    beyond_token = os.getenv("BEYOND_TOKEN", "mock_beyond_token")
    resource_id = os.getenv("RESOURCE_ID", "mock_resource_id")
    user_code = os.getenv("USER_CODE", "mock_user_code")
    agent_file_path_str = os.getenv("AGENT_FILE_PATH")

    logger.info(f"正在连接 Redis 进行服务发现: {redis_host}:{redis_port}")

    # 初始化 Redis (服务发现依赖 Redis)
    try:
        init_redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password or None,
            username=redis_username or None,
        )
    except Exception as e:
        logger.error(f"Redis 连接初始化失败: {e}")

    # 4. 初始化发现客户端
    discovery_client = DiscoveryClient(cache_interval=5)

    # 5. 配置重试策略 (当上传失败时自动切换节点重试，并自动重置文件/流游标)
    retry_config = RetryConfig(
        max_attempts=3,
        retry_on_status_codes={502, 503, 504},
    )

    # 准备上传的 Agent 压缩包文件 (.tar.gz)
    temp_dir = tempfile.gettempdir()
    is_temp_file = False
    
    if agent_file_path_str and os.path.exists(agent_file_path_str):
        agent_file_path = Path(agent_file_path_str)
        print(f"\n[+] 使用配置的 Agent 文件：{agent_file_path}")
    else:
        # 如果没有配置或者文件不存在，在临时目录自动生成一个演示用的 .tar.gz 文件
        agent_file_path = Path(temp_dir) / "your-agent.tar.gz"
        is_temp_file = True
        
        # 临时写入一个信息文件
        info_file = Path(temp_dir) / "agent_info.txt"
        info_file.write_text("This is a demo agent package generated for testing upload.")
        
        # 打包成 .tar.gz
        with tarfile.open(agent_file_path, "w:gz") as tar:
            tar.add(info_file, arcname="agent_info.txt")
        
        # 删除临时信息文件
        info_file.unlink()
        print(f"\n[+] 自动生成临时 Agent 演示压缩包：{agent_file_path}")

    # 6. 使用 DiscoveryHttpClient 进行调用
    async with DiscoveryHttpClient(
        discovery_client, retry_config=retry_config
    ) as client:
        service_name = os.getenv("SERVICE_NAME", "by-qa-manager")
        upload_path = "/byaiService/tool/uploadPersonalAgentTarGz"
        
        print(f"\n[*] 准备上传个人 Agent 至服务: {service_name}，接口路径: {upload_path}")
        print(f"    Beyond-Token: {beyond_token[:6]}*** (length: {len(beyond_token)})" if len(beyond_token) > 6 else f"    Beyond-Token: {beyond_token}")
        print(f"    resourceId: {resource_id}")
        print(f"    userCode: {user_code}")
        print(f"    file: {agent_file_path}")

        try:
            # 根据 curl 逻辑发起 Multipart 上传
            # -H "Beyond-Token: ${TOKEN}"
            # -F "file=@/path/to/your-agent.tar.gz"
            # -F "resourceId=${RESOURCE_ID}"
            # -F "userCode=${USER_CODE}"
            response = await client.upload(
                service_name=service_name,
                path=upload_path,
                file_path=agent_file_path,
                file_field="file",  # 根据 curl，这里是 file 字段
                headers={
                    "Beyond-Token": beyond_token
                },
                form_fields={
                    "resourceId": resource_id,
                    "userCode": user_code
                },
            )
            if response.is_success:
                print(f"[+] 上传个人 Agent 成功! 状态码: {response.status_code}")
                print(f"    响应内容: {str(response.data)[:500]}")
            else:
                print(f"[!] 上传个人 Agent 失败! 状态码: {response.status_code}")
                print(f"    错误响应: {str(response.data)[:500]}")
        except Exception as e:
            print(f"[!] 上传过程中发生异常: {e}")

    # 清理临时文件
    if is_temp_file:
        try:
            if agent_file_path.exists():
                agent_file_path.unlink()
                print("\n[+] 已清理临时 Agent 演示压缩包。")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

    # 7. 清理资源
    await discovery_client.close()
    print("\n[-] 演示结束。")


if __name__ == "__main__":
    try:
        asyncio.run(run_http_discovery_upload_example())
    except KeyboardInterrupt:
        pass
