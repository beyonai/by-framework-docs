import asyncio
import os
import logging
from dotenv import load_dotenv
from by_framework.core.discovery import DiscoveryClient
from by_framework.util.discovery_http_client import DiscoveryHttpClient
from by_framework.util.http_client import RetryConfig
from by_framework.common.redis_client import init_redis

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 1. 加载 .env 配置文件 (相对于脚本所在目录)
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    logger.info(f"加载配置文件: {env_path}")
    load_dotenv(env_path)
else:
    logger.warning(f"未找到配置文件: {env_path}, 将使用默认环境变量或系统变量")

async def run_http_discovery_example():
    """演示使用 DiscoveryHttpClient 进行服务发现调用。"""
    
    # 2. 从环境变量读取 Redis 配置
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    redis_password = os.getenv("REDIS_PASSWORD")
    redis_username = os.getenv("REDIS_USERNAME")

    logger.info(f"正在连接 Redis 进行服务发现: {redis_host}:{redis_port}")

    # 3. 初始化 Redis (服务发现依赖 Redis)
    init_redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password or None,
        username=redis_username or None
    )

    # 4. 初始化发现客户端
    # cache_interval=5 表示每 5 秒刷新一次实例缓存
    discovery_client = DiscoveryClient(cache_interval=5)
    
    # 5. 配置重试策略 (节点切换重试)
    # 当请求失败或返回 502, 503, 504 时，DiscoveryHttpClient 会自动尝试发现另一个健康的节点并重试
    retry_config = RetryConfig(
        max_attempts=3,
        retry_on_status_codes={502, 503, 504},
    )

    # 6. 使用 DiscoveryHttpClient 进行调用
    # 它可以作为异步上下文管理器使用
    async with DiscoveryHttpClient(discovery_client, retry_config=retry_config) as client:
        service_name = os.getenv("SERVICE_NAME", "springboot-sample-service")
        print(f"\n[*] 准备调用服务: {service_name}")
        
        # 演示 GET 请求
        # 注意：路径不需要包含域名/IP，DiscoveryHttpClient 会自动根据服务名填充
        print(f"\n--- 演示 GET 请求 (path: /health) ---")
        try:
            response = await client.get(service_name, "/")
            if response.is_success:
                print(f"[+] 成功! 响应状态码: {response.status_code}")
                print(f"    内容: {response.text[:200]}")
            else:
                print(f"[!] 请求失败: {response.status_code}")
        except Exception as e:
            print(f"[!] 发生异常 (可能是因为没有启动提供者): {e}")

        # 演示 POST 请求
        print(f"\n--- 演示 POST 请求 (path: /api/echo) ---")
        try:
            payload = {"message": "hello beyondai", "data": [1, 2, 3]}
            response = await client.post(service_name, "/api/echo", json=payload)
            if response.is_success:
                print(f"[+] 成功! 响应: {response.json()}")
            else:
                print(f"[!] 请求失败: {response.status_code}")
        except Exception as e:
            print(f"[!] 发生异常: {e}")

    # 7. 清理资源
    await discovery_client.close()
    print("\n[-] 演示结束。")

if __name__ == "__main__":
    try:
        asyncio.run(run_http_discovery_example())
    except KeyboardInterrupt:
        pass
