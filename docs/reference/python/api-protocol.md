# Protocol API

## Commands

### AskAgentCommand

```python
@dataclass
class AskAgentCommand:
    header: MessageHeader
    content: Any
    extra_payload: Optional[dict] = None
```

### CancelTaskCommand

```python
@dataclass
class CancelTaskCommand:
    header: MessageHeader
    reason: str = ""
```

### ResumeCommand

```python
@dataclass
class ResumeCommand:
    header: MessageHeader
    content: Any
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
    trace_id: Optional[str] = None
    target_agent_type: Optional[str] = None
```

## EventType 常量

| 值 | 描述 |
|----|------|
| `answerDelta` | 回答内容增量 |
| `reasoningLogDelta` | 推理或中间日志输出 |
| `appStreamResponse` | 标记流结束 |
| `taskCreate` | 任务创建相关事件 |
| `taskStop` | 任务终止相关事件 |
