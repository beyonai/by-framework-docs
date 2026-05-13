# 插件开发指南

插件是 by-framework 扩展能力的基石。你可以通过插件注册工具、提示词、技能等。

## 编写插件

=== "Python"

    ```python
    from by_framework import AgentConfig, AgentContext, Plugin, PluginBuildContext, PluginManifest
    from typing import Any

    class WeatherPlugin(Plugin):
        def __init__(self):
            super().__init__(PluginManifest(
                plugin_id="weather_plugin",
                version="1.0.0",
            ))

        async def register_agent_configs(self, build_context: PluginBuildContext) -> list[AgentConfig]:
            config = AgentConfig(
                agent_id="weather_assistant",
                tools={
                    "get_current_weather": self._get_weather,
                    "get_forecast": self._get_forecast
                },
                prompts={
                    "system_prompt": "你是一个天气助手..."
                }
            )
            return [config]

        async def _get_weather(self, city: str) -> dict[str, Any]:
            """获取当前天气"""
            return {
                "city": city,
                "temperature": 25,
                "condition": "晴",
                "humidity": 60
            }

        async def _get_forecast(self, city: str, days: int = 3) -> list[dict]:
            """获取天气预报"""
            return [
                {"day": 1, "high": 28, "low": 18, "condition": "晴"},
                {"day": 2, "high": 26, "low": 16, "condition": "多云"},
                {"day": 3, "high": 24, "low": 14, "condition": "阴"}
            ][:days]

        # 插件生命周期钩子
        async def on_task_start(self, context: AgentContext):
            """任务开始时调用"""
            print(f"任务 {context.message_id} 开始")

        async def on_task_complete(self, context: AgentContext, result: Any):
            """任务成功完成时调用"""
            print(f"任务 {context.message_id} 完成")

        async def on_task_error(self, context: AgentContext, error: Exception):
            """任务出错时调用"""
            print(f"任务 {context.message_id} 出错: {error}")
    ```

=== "Java"

    !!! info "Java 插件系统"
        Java SDK 的插件系统通过 `PluginRegistry` 实现，支持完整的生命周期钩子。

    ```java
    // Java 插件系统目前通过 PluginRegistry 进行管理
    // Worker 生命周期钩子可在 WorkerRunner 配置中注册
    // 详细 API 请参考 Java SDK 的 API 参考文档
    ```

=== "TypeScript"

    ```typescript
    import {
        Plugin, PluginManifest, PluginBuildContext,
        AgentConfig, AgentContext, GatewayWorker
    } from '@byclaw/by-framework';

    class WeatherPlugin extends Plugin {
        constructor() {
            super({
                plugin_id: "weather_plugin",
                version: "1.0.0",
            });
        }

        async registerAgentConfigs(buildContext: PluginBuildContext): Promise<AgentConfig[]> {
            return [
                new AgentConfig({
                    agentId: "weather_assistant",
                    tools: {
                        get_current_weather: this.getWeather.bind(this),
                    },
                    prompts: {
                        system_prompt: "你是一个天气助手...",
                    },
                }),
            ];
        }

        private async getWeather(city: string) {
            return { city, temperature: 25, condition: "晴" };
        }

        // 插件生命周期钩子
        async onTaskStart(context: AgentContext): Promise<void> {
            console.log(`任务 ${context.messageId} 开始`);
        }

        async onTaskComplete(context: AgentContext, result: any): Promise<void> {
            console.log(`任务 ${context.messageId} 完成`);
        }

        async onTaskError(context: AgentContext, error: Error): Promise<void> {
            console.error(`任务 ${context.messageId} 出错:`, error);
        }
    }
    ```

## 使用插件

=== "Python"

    **方式一：通过 plugin_list 参数传入**

    ```python
    from by_framework import run_worker
    from my_cool_plugin import WeatherPlugin

    run_worker(
        worker_class=MyAssistant,
        worker_id="worker-01",
        plugin_list=[WeatherPlugin()]
    )
    ```

    **方式二：通过 plugin_configurator 回调配置**

    ```python
    def configure_plugins(registry):
        registry.register_bundle(WeatherPlugin())

    run_worker(
        worker_class=MyAssistant,
        worker_id="worker-01",
        plugin_configurator=configure_plugins
    )
    ```

    **方式三：从插件目录加载模块**

    ```python
    run_worker(
        worker_class=MyAssistant,
        plugin_dir="./my_plugins"
    )
    ```

=== "Java"

    ```java
    // Java 通过 WorkerRunner 配置插件
    WorkerRunner runner = new WorkerRunner(worker);
    // 插件配置通过 Runner 内置的 PluginRegistry 管理
    runner.start();
    ```

=== "TypeScript"

    **方式一：通过 pluginList 参数传入**

    ```typescript
    import { runWorker } from '@byclaw/by-framework';

    runWorker(MyAssistant, {
        workerId: "worker-01",
        pluginList: [new WeatherPlugin()],
    });
    ```

    **方式二：通过 pluginConfigurator 回调配置**

    ```typescript
    runWorker(MyAssistant, {
        workerId: "worker-01",
        pluginConfigurator: (registry) => {
            registry.registerBundle(new WeatherPlugin());
        },
    });
    ```

    **方式三：从插件目录加载模块**

    ```typescript
    runWorker(MyAssistant, {
        workerId: "worker-01",
        pluginDir: "./my_plugins",
    });
    ```

## 生命周期钩子

插件可以实现的钩子方法：

| 钩子 | 描述 |
|------|------|
| `onWorkerStartup` | Worker 启动时调用 |
| `onWorkerShutdown` | Worker 关闭时调用 |
| `onTaskStart` | 任务开始时调用 |
| `onTaskComplete` | 任务成功完成时调用 |
| `onTaskError` | 任务出错时调用 |
| `onTaskCancel` | 任务取消时调用 |
| `onCallAgentStart` | 调用其他 Agent 开始时调用 |
| `onCallAgentComplete` | 调用其他 Agent 完成时调用 |
| `onCallAgentError` | 调用其他 Agent 出错时调用 |
