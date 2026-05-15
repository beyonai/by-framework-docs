"""Worker used by the route_policy send_message samples.

The same worker class can serve multiple agent types. In production, route
policies are a control-plane concern; business workers do not need different
implementations for FAIL_FAST, WAKE_AND_WAIT, WAKE_AND_QUEUE, or SEND_ANYWAY.
"""

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker


@dataclass(frozen=True)
class WorkerConfig:
    worker_id: str = "route-policy-worker-1"
    agent_types: tuple[str, ...] = ("route-policy-online-agent",)
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_username: str | None = None
    redis_password: str | None = None
    workspace_dir: str = "/tmp/by-framework-route-policy"
    consumer_group: str = "agent_engines"

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        raw_agent_types = os.getenv("WORKER_AGENT_TYPES") or os.getenv(
            "WORKER_AGENT_TYPE", "route-policy-online-agent"
        )
        agent_types = tuple(
            item.strip() for item in raw_agent_types.split(",") if item.strip()
        )
        return cls(
            worker_id=os.getenv("WORKER_ID", "route-policy-worker-1"),
            agent_types=agent_types or ("route-policy-online-agent",),
            redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
            redis_port=int(os.getenv("BYAI_REDIS_PORT", "6379")),
            redis_db=int(os.getenv("BYAI_REDIS_DB", "0")),
            redis_username=os.getenv("BYAI_REDIS_USERNAME"),
            redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
            workspace_dir=os.getenv(
                "WORKSPACE_DIR", "/tmp/by-framework-route-policy"
            ),
            consumer_group=os.getenv("CONSUMER_GROUP", "agent_engines"),
        )


def extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        if isinstance(content.get("content"), str):
            return content["content"]
    return str(content)


class RoutePolicyDemoWorker(GatewayWorker):
    def __init__(self, *, agent_types: tuple[str, ...], **kwargs: Any):
        super().__init__(**kwargs)
        self._agent_types = list(agent_types)

    def get_agent_types(self) -> list[str]:
        return self._agent_types

    async def process_command(
        self, command: GatewayCommand, context: AgentContext
    ) -> str:
        text = extract_text(command.content)
        agent_type = command.header.target_agent_type or ",".join(self._agent_types)
        reply = (
            f"[{self.worker_id}] agent_type={agent_type} received "
            f"message_id={command.header.message_id}: {text}"
        )
        await context.emit_chunk(reply, content_type="text")
        return reply


def main() -> None:
    load_dotenv()
    config = WorkerConfig.from_env()
    run_worker(
        RoutePolicyDemoWorker,
        worker_id=config.worker_id,
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_db=config.redis_db,
        redis_username=config.redis_username,
        redis_password=config.redis_password,
        workspace_dir=config.workspace_dir,
        consumer_group=config.consumer_group,
        agent_types=config.agent_types,
    )


if __name__ == "__main__":
    main()
