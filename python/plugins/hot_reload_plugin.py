"""Plugin hot reload sample for By-Framework.

The plugin owns one AgentConfig, `hot-reload-agent`. Its `reload` hook updates
only that config from a small JSON state file while preserving all unrelated
configs in the current snapshot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from by_framework.core.extensions import (
    AgentConfig,
    Plugin,
    PluginBuildContext,
    PluginManifest,
    PluginReloadContext,
)

HOT_RELOAD_AGENT_ID = "hot-reload-agent"
DEFAULT_STATE_FILE = Path(__file__).with_name("hot_reload_state.json")


@dataclass(frozen=True)
class HotReloadState:
    """File-backed state used to build the hot-reloadable AgentConfig."""

    version: int
    message: str
    description: str

    @classmethod
    def default(cls) -> "HotReloadState":
        return cls(
            version=1,
            message="hello from plugin version 1",
            description="Initial hot reload plugin config",
        )

    @classmethod
    def load(cls, state_file: Path) -> "HotReloadState":
        if not state_file.exists():
            state = cls.default()
            state.write(state_file)
            return state

        try:
            raw = json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise ValueError(f"Invalid hot reload state file: {state_file}") from err

        return cls(
            version=int(raw.get("version", 1)),
            message=str(raw.get("message", cls.default().message)),
            description=str(raw.get("description", cls.default().description)),
        )

    def write(self, state_file: Path) -> None:
        state_file.write_text(
            json.dumps(
                {
                    "version": self.version,
                    "message": self.message,
                    "description": self.description,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def build_reload_context(
        reload_id: str,
        current_agent_configs: Iterable[AgentConfig],
    ) -> PluginReloadContext:
        """Build a minimal reload context for the sample test."""
        configs = tuple(current_agent_configs)
        return PluginReloadContext(
            plugin_id="hot-reload-demo",
            reload_id=reload_id,
            reason="test",
            current_agent_configs=configs,
            previous_stable_agent_configs=configs,
            current_version=1,
        )


class HotReloadPlugin(Plugin):
    """A plugin that demonstrates incremental AgentConfig reload."""

    def __init__(self, state_file: Path = DEFAULT_STATE_FILE):
        super().__init__(
            PluginManifest(
                plugin_id="hot-reload-demo",
                version="1.0.0",
                priority=10,
            )
        )
        self.state_file = state_file

    async def register_agent_configs(
        self,
        build_context: PluginBuildContext,
    ) -> list[AgentConfig]:
        state = HotReloadState.load(self.state_file)
        print(
            "[hot-reload-plugin] register_agent_configs "
            f"version={state.version} message={state.message!r}"
        )
        return [self._build_agent_config(state)]

    async def reload(
        self,
        context: PluginReloadContext,
    ) -> list[AgentConfig]:
        state = HotReloadState.load(self.state_file)
        next_config = self._build_agent_config(state)
        replaced = False
        next_configs: list[AgentConfig] = []

        for config in context.current_agent_configs:
            if config.agent_id == HOT_RELOAD_AGENT_ID:
                next_configs.append(next_config)
                replaced = True
            else:
                next_configs.append(config)

        if not replaced:
            next_configs.append(next_config)

        print(
            "[hot-reload-plugin] reload "
            f"reload_id={context.reload_id} from_version={context.current_version} "
            f"to_hot_reload_version={state.version}"
        )
        return next_configs

    def _build_agent_config(self, state: HotReloadState) -> AgentConfig:
        return AgentConfig(
            agent_id=HOT_RELOAD_AGENT_ID,
            name=f"Hot Reload Demo Agent v{state.version}",
            description=state.description,
            prompts={
                "system": (
                    "You are a hot reload demo agent. "
                    "Always report the version from AgentConfig.extra."
                ),
                "reply_template": (
                    "[plugin-config-v{version}] {message}; user said: {content}"
                ),
            },
            extra={
                "hot_reload_version": state.version,
                "hot_reload_message": state.message,
                "state_file": str(self.state_file),
            },
            on_conflict="overwrite",
        )
