# Registry 模块

## 核心文件

=== "Python"

    - `src/by_framework/core/extensions/registry.py` - PluginRegistry
    - `src/by_framework/client/registry.py` - WorkerRegistry

=== "Java"

    - `core/WorkerRegistry.java` - WorkerRegistry
    - `core/extensions/PluginRegistry.java` - PluginRegistry

=== "TypeScript"

    - `src/registry.ts` - WorkerRegistry
    - `src/extensions/registry.ts` - PluginRegistry

## PluginRegistry

管理插件注册和发现。

=== "Python"

    ```python
    class PluginRegistry:
        def register_bundle(self, plugin: Plugin) -> None:
            """注册插件"""

        def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
            """获取指定ID的插件"""

        def list_plugins(self) -> List[Plugin]:
            """列出所有已注册插件"""

        def build_agent_configs(self) -> Dict[str, AgentConfig]:
            """构建所有Agent配置"""

        def clear(self) -> None:
            """清空所有注册"""
    ```

=== "Java"

    ```java
    public class PluginRegistry {
        public void registerBundle(Plugin plugin)
        public Plugin getPlugin(String pluginId)
        public List<Plugin> listPlugins()
        public void onTaskStart(AgentContext context)
        public void onTaskComplete(AgentContext context, Object result)
        public void onTaskError(AgentContext context, Exception error)
    }
    ```

=== "TypeScript"

    ```typescript
    export class PluginRegistry {
        registerBundle(plugin: Plugin): void
        getPlugin(pluginId: string): Plugin | undefined
        listPlugins(): Plugin[]
        async loadPluginsFromDir(dir: string): Promise<void>
        async onTaskStart(context: AgentContext): Promise<void>
        async onTaskComplete(context: AgentContext, result: any): Promise<void>
        async onTaskError(context: AgentContext, error: Error): Promise<void>
    }
    ```

## WorkerRegistry

管理 Worker 的在线状态和心跳。

=== "Python"

    ```python
    class WorkerRegistry:
        def __init__(self, redis_client: Redis) -> None:

        async def register_worker(self, worker_id: str, agent_types: List[str]) -> None:
        async def unregister_worker(self, worker_id: str) -> None:
        async def heartbeat(self, worker_id: str) -> None:
        async def get_online_workers(self, agent_type: Optional[str] = None) -> List[Dict]:
        async def is_worker_online(self, worker_id: str) -> bool:
    ```

=== "Java"

    ```java
    public class WorkerRegistry {
        public WorkerRegistry(RedisClient redisClient)

        public void registerWorker(String workerId, List<String> agentTypes)
        public void unregisterWorker(String workerId)
        public void heartbeat(String workerId)
        public boolean isWorkerOnline(String workerId)
    }
    ```

=== "TypeScript"

    ```typescript
    export class WorkerRegistry {
        constructor(redisClient: Redis)

        async registerWorker(workerId: string, agentTypes: string[]): Promise<void>
        async unregisterWorker(workerId: string): Promise<void>
        async heartbeat(workerId: string): Promise<void>
        async isWorkerOnline(workerId: string): Promise<boolean>
    }
    ```

## Redis Key 模式

| Key | 类型 | 描述 |
|-----|------|------|
| `byai_gateway:registry:workers` | Set | 所有已知 Worker ID 集合 |
| `byai_gateway:registry:worker:online:{worker_id}` | String | Worker 心跳租约，JSON 格式（含 ip_address / last_seen），TTL 15s |
| `byai_gateway:registry:worker:lock:{worker_id}` | String | Worker 启动互斥锁（TTL 60s） |
| `byai_gateway:registry:worker:agent_types:{worker_id}` | Set | Worker 声明的 Agent type 集合 |
| `byai_gateway:registry:agent_type:workers:{agent_type}` | Set | Agent type 的成员 Worker 集合 |
| `byai_gateway:registry:worker:admin:{worker_id}` | Hash | Worker 管控状态：`lifecycle` / `reason` / `updated_at`，由 WorkerManager 写入 |
| `byai_gateway:registry:agent_type:denied:{agent_type}` | Set | 被禁止消费该 agent_type 的 Worker ID 集合 |
| `by_framework:obs:collector_lock` | String | MetricsCollector 分布式锁（SET NX），TTL = interval × 3 |
| `by_framework:obs:history` | ZSet | 历史趋势点，score = Unix ms，保留最近 2 小时 |
