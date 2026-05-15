"""Agent-side call_agent route_policy sample.

Run this worker as ``route-policy-orchestrator-agent``. It receives a client
message and then calls another agent with the same control-plane route policy
API used by GatewayClient.send_message().
"""

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from by_framework.core.availability import RoutePolicy
from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from main import extract_text


@dataclass(frozen=True)
class OrchestratorConfig:
    worker_id: str = "route-policy-orchestrator-1"
    agent_type: str = "route-policy-orchestrator-agent"
    child_agent_type: str = "route-policy-child-agent"
    child_route_policy: str = RoutePolicy.WAKE_AND_WAIT
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_username: str | None = None
    redis_password: str | None = None
    workspace_dir: str = "/tmp/by-framework-route-policy"
    consumer_group: str = "agent_engines"

    @classmethod
    def from_env(cls) -> "OrchestratorConfig":
        return cls(
            worker_id=os.getenv("WORKER_ID", "route-policy-orchestrator-1"),
            agent_type=os.getenv(
                "WORKER_AGENT_TYPE", "route-policy-orchestrator-agent"
            ),
            child_agent_type=os.getenv(
                "CHILD_AGENT_TYPE", "route-policy-child-agent"
            ),
            child_route_policy=os.getenv(
                "CHILD_ROUTE_POLICY", RoutePolicy.WAKE_AND_WAIT
            ),
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


class RoutePolicyOrchestratorWorker(GatewayWorker):
    def __init__(self, *, config: OrchestratorConfig, **kwargs: Any):
        super().__init__(**kwargs)
        self._config = config

    def get_agent_types(self) -> list[str]:
        return [self._config.agent_type]

    async def process_command(
        self, command: GatewayCommand, context: AgentContext
    ) -> dict[str, Any]:
        content = extract_text(command.content)
        await context.emit_chunk(
            (
                f"[{self.worker_id}] calling {self._config.child_agent_type} "
                f"with route_policy={self._config.child_route_policy}"
            ),
            content_type="text",
        )
        result = await context.call_agent(
            target_agent_type=self._config.child_agent_type,
            content=f"child task from orchestrator: {content}",
            wait_for_reply=False,
            route_policy=self._config.child_route_policy,
            availability_timeout_ms=150000,
            priority=10,
        )
        await context.emit_chunk(f"call_agent result: {result}", content_type="text")
        return result


def main() -> None:
    load_dotenv()
    config = OrchestratorConfig.from_env()
    run_worker(
        RoutePolicyOrchestratorWorker,
        worker_id=config.worker_id,
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_db=config.redis_db,
        redis_username=config.redis_username,
        redis_password=config.redis_password,
        workspace_dir=config.workspace_dir,
        consumer_group=config.consumer_group,
        config=config,
    )


if __name__ == "__main__":
    main()
