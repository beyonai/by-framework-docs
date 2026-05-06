# Context API

## AgentContext

### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `session_id` | `str` | 会话ID |
| `trace_id` | `str` | 追踪ID |
| `message_id` | `str` | 消息ID |
| `parent_message_id` | `str` | 父消息ID |
| `current_agent_id` | `str` | 当前Agent ID |

### 方法

#### emit_chunk

```python
async def emit_chunk(
    self,
    event: Union[StreamChunkEvent, str],
    event_type: Optional[str] = None,
) -> None:
    """发送流式文本片段"""
```

#### emit_state

```python
async def emit_state(
    self,
    event: Union[StateChangeEvent, str],
    event_type: Optional[str] = None,
) -> None:
    """发送状态更新"""
```

#### emit_artifact

```python
async def emit_artifact(
    self,
    event: Union[ArtifactEvent, str],
    event_type: Optional[str] = None,
) -> None:
    """发送产物/附件"""
```

#### ask_user

```python
async def ask_user(
    self,
    event: Union[AskUserEvent, str],
) -> dict:
    """向用户发送等待输入请求"""
```

#### call_agent

```python
async def call_agent(
    self,
    target_agent_type: str,
    content: object,
    wait_for_reply: bool = True,
    **kwargs,
) -> dict:
    """调用其他Agent"""
```

#### dispatch_group

```python
async def dispatch_group(
    self,
    tasks: list[dict],
    wait_for_reply: bool = True,
    **kwargs,
) -> dict:
    """分发任务组"""
```

#### collect_group_results

```python
async def collect_group_results(
    self,
    task_group_id: str,
) -> dict:
    """收集任务组结果"""
```

#### get_active_workers

```python
async def get_active_workers(self) -> Dict[str, Any]:
    """获取集群中所有活跃的 worker"""
```
