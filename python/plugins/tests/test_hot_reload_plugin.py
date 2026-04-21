import asyncio
import json
import sys
from pathlib import Path

from by_framework.core.extensions import AgentConfig, PluginBuildContext

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hot_reload_plugin import HotReloadPlugin, HotReloadState


def test_hot_reload_plugin_replaces_only_its_agent_config(tmp_path):
    asyncio.run(_assert_hot_reload_plugin_replaces_only_its_agent_config(tmp_path))


async def _assert_hot_reload_plugin_replaces_only_its_agent_config(tmp_path):
    state_file = tmp_path / "hot_reload_state.json"
    state_file.write_text(
        json.dumps(
            {
                "version": 1,
                "message": "hello from v1",
                "description": "initial config",
            }
        ),
        encoding="utf-8",
    )
    plugin = HotReloadPlugin(state_file=state_file)

    initial_configs = await plugin.register_agent_configs(PluginBuildContext())

    assert initial_configs is not None
    assert [config.agent_id for config in initial_configs] == ["hot-reload-agent"]
    assert initial_configs[0].extra["hot_reload_version"] == 1

    state_file.write_text(
        json.dumps(
            {
                "version": 2,
                "message": "hello from v2",
                "description": "reloaded config",
            }
        ),
        encoding="utf-8",
    )
    unrelated_config = AgentConfig(agent_id="unrelated-agent")
    context = HotReloadState.build_reload_context(
        reload_id="reload-test",
        current_agent_configs=[initial_configs[0], unrelated_config],
    )

    reloaded_configs = await plugin.reload(context)

    assert [config.agent_id for config in reloaded_configs] == [
        "hot-reload-agent",
        "unrelated-agent",
    ]
    assert reloaded_configs[0].extra["hot_reload_version"] == 2
    assert reloaded_configs[0].extra["hot_reload_message"] == "hello from v2"
    assert reloaded_configs[1] is unrelated_config
