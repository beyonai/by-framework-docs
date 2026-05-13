# 快速入门

## 环境要求

=== "Python"

    - Python 3.12+
    - Redis 7.0+

=== "Java"

    - Java 21+
    - Maven 3.8+
    - Redis 7.0+

=== "TypeScript"

    - Node.js 18+
    - npm 或 yarn
    - Redis 7.0+

## 安装

=== "Python"

    ```bash
    #使用 pip
    pip install by-framework

    #使用 uv
    uv add by-framework
    ```

=== "Java"

    在 `pom.xml` 中添加依赖：

    ```xml
    <dependency>
        <groupId>com.iwhaleai.byai</groupId>
        <artifactId>by-framework</artifactId>
        <version>0.2.7</version>
    </dependency>
    ```

=== "TypeScript"

    ```bash
    npm install @byclaw/by-framework
    ```

## 启动 Redis

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

## 创建第一个 Worker

=== "Python"

    创建 `my_agent.py`：

    ```python
    import asyncio
    from by_framework import GatewayWorker, AgentContext, run_worker

    class MyAssistant(GatewayWorker):
        def get_agent_types(self):
            # 声明此 Worker 能够处理的 Agent 类型
            return ["weather_agent", "chat_agent"]

        async def process_command(self, command, context: AgentContext):
            # 发送流式文本片段
            await context.emit_chunk("正在处理您的请求...\n")

            # 模拟耗时操作
            await asyncio.sleep(0.5)

            # 更新任务状态
            await context.emit_state("thinking")

            # 从 command 的 content 中读取请求内容
            user_input = (
                command.content if isinstance(command.content, str) else str(command.content)
            )

            # 发送思考过程
            await context.emit_chunk(f"我收到了: {user_input}\n")
            await asyncio.sleep(0.3)

            # 发送最终结果
            await context.emit_chunk("这是我的回复！")

            return {
                "status": "success",
                "message": "任务完成",
                "data": {"answer": "今天天气晴朗"}
            }

    if __name__ == "__main__":
        run_worker(
            worker_class=MyAssistant,
            worker_id="worker-01",
            redis_host="localhost",
            redis_port=6379,
        )
    ```

    启动 Worker：

    ```bash
    uv run python my_agent.py
    ```

=== "Java"

    创建 `MyAssistant.java`：

    ```java
    import com.iwhaleai.byai.framework.core.protocol.AskAgentCommand;
    import com.iwhaleai.byai.framework.core.protocol.GatewayCommand;
    import com.iwhaleai.byai.framework.worker.AgentContext;
    import com.iwhaleai.byai.framework.worker.GatewayWorker;
    import com.iwhaleai.byai.framework.worker.WorkerRunner;

    import java.util.List;

    public class MyAssistant extends GatewayWorker {

        public MyAssistant(String workerId) {
            super(workerId);
        }

        @Override
        public List<String> getAgentTypes() {
            return List.of("weather_agent", "chat_agent");
        }

        @Override
        public Object processCommand(GatewayCommand command, AgentContext context) {
            AskAgentCommand askCommand = (AskAgentCommand) command;

            // 发送流式文本片段
            context.emitChunk("正在处理您的请求...\n");

            // 更新任务状态
            context.emitState("thinking");

            // 读取请求内容
            String userInput = String.valueOf(askCommand.content());

            context.emitChunk("我收到了: " + userInput + "\n");
            context.emitChunk("这是我的回复！");

            return "Task completed successfully";
        }

        public static void main(String[] args) {
            MyAssistant worker = new MyAssistant("worker-01");
            WorkerRunner runner = new WorkerRunner(worker);
            runner.start();

            Runtime.getRuntime().addShutdownHook(new Thread(runner::stop));
        }
    }
    ```

    启动 Worker：

    ```bash
    mvn compile exec:java -Dexec.mainClass="MyAssistant"
    ```

=== "TypeScript"

    创建 `my_agent.ts`：

    ```typescript
    import {
        GatewayWorker, AgentContext, GatewayCommand,
        WorkerRegistry, runWorker, AskAgentCommand
    } from '@byclaw/by-framework';

    class MyAssistant extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["weather_agent", "chat_agent"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            const askCommand = command as AskAgentCommand;

            // 发送流式文本片段
            await context.emitChunk("正在处理您的请求...\n");

            // 更新任务状态
            await context.emitState({ state: "thinking" });

            // 读取请求内容
            const userInput = String(askCommand.content);

            await context.emitChunk(`我收到了: ${userInput}\n`);
            await context.emitChunk("这是我的回复！");

            return { status: "success", content: "Task completed" };
        }
    }

    runWorker(MyAssistant, {
        workerId: "worker-01",
        redisHost: "localhost",
        redisPort: 6379,
    });
    ```

    启动 Worker：

    ```bash
    npx ts-node my_agent.ts
    ```

## 发送测试任务

=== "Python"

    创建 `send_task.py`：

    ```python
    import asyncio
    from by_framework import ByaiGatewayClient, WorkerRegistry, close_redis, init_redis

    async def send_task():
        redis = init_redis(host="localhost", port=6379)
        registry = WorkerRegistry(redis_client=redis)
        client = ByaiGatewayClient(redis_client=redis, registry=registry)

        response = await client.send_message(
            target_agent_type="weather_agent",
            session_id="session-001",
            content="今天北京天气怎么样？",
        )

        if response.success:
            print(f"任务已发送，消息 ID: {response.message_id}")
        else:
            print(f"发送失败: {response.error}")

        await close_redis()

    asyncio.run(send_task())
    ```

    ```bash
    uv run python send_task.py
    ```

=== "Java"

    创建 `SendTask.java`：

    ```java
    import com.iwhaleai.byai.framework.client.ByaiGatewayClient;
    import com.iwhaleai.byai.framework.client.GatewayClient;
    import com.iwhaleai.byai.framework.common.RedisClient;

    public class SendTask {
        public static void main(String[] args) {
            RedisClient redisClient = RedisClient.getInstance();
            ByaiGatewayClient client = new ByaiGatewayClient(redisClient);

            GatewayClient.SendResponse response = client.sendMessage(
                "weather_agent",      // targetAgentType
                "session-001",        // sessionId
                "今天北京天气怎么样？"   // content
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

    ```bash
    mvn compile exec:java -Dexec.mainClass="SendTask"
    ```

=== "TypeScript"

    创建 `send_task.ts`：

    ```typescript
    import { ByaiGatewayClient, initRedis, closeRedis } from '@byclaw/by-framework';

    async function sendTask() {
        const redis = initRedis({ host: "localhost", port: 6379 });
        const client = new ByaiGatewayClient({ redisClient: redis });

        const response = await client.sendMessage({
            targetAgentType: "weather_agent",
            sessionId: "session-001",
            content: "今天北京天气怎么样？",
        });

        if (response.success) {
            console.log(`任务已发送，消息 ID: ${response.message_id}`);
        } else {
            console.error(`发送失败: ${response.error}`);
        }

        await closeRedis();
    }

    sendTask();
    ```

    ```bash
    npx ts-node send_task.ts
    ```

## 下一步

- 深入了解 [Worker 开发](worker-guide.md)
- 学习 [插件系统](plugin-guide.md)
- 掌握 [客户端 API](client-guide.md)
