# Plugin Hot Reload Sample

这个目录包含两个 plugin 示例：

- `logging_plugin.py` / `logging_worker.py`: 基础生命周期 hook 示例。
- `hot_reload_plugin.py` / `hot_reload_worker.py` / `hot_reload_client.py`: plugin 增量热更新示例。

## 热更新示例怎么工作

`HotReloadPlugin` 负责注册 `hot-reload-agent` 的 `AgentConfig`。配置内容来自 `hot_reload_state.json`。

启动时：

1. `register_agent_configs` 读取 `hot_reload_state.json`。
2. plugin 生成初始 `AgentConfig`。
3. 每个请求都会绑定当时的 `AgentConfigsSnapshot`。

热更新时：

1. `hot_reload_client.py` 修改 `hot_reload_state.json`。
2. client 调用 `reload_plugins_for_agent_type("hot-reload-agent")`。
3. 框架把 reload 命令广播到所有在线的 `hot-reload-agent` workers。
4. `HotReloadPlugin.reload` 只替换自己负责的 `hot-reload-agent` 配置，保留其他已有配置。
5. 新请求使用 reload 后的新 snapshot；已经开始的请求继续使用自己启动时绑定的 snapshot。

## 运行方式

先启动 Redis，然后在本目录启动 worker：

```bash
uv run python hot_reload_worker.py
```

另开一个终端触发热更新：

```bash
uv run python hot_reload_client.py
```

你会看到 worker 日志里的 `hot_reload_version` 随着 reload 增长。

如果你想手动控制版本，也可以直接编辑 `hot_reload_state.json`，然后再次运行：

```bash
uv run python hot_reload_client.py
```

## 验证

这个示例包含一个最小测试，验证 reload 只替换 plugin 自己的 `AgentConfig`：

```bash
uv run --with pytest pytest tests/test_hot_reload_plugin.py -q
```
