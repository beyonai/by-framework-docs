import asyncio
import logging
import os

from dotenv import load_dotenv

from by_framework.common.constants import RedisKeys
from by_framework.common.redis_client import init_redis
from by_framework.core.discovery import DiscoveryClient
from by_framework.util.discovery_http_client import DiscoveryHttpClient
from by_framework.util.http_client import RetryConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    logger.info("加载配置文件: %s", env_path)
    load_dotenv(env_path)
else:
    logger.warning("未找到配置文件: %s, 将使用默认环境变量或系统变量", env_path)


async def run_no_health_check_example() -> None:
    """Call a discovered service while explicitly disabling heartbeat checks."""
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

    discovery_client = DiscoveryClient(cache_interval=5)
    retry_config = RetryConfig(max_attempts=2, retry_on_status_codes={502, 503, 504})
    service_name = os.getenv("SERVICE_NAME", "demo-service")

    print(f"[*] 准备调用服务: {service_name}")
    print("[*] 本示例会禁用基于心跳时间的健康探测。")
    print("[*] 适用于 provider 通过 register_only 注册、不会发送心跳的场景。")

    async with DiscoveryHttpClient(
        discovery_client,
        retry_config=retry_config,
        health_threshold_ms=RedisKeys.SD_NO_HEALTH_CHECK,
    ) as client:
        try:
            response = await client.get(service_name, "/")
            if response.is_success:
                print(f"[+] GET 成功: {response.status_code}")
                print(f"    内容: {response.text[:200]}")
            else:
                print(f"[!] GET 返回非成功状态码: {response.status_code}")
        except Exception as err:  # pylint: disable=broad-exception-caught
            print(f"[!] GET 调用异常: {err}")

        try:
            response = await client.post(
                service_name,
                "/api/echo",
                json={"mode": "no-health-check", "message": "hello beyondai"},
            )
            if response.is_success:
                print(f"[+] POST 成功: {response.status_code}")
                print(f"    响应: {response.text[:200]}")
            else:
                print(f"[!] POST 返回非成功状态码: {response.status_code}")
        except Exception as err:  # pylint: disable=broad-exception-caught
            print(f"[!] POST 调用异常: {err}")

    await discovery_client.close()
    print("[-] 演示结束。")


if __name__ == "__main__":
    try:
        asyncio.run(run_no_health_check_example())
    except KeyboardInterrupt:
        pass
