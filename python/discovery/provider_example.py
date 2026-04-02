import asyncio
import os
import signal
import sys
import logging
from dotenv import load_dotenv
from by_framework.core.discovery import ServiceRegistry
from by_framework.common.redis_client import init_redis

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

async def run_provider():
    """运行服务提供者示例。"""
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

    # 4. 初始化注册中心
    registry = ServiceRegistry()

    service_name = os.getenv("SERVICE_NAME", "demo-service")
    host = os.getenv("SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("SERVICE_PORT", 8080))
    weight = int(os.getenv("SERVICE_WEIGHT", 10))
    
    print(f"[*] 正在注册服务: {service_name} (host={host}, port={port}, weight={weight})...")

    # 2. 注册服务负载并自动启动后台心跳
    await registry.register(
        service_name=service_name,
        host=host,
        port=port,
        weight=weight,
        metadata={"version": "1.0.0", "region": "shanghai"}
    )
    
    print(f"[+] 服务 '{service_name}' 注册成功，正在运行心跳维护...")
    print("[!] 按 Ctrl+C 停止服务并注销。")

    # 3. 设置退出标志
    stop_event = asyncio.Event()

    def handle_exit():
        print("\n[!] 收到退出信号，开始注销服务...")
        stop_event.set()

    # 注册信号处理
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_exit)

    try:
        # 持续运行直到收到退出信号
        await stop_event.wait()
    finally:
        # 4. 注销服务，停止心跳
        await registry.unregister()
        print(f"[-] 服务 '{service_name}' 已成功注销。")

if __name__ == "__main__":
    try:
        asyncio.run(run_provider())
    except KeyboardInterrupt:
        pass
