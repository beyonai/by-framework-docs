# Protocol API

## Commands

### AskAgentCommand

```python
@dataclass
class AskAgentCommand:
    header: MessageHeader
    content: Any
    wait_for_reply: bool = False
    extra_payload: dict = field(default_factory=dict)
```

### CancelTaskCommand

```python
@dataclass
class CancelTaskCommand:
    header: MessageHeader
    target_message_id: str
    target_execution_id: str = ""
    target_worker_id: str = ""
    reason: str = ""
    requested_by: str = ""
    cancel_mode: str = "graceful"
```

### ResumeCommand

```python
@dataclass
class ResumeCommand:
    header: MessageHeader
    content: Any
    status: str = ""
    reply_data: Any = None
    extra_payload: dict = field(default_factory=dict)
```

### ReloadPluginsCommand

```python
@dataclass
class ReloadPluginsCommand:
    action_type: ClassVar[str] = "RELOAD_PLUGINS"
    header: MessageHeader
    reload_id: str
    reason: str = ""
```

## Events

### StreamChunkEvent

```python
@dataclass
class StreamChunkEvent:
    content: str
    event_type: str = "answerDelta"
```

### StateChangeEvent

```python
@dataclass
class StateChangeEvent:
    state: str
    event_type: str = "stateChange"
```

### ArtifactEvent

```python
@dataclass
class ArtifactEvent:
    url: str
    event_type: str = "artifact"
    metadata: Optional[dict] = None
```

### AskUserEvent

```python
@dataclass
class AskUserEvent:
    prompt: str
    event_type: str = "askUser"
```

## MessageHeader

```python
@dataclass
class MessageHeader:
    message_id: str
    session_id: str
    trace_id: str
    source_agent_type: str = ""
    target_agent_type: str = ""
    parent_message_id: str = ""
    task_group_id: str = ""
    user_code: str = ""
    user_name: str = ""
    metadata: dict = field(default_factory=dict)
```

## ActionType 枚举

| 值 | 描述 |
|----|------|
| `ASK_AGENT` | 向 Agent 发送任务 |
| `RESUME` | 恢复挂起的任务 |
| `ASK_USER` | 向用户请求输入 |
| `CANCEL_TASK` | 取消任务 |
| `RELOAD_PLUGINS` | 重新加载插件 |

## EventType 常量

| 值 | 描述 |
|----|------|
| `answerDelta` | 回答内容增量 |
| `finalAnswer` | 最终回答 |
| `reasoningLogDelta` | 推理或中间日志输出 |
| `reasoningLogStart` | 推理日志开始 |
| `reasoningLogEnd` | 推理日志结束 |
| `appStreamResponse` | 标记流结束 |
| `taskCreate` | 任务创建相关事件 |
| `stepComplete` | 步骤完成 |
| `taskStop` | 任务终止相关事件 |

## SseMessageType 枚举

| 值 | 编码 | 描述 |
|----|------|------|
| `text` | 1002 | 纯文本消息 |
| `echart` | 2001 | EChart 图表 |
| `form` | 2002 | 表单 |
| `digit` | 2003 | 数字展示 |
| `iframe` | 2006 | 内嵌页面 |
| `task` | 2008 | 任务卡片 |

## SseReasonMessageType 枚举

| 值 | 编码 | 描述 |
|----|------|------|
| `think_title` | 3003 | 思考标题 |
| `think_sub_title` | 3005 | 思考子标题 |
| `think_resource` | 3004 | 思考资源 |
| `think_text` | 1002 | 思考文本 |
| `think_code_answer` | 3008 | 思考代码答案 |
| `think_code` | 3006 | 思考代码 |
| `think_code_result` | 3007 | 思考代码结果 |
| `task_finished` | 3009 | 任务完成 |
| `task_user_input` | 3013 | 任务用户输入 |
| `task_create_file` | 3010 | 任务创建文件 |
| `task_title` | 3011 | 任务标题 |
| `agent_card` | 2015 | Agent 卡片 |
| `async_card` | 2014 | 异步卡片 |
