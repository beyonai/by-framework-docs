# 插件系统架构

## 插件架构总览

```mermaid
graph TB
    subgraph 注册阶段
        P1["Plugin A"] -->|registerBundle| PR["PluginRegistry"]
        P2["Plugin B"] -->|registerBundle| PR
        P3["Plugin C"] -->|registerBundle| PR
        PR -->|buildAgentConfigs| AC["AgentConfig 集合"]
    end

    subgraph 运行阶段
        Runner["WorkerRunner"] -->|onWorkerStartup| PR2["PluginRegistry"]
        PR2 -->|onTaskStart| Hooks["Plugin Hooks"]
        Hooks -->|onTaskComplete| PR2
        Hooks -->|onTaskError| PR2
        Runner -->|onWorkerShutdown| PR2
    end

    注册阶段 --> 运行阶段

    style PR fill:#fff3e0,stroke:#ef6c00
    style PR2 fill:#fff3e0,stroke:#ef6c00
```

## 核心组件关系

```mermaid
classDiagram
    class Plugin {
        <<abstract>>
        +PluginManifest manifest
        +registerAgentConfigs(ctx) AgentConfig[]
        +onWorkerStartup(worker)
        +onWorkerShutdown(worker)
        +onTaskStart(context)
        +onTaskComplete(context, result)
        +onTaskError(context, error)
        +onTaskCancel(context, command)
    }

    class PluginManifest {
        +pluginId: string
        +version: string
        +priority: int
        +enabled: boolean
    }

    class PluginBuildContext {
        +listAgentConfigs() AgentConfig[]
        +setAgentConfigs(configs)
    }

    class AgentConfig {
        +agentId: string
        +name: string
        +tools: Map
        +prompts: Map
        +skills: Map
        +extra: Map
    }

    class PluginRegistry {
        +registerBundle(plugin)
        +getPlugin(pluginId) Plugin
        +listPlugins() Plugin[]
        +buildAgentConfigs() Map
        +onTaskStart(context)
        +onTaskComplete(context, result)
        +onTaskError(context, error)
    }

    Plugin *-- PluginManifest
    Plugin ..> PluginBuildContext : uses
    Plugin ..> AgentConfig : produces
    PluginRegistry o-- Plugin : manages
```

## 插件生命周期

```mermaid
sequenceDiagram
    participant R as WorkerRunner
    participant PR as PluginRegistry
    participant P as Plugin
    participant W as GatewayWorker
    participant C as AgentContext

    Note over R: === Worker 启动 ===
    R->>PR: loadPluginsFromDir() / registerBundle()
    PR->>P: new Plugin(manifest)
    PR->>P: registerAgentConfigs(buildContext)
    P-->>PR: AgentConfig[]

    R->>PR: onWorkerStartup(worker)
    PR->>P: onWorkerStartup(worker)

    Note over R: === 任务处理 ===
    loop 每个任务
        R->>PR: onTaskStart(context)
        PR->>P: onTaskStart(context)

        R->>W: processCommand(command, context)

        alt 正常完成
            R->>PR: onTaskComplete(context, result)
            PR->>P: onTaskComplete(context, result)
        else 异常
            R->>PR: onTaskError(context, error)
            PR->>P: onTaskError(context, error)
        else 取消
            R->>PR: onTaskCancel(context, command)
            PR->>P: onTaskCancel(context, command)
        end
    end

    Note over R: === Worker 关闭 ===
    R->>PR: onWorkerShutdown(worker)
    PR->>P: onWorkerShutdown(worker)
```

## PluginRegistry API

=== "Python"

    ```python
    class PluginRegistry:
        def register_bundle(self, plugin: Plugin) -> None:
            """注册插件"""

        def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
            """获取插件"""

        def list_plugins(self) -> List[Plugin]:
            """列出所有插件"""

        def build_agent_configs(self) -> Dict[str, AgentConfig]:
            """构建所有 Agent 配置"""
    ```

=== "Java"

    ```java
    public class PluginRegistry {
        public void registerBundle(Plugin plugin)
        public Plugin getPlugin(String pluginId)
        public List<Plugin> listPlugins()
    }
    ```

=== "TypeScript"

    ```typescript
    export class PluginRegistry {
        registerBundle(plugin: Plugin): void
        getPlugin(pluginId: string): Plugin | undefined
        listPlugins(): Plugin[]
        async loadPluginsFromDir(dir: string): Promise<void>
    }
    ```

## 插件加载方式

```mermaid
graph TD
    RW["runWorker()"]

    RW -->|"pluginList"| M1["直接传入实例列表"]
    RW -->|"pluginConfigurator"| M2["回调函数配置"]
    RW -->|"pluginDir"| M3["从目录自动加载"]

    M1 --> PR["PluginRegistry.registerBundle()"]
    M2 --> PR
    M3 -->|"loadPluginsFromDir()"| PR

    PR --> Build["buildAgentConfigs()"]
    Build --> Ready["✅ 插件就绪"]
```

=== "Python"

    ```python
    # 方式一：直接传入
    run_worker(MyWorker, plugin_list=[MyPlugin()])

    # 方式二：回调配置
    run_worker(MyWorker, plugin_configurator=lambda reg: reg.register_bundle(MyPlugin()))

    # 方式三：目录加载
    run_worker(MyWorker, plugin_dir="./my_plugins")
    ```

=== "TypeScript"

    ```typescript
    // 方式一：直接传入
    runWorker(MyWorker, { pluginList: [new MyPlugin()] });

    // 方式二：回调配置
    runWorker(MyWorker, {
        pluginConfigurator: (reg) => reg.registerBundle(new MyPlugin()),
    });

    // 方式三：目录加载
    runWorker(MyWorker, { pluginDir: "./my_plugins" });
    ```

## 工具注册

=== "Python"

    ```python
    class MyPlugin(Plugin):
        async def register_agent_configs(
            self, build_context: PluginBuildContext
        ) -> list[AgentConfig]:
            return [
                AgentConfig(
                    agent_id="my_agent",
                    tools={"my_tool": self.my_tool},
                )
            ]

        async def my_tool(self, arg1: str, arg2: int) -> dict:
            return {"result": f"{arg1} - {arg2}"}
    ```

=== "Java"

    ```java
    // Java 通过 PluginRegistry 的回调机制实现工具注册
    // 具体工具通过 Worker processCommand 中实现
    ```

=== "TypeScript"

    ```typescript
    class MyPlugin extends Plugin {
        async registerAgentConfigs(
            buildContext: PluginBuildContext
        ): Promise<AgentConfig[]> {
            return [
                new AgentConfig({
                    agentId: "my_agent",
                    tools: { my_tool: this.myTool.bind(this) },
                }),
            ];
        }

        async myTool(arg1: string, arg2: number) {
            return { result: `${arg1} - ${arg2}` };
        }
    }
    ```
