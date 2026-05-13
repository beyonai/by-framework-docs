# Client API

## GatewayClient

```python
class GatewayClient:
    def __init__(
        self,
        registry: Optional[WorkerRegistry] = None,
        redis_client: Optional[Redis] = None,
        interceptors: Optional[List[GatewayInterceptor]] = None,
    ) -> None:

    def add_interceptor(self, interceptor: GatewayInterceptor) -> None:
        """添加拦截器"""
```

### send_message

```python
async def send_message(
    self,
    target_agent_type: str,
    session_id: str,
    content: Any,
    user_code: str = "",
    user_name: str = "",
    action_type: str = "ASK_AGENT",
    parent_message_id: str = "",
    message_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
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
    target_agent_type: str = "",
    requested_by: str = "client",
    cancel_mode: str = "graceful",
) -> CancelTaskResponse:
    """取消指定的任务"""
```

### reload_plugins_for_agent_type

```python
async def reload_plugins_for_agent_type(
    self,
    agent_type: str,
    reason: str = "",
    reload_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """重新加载指定 Agent 类型的插件"""
```

## ByaiGatewayClient

```python
class ByaiGatewayClient(GatewayClient):
    def __init__(
        self,
        registry: Optional[WorkerRegistry] = None,
        redis_client: Optional[Redis] = None,
        interceptors: Optional[List[GatewayInterceptor]] = None,
    ) -> None:
```

## GatewayInterceptor

```python
class GatewayInterceptor:
    async def before_send(self, params: dict) -> dict:
        """发送前拦截，可修改参数"""
        return params

    async def after_send(self, response: SendMessageResponse) -> SendMessageResponse:
        """发送后拦截，可修改响应"""
        return response
```

## SendMessageResponse

```python
@dataclass
class SendMessageResponse:
    success: bool
    message_id: str
    trace_id: str
    target_worker_id: str
    timestamp: int
    status: str
    error: str = ""
    error_code: str = ""
```

## CancelTaskResponse

```python
@dataclass
class CancelTaskResponse:
    success: bool
    message_id: str
    execution_id: str
    worker_id: str
    status: str
    timestamp: int
    error: str = ""
    cancelled_count: int = 0
```
