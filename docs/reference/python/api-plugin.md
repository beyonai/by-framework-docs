# Plugin API

## Plugin

```python
class Plugin:
    """Abstract base class for plugins."""

    def __init__(self, manifest: PluginManifest) -> None:
        self._manifest = manifest

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest
```

### 生命周期方法

```python
    async def on_worker_startup(self) -> None:
        """Worker 启动时调用"""

    async def on_worker_shutdown(self) -> None:
        """Worker 关闭时调用"""

    async def on_task_start(self, context: AgentContext) -> None:
        """任务开始时调用"""

    async def on_task_complete(
        self,
        context: AgentContext,
        result: Any,
    ) -> None:
        """任务成功完成时调用"""

    async def on_task_error(
        self,
        context: AgentContext,
        error: Exception,
    ) -> None:
        """任务出错时调用"""

    async def on_task_cancel(
        self,
        context: AgentContext,
        command: CancelTaskCommand,
    ) -> None:
        """任务取消时调用"""

    async def on_call_agent_start(
        self,
        context: AgentContext,
        command: AskAgentCommand,
    ) -> None:
        """调用其他 Agent 开始时调用"""

    async def on_call_agent_complete(
        self,
        context: AgentContext,
        command: AskAgentCommand,
        result: Any,
    ) -> None:
        """调用其他 Agent 完成时调用"""

    async def on_call_agent_error(
        self,
        context: AgentContext,
        command: AskAgentCommand,
        error: Exception,
    ) -> None:
        """调用其他 Agent 出错时调用"""

    async def register_agent_configs(
        self,
        build_context: PluginBuildContext,
    ) -> list[AgentConfig]:
        """注册 Agent 配置"""
```

## PluginManifest

```python
@dataclass
class PluginManifest:
    plugin_id: str
    version: str = "1.0.0"
    priority: int = 0
    enabled: bool = True
    name: Optional[str] = None
    description: Optional[str] = None
```

## PluginBuildContext

```python
class PluginBuildContext:
    """Plugin build context."""

    @property
    def redis_client(self) -> Redis:
        """获取 Redis 客户端"""
```

## AgentConfig

```python
@dataclass
class AgentConfig:
    agent_id: str
    name: str = ""
    description: str = ""
    tools: Optional[Dict[str, Callable]] = None
    prompts: Optional[Dict[str, str]] = None
    skills: Optional[Dict[str, Any]] = None
    callbacks: Optional[Dict[str, List[Callable]]] = None
    knowledge_bases: Optional[Dict[str, Any]] = None
    sub_agents: Optional[List[str]] = None
    extra: Optional[Dict[str, Any]] = None
    on_conflict: str = "error"
```

## PluginRegistry

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
