import asyncio
import logging
import os
import signal

from dotenv import load_dotenv

from by_framework.common.redis_client import init_redis
from by_framework.core.discovery import ServiceRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    logger.info("加载配置文件: %s", env_path)
    load_dotenv(env_path)
else:
    logger.warning("未找到配置文件: %s, 将使用默认环境变量或系统变量", env_path)


async def run_provider_register_only() -> None:
    """Register a service instance without starting a heartbeat loop."""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    redis_password = os.getenv("REDIS_PASSWORD")
    redis_username = os.getenv("REDIS_USERNAME")

    init_redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password or None,
        username=redis_username or None,
    )

    registry = ServiceRegistry()
    service_name = os.getenv("SERVICE_NAME", "demo-service")
    host = os.getenv("SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("SERVICE_PORT", 8080))
    protocol = os.getenv("SERVICE_PROTOCOL", "http")
    path_prefix = os.getenv("SERVICE_PATH_PREFIX", "/")

    print(
        "[*] 正在以 register_only 模式注册服务: "
        f"{service_name} ({protocol}://{host}:{port}{path_prefix})"
    )

    await registry.register_only(
        service_name=service_name,
        host=host,
        port=port,
        protocol=protocol,
        path_prefix=path_prefix,
        metadata={"mode": "register_only", "version": "1.0.0"},
    )

    print("[+] 注册完成，本示例不会启动后台心跳。")
    print("[!] 这种模式适合你明确不希望由 SDK 心跳判活的场景。")
    print("[!] 按 Ctrl+C 退出并手动注销该实例。")

    stop_event = asyncio.Event()

    def handle_exit() -> None:
        print("\n[!] 收到退出信号，开始注销服务...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_exit)

    try:
        await stop_event.wait()
    finally:
        pass
        # await registry.unregister()
        # print(f"[-] 服务 '{service_name}' 已成功注销。")


if __name__ == "__main__":
    try:
        asyncio.run(run_provider_register_only())
    except KeyboardInterrupt:
        pass
