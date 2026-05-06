# Client 模块

## 核心文件

=== "Python"

    - `src/by_framework/client/client.py` - GatewayClient
    - `src/by_framework/client/byai_client.py` - ByaiGatewayClient

=== "Java"

    - `client/GatewayClient.java` - GatewayClient
    - `client/ByaiGatewayClient.java` - ByaiGatewayClient

=== "TypeScript"

    - `src/client.ts` - GatewayClient
    - `src/byai_client.ts` - ByaiGatewayClient

## GatewayClient

向 Redis Streams 发送命令的客户端。

### 构造方法

=== "Python"

    ```python
    class GatewayClient:
        def __init__(
            self,
            redis_client: Redis,
            registry: WorkerRegistry,
        ) -> None:
    ```

=== "Java"

    ```java
    public class GatewayClient<T> {
        public GatewayClient(RedisClient redisClient)
        public GatewayClient(RedisClient redisClient, WorkerRegistry registry, List<GatewayInterceptor> interceptors)
    }
    ```

=== "TypeScript"

    ```typescript
    export class GatewayClient {
        constructor(params: {
            redisClient: Redis;
            registry?: WorkerRegistry;
            interceptors?: GatewayInterceptor[];
        })
    }
    ```

### sendMessage

=== "Python"

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
    ```

=== "Java"

    ```java
    public SendResponse sendMessage(
        String targetAgentType,
        String sessionId,
        Object content,
        String userCode, String userName,
        ActionType actionType, String targetWorkerId,
        String parentMessageId, String sourceAgentType,
        Map<String, Object> extraPayload,
        Map<String, Object> metadata
    )
    ```

=== "TypeScript"

    ```typescript
    async sendMessage(params: SendMessageParams): Promise<SendMessageResponse>
    ```

### cancelTask

=== "Python"

    ```python
    async def cancel_task(
        self, message_id: str, session_id: str, reason: str = "",
    ) -> CancelTaskResponse:
    ```

=== "Java"

    ```java
    public CancelResponse cancelTask(String messageId, String sessionId, String reason)
    ```

=== "TypeScript"

    ```typescript
    async cancelTask(params: CancelTaskParams): Promise<CancelTaskResponse>
    ```

## ByaiGatewayClient

GatewayClient 的封装，增加了 ByaiMessageInterceptor，支持更高级的消息协议。所有语言的 `ByaiGatewayClient` 都自动包含消息拦截器。
