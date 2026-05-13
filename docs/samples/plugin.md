# 插件示例

## 基础插件示例

### LoggingPlugin - 带生命周期的插件

=== "Python"

    ```python
    import time
    from typing import Any
    from by_framework.core.extensions import (
        AgentConfig, Plugin, PluginBuildContext, PluginManifest,
    )
    from by_framework.worker import AgentContext
    from langchain_core.tools import tool

    class LoggingPlugin(Plugin):
        """原生 By-Framework 插件示例：自动化记录任务执行生命周期"""

        def __init__(self):
            super().__init__(PluginManifest(
                plugin_id="logging-plugin",
                version="1.0.0",
            ))
            self._start_times = {}

        async def register_agent_configs(
            self, build_context: PluginBuildContext
        ) -> list[AgentConfig]:
            @tool
            async def get_worker_stats(metrics: list = None) -> str:
                """实时获取当前 Worker 的资源指标"""
                return f"[插件执行] 成功获取指标 {metrics or 'all'}: CPU 12.4%, 内存 4.2GB"

            return [
                AgentConfig(
                    agent_id="debug-agent",
                    name="By-Framework 诊断专家",
                    tools={"get_worker_stats": get_worker_stats},
                )
            ]

        async def on_task_start(self, context: AgentContext) -> None:
            self._start_times[context.message_id] = time.time()
            print(f"[插件钩子] 任务 {context.message_id} 开始执行")

        async def on_task_complete(self, context: AgentContext, result: Any) -> None:
            start_time = self._start_times.pop(context.message_id, time.time())
            duration = time.time() - start_time
            print(f"[插件钩子] 任务 {context.message_id} 完成，耗时 {duration:.4f}s")

        async def on_worker_startup(self, worker: Any) -> None:
            print(f"[插件钩子] Worker {getattr(worker, 'worker_id', 'unknown')} 已启动")
    ```

=== "Java"

    ```java
    // Java 通过 PluginRegistry 的回调机制实现类似生命周期
    // Worker 生命周期钩子可在 WorkerRunner 配置中注册

    // 示例：在启动时注册监控回调
    WorkerRunner runner = new WorkerRunner(worker);
    runner.onTaskStart(context -> {
        System.out.println("[插件钩子] 任务 " + context.getCurrentMessageId() + " 开始执行");
    });
    runner.onTaskComplete((context, result) -> {
        System.out.println("[插件钩子] 任务 " + context.getCurrentMessageId() + " 完成");
    });
    ```

=== "TypeScript"

    ```typescript
    import {
        Plugin, PluginBuildContext, AgentConfig, AgentContext, GatewayWorker
    } from '@byclaw/by-framework';

    class LoggingPlugin extends Plugin {
        private startTimes: Map<string, number> = new Map();

        constructor() {
            super({ plugin_id: "logging-plugin", version: "1.0.0" });
        }

        async registerAgentConfigs(buildContext: PluginBuildContext): Promise<AgentConfig[]> {
            return []; // 或返回需要注入的 Agent 配置
        }

        async onTaskStart(context: AgentContext): Promise<void> {
            this.startTimes.set(context.messageId, Date.now());
            console.log(`[插件钩子] 任务 ${context.messageId} 开始执行`);
        }

        async onTaskComplete(context: AgentContext, result: any): Promise<void> {
            const startTime = this.startTimes.get(context.messageId) || Date.now();
            const duration = (Date.now() - startTime) / 1000;
            this.startTimes.delete(context.messageId);
            console.log(`[插件钩子] 任务 ${context.messageId} 完成，耗时 ${duration.toFixed(4)}s`);
        }

        async onWorkerStartup(worker: GatewayWorker): Promise<void> {
            console.log(`[插件钩子] Worker ${worker.workerId} 已启动`);
        }
    }
    ```

### 使用插件

=== "Python"

    ```python
    from by_framework import run_worker

    run_worker(
        EchoWorker,
        worker_id="echo-worker-1",
        redis_host="127.0.0.1",
        redis_port=6379,
        plugin_list=[LoggingPlugin()],  # 传入插件列表
    )
    ```

=== "Java"

    ```java
    // Java 通过 WorkerRunner 配置插件回调
    WorkerRunner runner = new WorkerRunner(worker);
    runner.start();
    ```

=== "TypeScript"

    ```typescript
    import { runWorker } from '@byclaw/by-framework';

    runWorker(EchoWorker, {
        workerId: "echo-worker-1",
        redisHost: "127.0.0.1",
        redisPort: 6379,
        pluginList: [new LoggingPlugin()],
    });
    ```

## 热更新插件示例

!!! info "Python 特有功能"
    热更新插件目前仅在 Python SDK 中支持。

```python
import json
from pathlib import Path
from by_framework.core.extensions import (
    AgentConfig, Plugin, PluginBuildContext, PluginManifest, PluginReloadContext,
)

class HotReloadPlugin(Plugin):
    """支持增量热更新的插件"""

    def __init__(self, state_file: Path = Path("hot_reload_state.json")):
        super().__init__(PluginManifest(
            plugin_id="hot-reload-demo",
            version="1.0.0",
            priority=10,
        ))
        self.state_file = state_file

    async def register_agent_configs(
        self, build_context: PluginBuildContext,
    ) -> list[AgentConfig]:
        state = self._load_state()
        return [self._build_config(state)]

    async def reload(
        self, context: PluginReloadContext,
    ) -> list[AgentConfig]:
        """热更新时替换自己的配置"""
        state = self._load_state()
        next_config = self._build_config(state)

        next_configs = []
        for config in context.current_agent_configs:
            if config.agent_id == "hot-reload-agent":
                next_configs.append(next_config)
            else:
                next_configs.append(config)

        return next_configs

    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {"version": 1, "message": "hello from plugin"}

    def _build_config(self, state: dict) -> AgentConfig:
        return AgentConfig(
            agent_id="hot-reload-agent",
            name=f"Hot Reload Demo v{state['version']}",
        )
```
