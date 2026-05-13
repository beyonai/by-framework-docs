# Worker 开发指南

## GatewayWorker 基类

`GatewayWorker` 是所有自定义 Worker 的基类，你需要实现以下方法：

| 方法 | 是否必须 | 描述 |
|------|---------|------|
| `getAgentTypes()` | 是 | 返回此 Worker 能处理的 Agent 类型列表 |
| `processCommand(command, context)` | 是 | 处理具体的业务逻辑 |

## AgentContext 上下文

`AgentContext` 提供了与运行环境交互的能力：

=== "Python"

    ```python
    from by_framework import AgentContext, ArtifactEvent

    async def process_command(self, command, context: AgentContext):
        # 1. 发送流式输出
        await context.emit_chunk("正在处理...")

        # 2. 发送产物/结构化数据
        await context.emit_artifact(ArtifactEvent(url="https://example.com/result.json"))

        # 3. 获取消息 ID 和会话 ID
        msg_id = context.message_id
        session_id = context.session_id

        # 4. 调用其他 Agent (支持挂起当前任务等待返回)
        result = await context.call_agent(
            target_agent_type="translator_agent",
            content="Hello",
            wait_for_reply=True
        )
    ```

=== "Java"

    ```java
    @Override
    public Object processCommand(GatewayCommand command, AgentContext context) {
        // 1. 发送流式输出
        context.emitChunk("正在处理...");

        // 2. 获取消息 ID 和会话 ID
        String msgId = context.getCurrentMessageId();
        String sessionId = context.getSessionId();

        // 3. 调用其他 Agent
        Map<String, Object> result = context.callAgent(
            "translator_agent",  // targetAgentType
            "Hello",             // content
            true                 // waitForReply
        );

        return result;
    }
    ```

=== "TypeScript"

    ```typescript
    async processCommand(command: GatewayCommand, context: AgentContext) {
        // 1. 发送流式输出
        await context.emitChunk("正在处理...");

        // 2. 获取消息 ID 和会话 ID
        const msgId = context.messageId;
        const sessionId = context.sessionId;

        // 3. 调用其他 Agent
        const result = await context.callAgent({
            targetAgentType: "translator_agent",
            content: "Hello",
            waitForReply: true,
        });

        return result;
    }
    ```

## AgentContext API

| 方法 | 描述 |
|------|------|
| `emitChunk()` | 发送流式文本片段 |
| `emitState()` | 发送状态更新事件 |
| `emitArtifact()` | 发送产物/附件事件 |
| `askUser()` | 向用户发送等待输入请求 |
| `callAgent()` | 调用其他 Agent |
| `dispatchGroup()` | 分发任务组 |
| `getActiveWorkers()` | 获取集群中所有活跃的 worker |

## 完整示例

=== "Python"

    ```python
    import asyncio
    from by_framework import GatewayWorker, AgentContext, run_worker

    class StreamingAgent(GatewayWorker):
        def get_agent_types(self):
            return ["streaming_demo"]

        async def process_command(self, command, context: AgentContext):
            text = "这是一段流式输出的示例文本。"

            for char in text:
                await context.emit_chunk(char)
                await asyncio.sleep(0.05)

            return {"status": "done"}

    if __name__ == "__main__":
        run_worker(
            worker_class=StreamingAgent,
            worker_id="streaming-worker-01",
            redis_host="localhost",
            redis_port=6379,
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

    public class StreamingAgent extends GatewayWorker {
        public StreamingAgent(String workerId) {
            super(workerId);
        }

        @Override
        public List<String> getAgentTypes() {
            return List.of("streaming_demo");
        }

        @Override
        public Object processCommand(GatewayCommand command, AgentContext context) {
            String text = "这是一段流式输出的示例文本。";

            for (char c : text.toCharArray()) {
                context.emitChunk(String.valueOf(c));
                try { Thread.sleep(50); } catch (InterruptedException e) { break; }
            }

            return "done";
        }

        public static void main(String[] args) {
            StreamingAgent worker = new StreamingAgent("streaming-worker-01");
            WorkerRunner runner = new WorkerRunner(worker);
            runner.start();
            Runtime.getRuntime().addShutdownHook(new Thread(runner::stop));
        }
    }
    ```

