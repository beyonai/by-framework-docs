import asyncio
import os
from dotenv import load_dotenv
from by_framework.core.discovery import DiscoveryClient
from by_framework.common.redis_client import init_redis
import logging

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 1. 加载 .env 配置文件 (相对于脚本所在目录)
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    logger.info(f"加载配置文件: {env_path}")
    load_dotenv(env_path)
else:
    logger.warning(f"未找到配置文件: {env_path}, 将使用默认环境变量或系统变量")

async def run_consumer():
    """运行服务消费者发现示例。"""
    # 2. 从环境变量读取 Redis 配置
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    redis_password = os.getenv("REDIS_PASSWORD")
    redis_username = os.getenv("REDIS_USERNAME")

    logger.info(f"正在连接 Redis: {redis_host}:{redis_port} (DB: {redis_db}, 用户: {redis_username or 'default'}, 密码已设置: {'Yes' if redis_password else 'No'})")

    # 3. 初始化全局单例
    init_redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password or None,
        username=redis_username or None
    )

    # 4. 初始化发现客户端
    client = DiscoveryClient(cache_interval=5)

    service_name = os.getenv("SERVICE_NAME", "springboot-sample-service")
    
    # 2. 注册服务监考（开启后台刷新）
    client.watch(service_name)
    print(f"[*] 正在监听服务: {service_name}...")

    # 等待同步一次数据
    await asyncio.sleep(2)

    # 3. 第一部分：获取所有可用实例
    instances = await client.get_instances(service_name)
    if not instances:
        print("[!] 未发现可用的服务实例，请先启动 provider_example.py。")
    else:
        print(f"[+] 发现 {len(instances)} 个活跃实例:")
        for inst in instances:
            print(f"    - ID: {inst.id}, 地址: {inst.host}:{inst.port}, 权重: {inst.weight}, 元数据: {inst.metadata}")

    # 4. 第二部分：演示不同负载均衡策略
    strategies = ["random", "round-robin"]
    print("\n[负载均衡演示] 模拟 5 次服务发现请求:")
    
    for strategy in strategies:
        print(f"\n--- 策略: {strategy} ---")
        for i in range(5):
            instance = await client.discover(service_name, strategy=strategy)
            if instance:
                print(f"    第 {i+1} 次选中: {instance.id} ({instance.host}:{instance.port})")
            else:
                print(f"    第 {i+1} 次选中: 未找到实例")

    # 5. 清理后台任务
    await client.close()
    print("\n[-] 客户端已关闭。")

if __name__ == "__main__":
    asyncio.run(run_consumer())
