# Client API

## GatewayClient

```python
class GatewayClient:
    def __init__(
        self,
        redis_client: Redis,
        registry: WorkerRegistry,
    ) -> None:
```

### send_message

```python
async def send_message(
    self,
    target_agent_type: str,
    session_id: str,
    content: Any,
    user_code: str = "",
    action_type: str = "ASK_AGENT",
    metadata: Optional[dict] = None,
    target_worker_id: Optional[str] = None,
    require_online_worker: bool = True,
) -> SendMessageResponse:
    """发送消息，返回响应对象"""
```

### cancel_task

```python
async def cancel_task(
    self,
    message_id: str,
    session_id: str,
    reason: str = "",
) -> CancelTaskResponse:
    """取消指定的任务"""
```

## ByaiGatewayClient

```python
class ByaiGatewayClient(GatewayClient):
    def __init__(
        self,
        redis_client: Redis,
        registry: WorkerRegistry,
        message_interceptor: Optional[ByaiMessageInterceptor] = None,
    ) -> None:
```

## SendMessageResponse

```python
@dataclass
class SendMessageResponse:
    success: bool
    message_id: Optional[str] = None
    target_worker_id: Optional[str] = None
    error: Optional[str] = None
```

## CancelTaskResponse

```python
@dataclass
class CancelTaskResponse:
    success: bool
    error: Optional[str] = None
```
