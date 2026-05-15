"""Manager-side wakeup controller sample for route_policy demos."""

import asyncio
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from by_framework.common.redis_client import init_redis
from by_framework.core.availability import (
    RoutePolicy,
    WakeupDecision,
    WakeupDecisionStatus,
    WakeupRequest,
)
from by_framework.core.delivery_gate import DeliveryGate
from by_framework.core.registry import check_agent_type_online
from by_framework.core.wakeup_controller import WakeupController


@dataclass(frozen=True)
class ControllerConfig:
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_username: str | None = None
    redis_password: str | None = None
    start_local_worker: bool = True
    ready_timeout_seconds: float = 15.0
    poll_interval_seconds: float = 0.5
    stream_start_id: str = "$"

    @classmethod
    def from_env(cls) -> "ControllerConfig":
        return cls(
            redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
            redis_port=int(os.getenv("BYAI_REDIS_PORT", "6379")),
            redis_db=int(os.getenv("BYAI_REDIS_DB", "0")),
            redis_username=os.getenv("BYAI_REDIS_USERNAME"),
            redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
            start_local_worker=os.getenv("WAKEUP_START_LOCAL_WORKER", "1")
            != "0",
            ready_timeout_seconds=float(os.getenv("WAKEUP_READY_TIMEOUT", "15")),
            poll_interval_seconds=float(os.getenv("WAKEUP_POLL_INTERVAL", "0.5")),
            stream_start_id=os.getenv("WAKEUP_STREAM_START_ID", "$"),
        )


class LocalWorkerWakeupProvider:
    """Example provider owned by the manager/client owner."""

    def __init__(self, redis, config: ControllerConfig):
        self.redis = redis
        self.config = config
        self.processes: list[asyncio.subprocess.Process] = []

    async def wakeup(self, request: WakeupRequest) -> WakeupDecision:
        if self.config.start_local_worker:
            await self._start_worker(request)

        worker_ids = await self._wait_until_online(request.target_agent_type)
        if not worker_ids:
            return WakeupDecision(
                execution_id=request.execution_id,
                target_agent_type=request.target_agent_type,
                status=WakeupDecisionStatus.FAILED,
                reason="worker did not become online before timeout",
            )

        dispatched = 0
        if request.policy == RoutePolicy.WAKE_AND_QUEUE:
            dispatched = await DeliveryGate(self.redis).dispatch_ready(
                request.execution_id
            )

        return WakeupDecision(
            execution_id=request.execution_id,
            target_agent_type=request.target_agent_type,
            status=WakeupDecisionStatus.READY,
            worker_ids=worker_ids,
            reason=f"worker ready; dispatched_pending={dispatched}",
        )

    async def _start_worker(self, request: WakeupRequest) -> None:
        worker_script = Path(__file__).with_name("main.py")
        env = dict(os.environ)
        safe_agent_type = request.target_agent_type.replace(":", "-")
        env["WORKER_ID"] = f"wakeup-{safe_agent_type}-{request.execution_id[-8:]}"
        env["WORKER_AGENT_TYPES"] = request.target_agent_type
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(worker_script),
            cwd=str(worker_script.parent),
            env=env,
        )
        self.processes.append(process)
        print(
            "started local worker",
            env["WORKER_ID"],
            "for",
            request.target_agent_type,
        )

    async def _wait_until_online(self, agent_type: str) -> list[str]:
        deadline = asyncio.get_running_loop().time() + self.config.ready_timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            online, worker_ids = await check_agent_type_online(
                self.redis, agent_type, check_active=True
            )
            if online:
                return worker_ids
            await asyncio.sleep(self.config.poll_interval_seconds)
        return []

    async def shutdown(self) -> None:
        for process in self.processes:
            if process.returncode is None:
                process.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    process.kill()


async def main() -> None:
    load_dotenv()
    config = ControllerConfig.from_env()
    redis = init_redis(
        config.redis_host,
        config.redis_port,
        config.redis_db,
        config.redis_password,
        config.redis_username,
    )
    provider = LocalWorkerWakeupProvider(redis, config)
    controller = WakeupController(redis, provider, dedupe_ttl_seconds=30)
    last_id = config.stream_start_id
    print("wakeup controller listening from", last_id)
    try:
        while True:
            last_id = await controller.run_once(last_id=last_id, block_ms=5000)
    finally:
        await provider.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
