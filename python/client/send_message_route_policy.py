"""Examples for the new GatewayClient.send_message route_policy API."""

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass

from dotenv import load_dotenv

from by_framework.client.byai_client import ByaiGatewayClient
from by_framework.common.redis_client import init_redis
from by_framework.core.availability import RoutePolicy
from by_framework.core.registry import WorkerRegistry


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("send-message-route-policy")


@dataclass(frozen=True)
class ClientConfig:
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_username: str | None = None
    redis_password: str | None = None
    fail_fast_agent_type: str = "route-policy-online-agent"
    wake_and_wait_agent_type: str = "route-policy-wakeup-agent"
    wake_and_queue_agent_type: str = "route-policy-queued-agent"
    send_anyway_agent_type: str = "route-policy-manual-agent"
    user_code: str = "demo-user"

    @classmethod
    def from_env(cls) -> "ClientConfig":
        return cls(
            redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
            redis_port=int(os.getenv("BYAI_REDIS_PORT", "6379")),
            redis_db=int(os.getenv("BYAI_REDIS_DB", "0")),
            redis_username=os.getenv("BYAI_REDIS_USERNAME"),
            redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
            fail_fast_agent_type=os.getenv(
                "BYAI_FAIL_FAST_AGENT_TYPE",
                os.getenv("BYAI_TARGET_AGENT_TYPE", "route-policy-online-agent"),
            ),
            wake_and_wait_agent_type=os.getenv(
                "BYAI_WAKE_AND_WAIT_AGENT_TYPE", "route-policy-wakeup-agent"
            ),
            wake_and_queue_agent_type=os.getenv(
                "BYAI_WAKE_AND_QUEUE_AGENT_TYPE", "route-policy-queued-agent"
            ),
            send_anyway_agent_type=os.getenv(
                "BYAI_SEND_ANYWAY_AGENT_TYPE", "route-policy-manual-agent"
            ),
            user_code=os.getenv("BYAI_USER_CODE", "demo-user"),
        )


async def send_with_policy(
    client: ByaiGatewayClient,
    *,
    target_agent_type: str,
    user_code: str,
    route_policy: str,
    content: str,
) -> None:
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    response = await client.send_message(
        target_agent_type=target_agent_type,
        session_id=session_id,
        user_code=user_code,
        content=content,
        route_policy=route_policy,
        availability_timeout_ms=10000,
    )
    logger.info(
        "route_policy=%s success=%s status=%s message_id=%s trace_id=%s error=%s",
        route_policy,
        response.success,
        response.status,
        response.message_id,
        response.trace_id,
        response.error,
    )


async def main() -> None:
    load_dotenv()
    config = ClientConfig.from_env()
    redis_client = init_redis(
        config.redis_host,
        config.redis_port,
        config.redis_db,
        config.redis_password,
        config.redis_username,
    )
    registry = WorkerRegistry(redis_client)
    client = ByaiGatewayClient(registry=registry, redis_client=redis_client)

    await send_with_policy(
        client,
        target_agent_type=config.fail_fast_agent_type,
        user_code=config.user_code,
        route_policy=RoutePolicy.FAIL_FAST,
        content="FAIL_FAST: 只有在线 Worker 存在时才会投递。",
    )

    await send_with_policy(
        client,
        target_agent_type=config.wake_and_wait_agent_type,
        user_code=config.user_code,
        route_policy=RoutePolicy.WAKE_AND_WAIT,
        content="如果当前没有在线 Worker，请先触发唤醒并等待可用后再投递。",
    )

    await send_with_policy(
        client,
        target_agent_type=config.wake_and_queue_agent_type,
        user_code=config.user_code,
        route_policy=RoutePolicy.WAKE_AND_QUEUE,
        content="如果当前没有在线 Worker，请触发唤醒并先进入 pending delivery。",
    )

    await send_with_policy(
        client,
        target_agent_type=config.send_anyway_agent_type,
        user_code=config.user_code,
        route_policy=RoutePolicy.SEND_ANYWAY,
        content="跳过在线检查，直接写入目标 agent_type 控制队列。",
    )


if __name__ == "__main__":
    asyncio.run(main())
