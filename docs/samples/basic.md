# 基础示例

## 简单的 Echo Worker

### Worker 实现

=== "Python"

    ```python
    import os
    from by_framework import run_worker

    class EchoWorker:
        def get_agent_types(self):
            return ["echo_agent"]

        async def process_command(self, command, context):
            user_input = (
                command.content
                if isinstance(command.content, str)
                else str(command.content)
            )
            await context.emit_chunk(f"收到: {user_input}")
            return {"status": "success", "echo": user_input}

    if __name__ == "__main__":
        run_worker(
            EchoWorker,
            worker_id="echo-worker-1",
            redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
            redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        )
    ```

=== "Java"

    ```java
    import com.iwhaleai.byai.framework.core.protocol.AskAgentCommand;
    import com.iwhaleai.byai.framework.core.protocol.GatewayCommand;
    import com.iwhaleai.byai.framework.worker.AgentContext;
    import com.iwhaleai.byai.framework.worker.GatewayWorker;
    import com.iwhaleai.byai.framework.worker.WorkerRunner;
    import java.util.List;

    public class EchoWorker extends GatewayWorker {
        public EchoWorker(String workerId) {
            super(workerId);
        }

        @Override
        public List<String> getAgentTypes() {
            return List.of("echo_agent");
        }

        @Override
        public Object processCommand(GatewayCommand command, AgentContext context) {
            AskAgentCommand askCommand = (AskAgentCommand) command;
            String userInput = String.valueOf(askCommand.content());
            context.emitChunk("收到: " + userInput);
            return "success";
        }

        public static void main(String[] args) {
            EchoWorker worker = new EchoWorker("echo-worker-1");
            WorkerRunner runner = new WorkerRunner(worker);
            runner.start();
            Runtime.getRuntime().addShutdownHook(new Thread(runner::stop));
        }
    }
    ```

=== "TypeScript"

    ```typescript
    import {
        GatewayWorker, AgentContext, GatewayCommand,
        AskAgentCommand, runWorker
    } from '@byclaw/by-framework';

    class EchoWorker extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["echo_agent"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            const askCommand = command as AskAgentCommand;
            const userInput = String(askCommand.content);
            await context.emitChunk(`收到: ${userInput}`);
            return { status: "success", echo: userInput };
        }
    }

    runWorker(EchoWorker, {
        workerId: "echo-worker-1",
        redisHost: process.env.BYAI_REDIS_HOST || "127.0.0.1",
        redisPort: Number(process.env.BYAI_REDIS_PORT || 6379),
    });
    ```

### 发送任务客户端

=== "Python"

    ```python
    import asyncio
    import os
    from by_framework import ByaiGatewayClient, WorkerRegistry, init_redis, close_redis

    async def send():
        redis = init_redis(
            host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        )
        registry = WorkerRegistry(redis_client=redis)
        client = ByaiGatewayClient(redis_client=redis, registry=registry)

        response = await client.send_message(
            target_agent_type="echo_agent",
            session_id="session-001",
            content="Hello, World!",
        )

        print(f"Success: {response.success}")
        if response.message_id:
            print(f"Message ID: {response.message_id}")

        await close_redis()

    asyncio.run(send())
    ```

=== "Java"

    ```java
    import com.iwhaleai.byai.framework.client.ByaiGatewayClient;
    import com.iwhaleai.byai.framework.client.GatewayClient;
    import com.iwhaleai.byai.framework.common.RedisClient;

    public class SendTask {
        public static void main(String[] args) {
            RedisClient redisClient = RedisClient.getInstance();
            ByaiGatewayClient client = new ByaiGatewayClient(redisClient);

            GatewayClient.SendResponse response = client.sendMessage(
                "echo_agent", "session-001", "Hello, World!"
            );

            System.out.println("Success: " + response.isSuccess());
            if (response.getMessageId() != null) {
                System.out.println("Message ID: " + response.getMessageId());
            }

            redisClient.close();
        }
    }
    ```

=== "TypeScript"

    ```typescript
    import { ByaiGatewayClient, initRedis, closeRedis } from '@byclaw/by-framework';

    async function send() {
        const redis = initRedis({
            host: process.env.BYAI_REDIS_HOST || "127.0.0.1",
            port: Number(process.env.BYAI_REDIS_PORT || 6379),
        });
        const client = new ByaiGatewayClient({ redisClient: redis });

        const response = await client.sendMessage({
            targetAgentType: "echo_agent",
            sessionId: "session-001",
            content: "Hello, World!",
        });

        console.log(`Success: ${response.success}`);
        if (response.message_id) {
            console.log(`Message ID: ${response.message_id}`);
        }

        await closeRedis();
    }

    send();
    ```

## 带状态的 Worker

=== "Python"

    ```python
    import asyncio
    from by_framework import run_worker

    class StatefulWorker:
        def get_agent_types(self):
            return ["stateful_agent"]

        async def process_command(self, command, context):
            # 发送开始状态
            await context.emit_state("idle")
            await context.emit_chunk("开始处理...\n")

            # 处理中
            await context.emit_state("processing")
            await asyncio.sleep(1)

            # 完成
            await context.emit_state("completed")
            await context.emit_chunk("处理完成！")

            return {"status": "success"}
    ```

=== "Java"

    ```java
    public class StatefulWorker extends GatewayWorker {
        public StatefulWorker(String workerId) { super(workerId); }

        @Override
        public List<String> getAgentTypes() {
            return List.of("stateful_agent");
        }

        @Override
        public Object processCommand(GatewayCommand command, AgentContext context) {
            context.emitState("idle");
            context.emitChunk("开始处理...\n");

            context.emitState("processing");
            try { Thread.sleep(1000); } catch (InterruptedException e) { return "cancelled"; }

            context.emitState("completed");
            context.emitChunk("处理完成！");

            return "success";
        }
    }
    ```

=== "TypeScript"

    ```typescript
    class StatefulWorker extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["stateful_agent"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            await context.emitState({ state: "idle" });
            await context.emitChunk("开始处理...\n");

            await context.emitState({ state: "processing" });
            await new Promise(resolve => setTimeout(resolve, 1000));

            await context.emitState({ state: "completed" });
            await context.emitChunk("处理完成！");

            return { status: "success" };
        }
    }
    ```

## 启动多个 Worker

在不同的终端启动多个 Worker 实例，实现负载均衡：

=== "Python"

    ```bash
    # Terminal 1
    uv run python echo_worker.py --worker-id echo-worker-1

    # Terminal 2
    uv run python echo_worker.py --worker-id echo-worker-2
    ```

=== "Java"

    ```bash
    # Terminal 1
    java -jar my-worker.jar --worker-id echo-worker-1

    # Terminal 2
    java -jar my-worker.jar --worker-id echo-worker-2
    ```

=== "TypeScript"

    ```bash
    # Terminal 1
    WORKER_ID=echo-worker-1 node dist/echo_worker.mjs

    # Terminal 2
    WORKER_ID=echo-worker-2 node dist/echo_worker.mjs
    ```

多个 Worker 连接同一个 Redis Stream，Redis 会自动进行负载分配。
