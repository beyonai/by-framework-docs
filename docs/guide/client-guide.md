# 客户端开发指南

## ByaiGatewayClient

`ByaiGatewayClient` 是对 `GatewayClient` 的封装，默认通过共享的 Byai codec 进行消息序列化，支持更高级的消息协议。

=== "Python"

    ```python
    import asyncio
    from by_framework import ByaiGatewayClient, WorkerRegistry, close_redis, init_redis

    async def main():
        redis = init_redis(host="localhost", port=6379)
        registry = WorkerRegistry(redis_client=redis)
        client = ByaiGatewayClient(redis_client=redis, registry=registry)

        response = await client.send_message(
            target_agent_type="weather_agent",
            session_id="session_123",
            user_code="user_123",
            content="查询北京今天的天气",
        )

        if response.success:
            print(f"任务已发送，消息 ID: {response.message_id}")
        else:
            print(f"发送失败: {response.error}")

        await close_redis()

    asyncio.run(main())
    ```

=== "Java"

    ```java
    import com.iwhaleai.byai.framework.client.ByaiGatewayClient;
    import com.iwhaleai.byai.framework.client.GatewayClient;
    import com.iwhaleai.byai.framework.common.RedisClient;

    public class ClientExample {
        public static void main(String[] args) {
            RedisClient redisClient = RedisClient.getInstance();
            ByaiGatewayClient client = new ByaiGatewayClient(redisClient);

            GatewayClient.SendResponse response = client.sendMessage(
                "weather_agent",        // targetAgentType
                "session_123",          // sessionId
                "查询北京今天的天气",      // content
                "user_123",             // userCode
                "测试用户"               // userName
            );

            if (response.isSuccess()) {
                System.out.println("任务已发送，消息 ID: " + response.getMessageId());
            } else {
                System.err.println("发送失败: " + response.getError());
            }

            redisClient.close();
        }
    }
    ```

=== "TypeScript"

    ```typescript
    import { ByaiGatewayClient, initRedis, closeRedis } from 'byclaw-gateway-sdk';

    async function main() {
        const redis = initRedis({ host: "localhost", port: 6379 });
        const client = new ByaiGatewayClient({ redisClient: redis });

        const response = await client.sendMessage({
            targetAgentType: "weather_agent",
            sessionId: "session_123",
            userCode: "user_123",
            content: "查询北京今天的天气",
        });

        if (response.success) {
            console.log(`任务已发送，消息 ID: ${response.message_id}`);
        } else {
            console.error(`发送失败: ${response.error}`);
        }

        await closeRedis();
    }

    main();
    ```

## 发送路径说明

`GatewayClient.sendMessage(...)` 有两种模式：

### Agent Type 模式（默认）

- 根据 `target_agent_type` 写入 agent type stream
- 在 `require_online_worker=True` 时验证是否存在在线 worker
- 实际由哪个 worker 消费是在消费者真正读到消息时才确定的

### Direct Worker 模式

- 传入 `target_worker_id` 后直接写入 worker stream
- 适合 debug 或定向控制
- 发送前会显式检查该 worker 是否 online

## GatewayClient API

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
        """发送消息，返回响应对象"""

    async def cancel_task(
        self,
        message_id: str,
        session_id: str,
        reason: str = ""
    ) -> CancelTaskResponse:
        """取消指定的任务"""
    ```

=== "Java"

    ```java
    public SendResponse sendMessage(
        String targetAgentType,
        String sessionId,
        Object content,
        String userCode,
        String userName,
        ActionType actionType,
        String targetWorkerId,
        String parentMessageId,
        String sourceAgentType,
        Map<String, Object> extraPayload,
        Map<String, Object> metadata
    )

    public CancelResponse cancelTask(
        String messageId,
        String sessionId,
        String reason
    )
    ```

=== "TypeScript"

    ```typescript
    async sendMessage(params: {
        targetAgentType: string;
        sessionId: string;
        content: string | unknown[];
        userCode?: string;
        userName?: string;
        actionType?: string;
        targetWorkerId?: string;
        requireOnlineWorker?: boolean;
        metadata?: Record<string, unknown>;
        extraPayload?: Record<string, unknown>;
    }): Promise<SendMessageResponse>

    async cancelTask(params: {
        messageId: string;
        sessionId: string;
        reason?: string;
    }): Promise<CancelTaskResponse>
    ```

## 取消任务

=== "Python"

    ```python
    response = await client.cancel_task(
        message_id="msg_123",
        session_id="sess_456",
        reason="用户主动取消"
    )
    ```

=== "Java"

    ```java
    CancelResponse response = client.cancelTask(
        "msg_123",
        "sess_456",
        "用户主动取消"
    );
    ```

=== "TypeScript"

    ```typescript
    const response = await client.cancelTask({
        messageId: "msg_123",
        sessionId: "sess_456",
        reason: "用户主动取消",
    });
    ```
