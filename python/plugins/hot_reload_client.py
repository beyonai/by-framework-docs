"""Client sample that broadcasts a plugin reload to hot-reload workers."""

from __future__ import annotations

import asyncio
import os
import uuid

from dotenv import load_dotenv

from by_framework.client.client import GatewayClient
from by_framework.common.redis_client import init_redis
from by_framework.core.registry import WorkerRegistry

from hot_reload_plugin import (
    DEFAULT_STATE_FILE,
    HOT_RELOAD_AGENT_ID,
    HotReloadState,
)

load_dotenv()


def _next_state() -> HotReloadState:
    current = HotReloadState.load(DEFAULT_STATE_FILE)
    next_version = current.version + 1
    return HotReloadState(
        version=next_version,
        message=f"hello from plugin version {next_version}",
        description=f"Reloaded hot reload plugin config v{next_version}",
    )


async def main() -> None:
    redis_host = os.getenv("BYAI_REDIS_HOST", "127.0.0.1")
    redis_port = int(os.getenv("BYAI_REDIS_PORT", "6379"))
    redis_db = int(os.getenv("BYAI_REDIS_DB", "0"))
    redis_password = os.getenv("BYAI_REDIS_PASSWORD")
    redis_username = os.getenv("BYAI_REDIS_USERNAME")

    redis_client = init_redis(
        redis_host,
        redis_port,
        redis_db,
        redis_password,
        redis_username,
    )
    registry = WorkerRegistry(redis_client)
    client = GatewayClient(registry=registry, redis_client=redis_client)

    session_id = f"hot-reload-session-{uuid.uuid4().hex[:8]}"
    before = await client.send_message(
        target_agent_type=HOT_RELOAD_AGENT_ID,
        session_id=session_id,
        content="before reload",
    )
    print(f"[client] sent before reload: success={before.success}")

    next_state = _next_state()
    next_state.write(DEFAULT_STATE_FILE)
    print(
        "[client] updated state file "
        f"path={DEFAULT_STATE_FILE} version={next_state.version}"
    )

    dispatch = await client.reload_plugins_for_agent_type(
        HOT_RELOAD_AGENT_ID,
        reason=f"demo update to version {next_state.version}",
    )
    print(f"[client] reload dispatch: {dispatch}")

    if dispatch["dispatched_count"] > 0:
        acks = await client.collect_reload_acks(
            dispatch["reload_id"],
            block_ms=3000,
            count=dispatch["dispatched_count"],
        )
        print(f"[client] reload acks: {acks}")

    after = await client.send_message(
        target_agent_type=HOT_RELOAD_AGENT_ID,
        session_id=session_id,
        content="after reload",
    )
    print(f"[client] sent after reload: success={after.success}")


if __name__ == "__main__":
    asyncio.run(main())
