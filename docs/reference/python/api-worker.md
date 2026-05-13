# Worker API (Python)

Python SDK 是框架的参考实现，提供了最完整的功能支持。

## GatewayWorker

通过继承 `GatewayWorker` 类来实现自定义 Agent。

### 核心方法

```python
from by_framework.worker import GatewayWorker, GatewayCommand, AgentContext
from by_framework.core.protocol.results import ProcessCommandResult, AgentTaskResult

class MyWorker(GatewayWorker):
    def get_agent_types(self) -> list[str]:
        """声明此 Worker 支持的 Agent 类型列表"""
        return ["python-chat-agent"]

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> ProcessCommandResult:
        """核心业务逻辑"""
        await context.emit_chunk("Hello from Python!")
        
        # 可以直接返回字符串、字典，或者结构化的 AgentTaskResult
        return AgentTaskResult(
            status="completed",
            content="处理完成",
            reply_data={"key": "value"},
            metadata={"source": "my-worker"}
        )
```

### 高级定制接口

| 方法 | 说明 |
| :--- | :--- |
| `get_context_class()` | 返回自定义的 `AgentContext` 子类，用于扩展上下文能力。 |
| `get_content_codec()` | 返回自定义的 `ContentCodec`，处理特殊格式的消息序列化。 |
| `get_data_layout_builder()` | 返回自定义的 `DataLayoutBuilder`，用于定制发射到数据流的事件结构。 |

---

## AgentContext

### 基础属性

- `session_id`: 当前会话 ID。
- `trace_id`: 全局追踪 ID。
- `message_id`: 当前处理的消息 ID。
- `parent_message_id`: 父消息 ID。

### 事件上报 (Emission)

| 方法 | 说明 |
| :--- | :--- |
| `await emit_chunk(content, event_type)` | 发送流式文本片段。默认作为 `answerDelta`，结束时如果业务有内容会发送 `finalAnswer`。 |
| `await emit_state(state)` | 更新执行状态或思考日志 (默认 `reasoningLogDelta` / `think_title`)。 |
| `await emit_artifact(url)` | 发送产物（图片、文件等）链接。 |
| `await ask_user(prompt)` | 挂起执行，向用户发起表单输入请求。 |

### Agent 间调用 (call_agent)

```python
await context.call_agent(
    target_agent_type="sub-agent",
    content="请执行子任务",
    wait_for_reply=True  # 是否挂起等待
)
```

### 任务组 (dispatch_group)

```python
result = await context.dispatch_group(
    tasks=[
        {"target_agent_type": "a", "content": "task1"},
        {"target_agent_type": "b", "content": "task2"}
    ],
    wait_for_reply=True
)
group_id = result["task_group_id"]

# 收集结果
results = await context.collect_group_results(group_id)
```

### 任务取消检查

- `is_cancel_requested()`: 返回 `bool`。
- `await check_cancelled()`: 如果已取消则抛出 `asyncio.CancelledError`。

---

## ByaiWorker

`ByaiWorker` 是 `GatewayWorker` 的预构建子类，自动解码 Byai 消息格式的 payload，适用于需要处理 `BaiYingMessage` 格式的业务逻辑。

```python
from by_framework import ByaiWorker, run_worker

class MyByaiAgent(ByaiWorker):
    def get_agent_types(self):
        return ["byai-chat-agent"]

    async def process_command(self, command, context):
        # command 已被解码为 ByaiAskAgentCommand / ByaiResumeCommand
        await context.emit_chunk("Hello from Byai!")
        return {"status": "completed"}
```

---

## run_worker

启动 Worker 的入口函数。

```python
from by_framework.worker import run_worker

run_worker(
    MyWorker,
    worker_id="py-worker-01",
    redis_host="127.0.0.1",
    redis_port=6379,
    redis_db=0,
    redis_password=None,
    redis_username=None,
    redis_max_connections=None,
    consumer_group="agent_engines",
    max_concurrency=50,
    fetch_count=10,
    plugin_list=None,
    plugin_configurator=None,
    plugin_dir=None,
    plugin_hook_timeout_seconds=None,
    plugin_log_hook_stats_on_shutdown=True,
    history_backend=None,
    storage=None,
    layout_builder=None,
)
```

### 关键参数

| 参数 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `worker_class` | `Type[GatewayWorker]` | (必填) | Worker 类。 |
| `worker_id` | `str` | `"worker-1"` | Worker 唯一标识。 |
| `redis_host` | `str` | `"localhost"` | Redis 地址。 |
| `redis_port` | `int` | `6379` | Redis 端口。 |
| `redis_db` | `int` | `0` | Redis 数据库编号。 |
| `redis_password` | `str` | `None` | Redis 密码。 |
| `redis_username` | `str` | `None` | Redis 用户名。 |
| `redis_max_connections` | `int` | `None` | Redis 连接池大小。 |
| `consumer_group` | `str` | `"agent_engines"` | Redis Stream 消费者组。 |
| `max_concurrency` | `int` | `50` | 最大并发任务数。 |
| `fetch_count` | `int` | `10` | 每次从 Stream 拉取的消息数。 |
| `plugin_list` | `List[Plugin]` | `None` | 直接传入的插件列表。 |
| `plugin_configurator` | `Callable` | `None` | 插件配置回调。 |
| `plugin_dir` | `str` | `None` | 插件目录路径。 |
| `plugin_hook_timeout_seconds` | `float` | `None` | 插件钩子超时时间。 |
| `plugin_log_hook_stats_on_shutdown` | `bool` | `True` | 关闭时打印钩子统计。 |
| `history_backend` | `BaseHistoryBackend` | `None` | 历史存储后端。 |
| `storage` | `FileStorage` | `None` | 文件存储。 |
| `layout_builder` | `DataLayoutBuilder` | `None` | 数据布局构建器。 |