=== "TypeScript"

    ```typescript
    import { GatewayWorker, AgentContext, GatewayCommand, runWorker } from '@byclaw/by-framework';

    class StreamingAgent extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["streaming_demo"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            const text = "这是一段流式输出的示例文本。";

            for (const char of text) {
                await context.emitChunk(char);
                await new Promise(resolve => setTimeout(resolve, 50));
            }

            return { status: "done" };
        }
    }

    runWorker(StreamingAgent, {
        workerId: "streaming-worker-01",
        redisHost: "localhost",
        redisPort: 6379,
    });
    ```

## 进阶能力

### 人机交互型流程

Worker 可以通过 `context.askUser(...)` 挂起执行并等待用户输入。用户回复回来后，会以 `ResumeCommand` 的形式重新进入同一个 Worker。

=== "Python"

    ```python
    from by_framework import AgentContext, AskUserEvent, GatewayWorker, ResumeCommand

    class ApprovalAgent(GatewayWorker):
        def get_agent_types(self):
            return ["approval_agent"]

        async def process_command(self, command, context: AgentContext):
            if isinstance(command, ResumeCommand):
                await context.emit_chunk(f"用户回复: {command.content}")
                return {"status": "completed"}

            return await context.ask_user(
                AskUserEvent(prompt="请确认部署窗口。")
            )
    ```

=== "Java"

    ```java
    import com.iwhaleai.byai.framework.core.protocol.*;
    import com.iwhaleai.byai.framework.worker.*;
    import java.util.List;

    public class ApprovalAgent extends GatewayWorker {
        public ApprovalAgent(String workerId) { super(workerId); }

        @Override
        public List<String> getAgentTypes() {
            return List.of("approval_agent");
        }

        @Override
        public Object processCommand(GatewayCommand command, AgentContext context) {
            if (command instanceof ResumeCommand resumeCommand) {
                context.emitChunk("用户回复: " + resumeCommand.content());
                return "completed";
            }

            return context.askUser("请确认部署窗口。");
        }
    }
    ```

=== "TypeScript"

    ```typescript
    import {
        GatewayWorker, AgentContext, GatewayCommand,
        ResumeCommand, AskUserEvent
    } from '@byclaw/by-framework';

    class ApprovalAgent extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["approval_agent"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            if (command instanceof ResumeCommand) {
                await context.emitChunk(`用户回复: ${command.content}`);
                return { status: "completed" };
            }

            return await context.askUser({ prompt: "请确认部署窗口。" });
        }
    }
    ```

### Scatter-Gather 分发

`dispatchGroup(...)` 可以一次分发多个子任务：

=== "Python"

    ```python
    tasks = [
        {"target_agent_type": "researcher", "content": "收集参考资料"},
        {"target_agent_type": "writer", "content": "起草摘要"},
    ]

    group = await context.dispatch_group(tasks, wait_for_reply=True)
    results = await context.collect_group_results(group["task_group_id"])
    ```

=== "Java"

    ```java
    List<Map<String, Object>> tasks = List.of(
        Map.of("target_agent_type", "researcher", "content", "收集参考资料"),
        Map.of("target_agent_type", "writer", "content", "起草摘要")
    );

    Map<String, Object> group = context.dispatchGroup(tasks, true);
    List<Map<String, Object>> results = context.collectGroupResults(
        (String) group.get("task_group_id")
    );
    ```

=== "TypeScript"

    ```typescript
    const group = await context.dispatchGroup({
        tasks: [
            { targetAgentType: "researcher", content: "收集参考资料" },
            { targetAgentType: "writer", content: "起草摘要" },
        ],
        waitForReply: true,
    });

    const results = await context.collectGroupResults(group.taskGroupId);
    ```
