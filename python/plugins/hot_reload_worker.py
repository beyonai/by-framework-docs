"""Worker sample that consumes the hot-reloadable plugin AgentConfig."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from hot_reload_plugin import HOT_RELOAD_AGENT_ID, HotReloadPlugin

load_dotenv()


class HotReloadWorker(GatewayWorker):
    """Worker that shows which AgentConfig snapshot each request receives."""

    def get_agent_types(self) -> list[str]:
        return [HOT_RELOAD_AGENT_ID]

    async def process_command(
        self,
        command: GatewayCommand,
        context: AgentContext,
    ) -> Any:
        config = context.agent_runtime_state.config_manager.get_config(
            HOT_RELOAD_AGENT_ID
        )
        version = config.extra["hot_reload_version"]
        message = config.extra["hot_reload_message"]
        template = config.prompts["reply_template"]
        content = getattr(command, "content", "")

        response = template.format(
            version=version,
            message=message,
            content=content,
        )
        print(
            "[hot-reload-worker] handled request "
            f"message_id={context.message_id} "
            f"agent_configs_version={context.agent_configs_version} "
            f"hot_reload_version={version}"
        )
        return response


if __name__ == "__main__":
    redis_host = os.getenv("BYAI_REDIS_HOST", "127.0.0.1")
    redis_port = int(os.getenv("BYAI_REDIS_PORT", "6379"))
    redis_db = int(os.getenv("BYAI_REDIS_DB", "0"))
    redis_password = os.getenv("BYAI_REDIS_PASSWORD")
    redis_username = os.getenv("BYAI_REDIS_USERNAME")
    worker_id = os.getenv("BYAI_WORKER_ID", "hot-reload-worker-1")

    print(
        "[hot-reload-worker] starting "
        f"worker_id={worker_id} redis={redis_host}:{redis_port}/{redis_db}"
    )
    run_worker(
        HotReloadWorker,
        worker_id=worker_id,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db,
        redis_password=redis_password,
        redis_username=redis_username,
        plugin_list=[HotReloadPlugin()],
    )
