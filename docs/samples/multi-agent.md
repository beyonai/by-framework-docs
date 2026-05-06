# 多 Agent 协作示例

## 架构说明

```
┌─────────────────────┐     ┌─────────────────────┐
│  Orchestrator       │     │   Sub-Worker        │
│  (协调层进程)        │     │   (执行层进程)       │
│                     │     │                     │
│  - LLM 决策         │────▶│  - 文本反转         │
│  - 调用子 Agent     │◀────│  - 计算任务         │
└─────────────────────┘     └─────────────────────┘
           │                          │
           └────────── Redis ─────────┘
```

## Sub-Worker (执行节点)

=== "Python"

    ```python
    from by_framework import GatewayWorker, AgentContext, run_worker

    class SubWorker(GatewayWorker):
        """纯粹的计算节点，负责执行具体任务"""

        def get_agent_types(self):
            return ["poet-agent", "translator-agent", "critic-agent"]

        async def process_command(self, command, context: AgentContext):
            text = str(command.content)

            if "poet" in context.current_agent_id:
                result = f"诗篇：关于 {text} 的美丽诗行"
            elif "translator" in context.current_agent_id:
                result = f"[EN] {text}"
            else:
                result = f"处理完成: {text}"

            await context.emit_chunk(result)
            return {"status": "success", "result": result}

    if __name__ == "__main__":
        run_worker(SubWorker, worker_id="sub-worker-01")
    ```

=== "Java"

    ```java
    import com.iwhaleai.byai.framework.core.protocol.*;
    import com.iwhaleai.byai.framework.worker.*;
    import java.util.List;

    public class SubWorker extends GatewayWorker {
        public SubWorker(String workerId) { super(workerId); }

        @Override
        public List<String> getAgentTypes() {
            return List.of("poet-agent", "translator-agent", "critic-agent");
        }

        @Override
        public Object processCommand(GatewayCommand command, AgentContext context) {
            String text = String.valueOf(((AskAgentCommand) command).content());
            String agentType = context.getCurrentAgentType();
            String result;

            if (agentType.contains("poet")) {
                result = "诗篇：关于 " + text + " 的美丽诗行";
            } else if (agentType.contains("translator")) {
                result = "[EN] " + text;
            } else {
                result = "处理完成: " + text;
            }

            context.emitChunk(result);
            return result;
        }

        public static void main(String[] args) {
            SubWorker worker = new SubWorker("sub-worker-01");
            new WorkerRunner(worker).start();
        }
    }
    ```

=== "TypeScript"

    ```typescript
    import {
        GatewayWorker, AgentContext, GatewayCommand,
        AskAgentCommand, runWorker
    } from 'byclaw-gateway-sdk';

    class SubWorker extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["poet-agent", "translator-agent", "critic-agent"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            const text = String((command as AskAgentCommand).content);
            const agentType = context.currentAgentType;
            let result: string;

            if (agentType.includes("poet")) {
                result = `诗篇：关于 ${text} 的美丽诗行`;
            } else if (agentType.includes("translator")) {
                result = `[EN] ${text}`;
            } else {
                result = `处理完成: ${text}`;
            }

            await context.emitChunk(result);
            return { status: "success", result };
        }
    }

    runWorker(SubWorker, { workerId: "sub-worker-01" });
    ```

## Orchestrator Agent（协调层）

协调层通过 `context.callAgent()` 调度子 Agent 并汇总结果。

=== "Python"

    ```python
    from by_framework import GatewayWorker, AgentContext, ResumeCommand, run_worker

    class OrchestratorWorker(GatewayWorker):
        """协调层 Worker：调度子 Agent 并汇总结果"""

        def get_agent_types(self):
            return ["orchestrator-agent"]

        async def process_command(self, command, context: AgentContext):
            if isinstance(command, ResumeCommand):
                # 子 Agent 返回结果后继续处理
                result = str(command.reply_data) if hasattr(command, "reply_data") else ""
                await context.emit_chunk(f"子 Agent 返回: {result}")
                return {"status": "success"}

            text = str(command.content)
            await context.emit_chunk(f"🎨 正在调度诗人 Agent...")

            # 调用子 Agent
            await context.call_agent(
                target_agent_type="poet-agent",
                content=text,
            )
            return "dispatched"

    if __name__ == "__main__":
        run_worker(OrchestratorWorker, worker_id="orchestrator-01")
    ```

=== "Java"

    ```java
    public class OrchestratorWorker extends GatewayWorker {
        public OrchestratorWorker(String workerId) { super(workerId); }

        @Override
        public List<String> getAgentTypes() {
            return List.of("orchestrator-agent");
        }

        @Override
        public Object processCommand(GatewayCommand command, AgentContext context) {
            if (command instanceof ResumeCommand resumeCommand) {
                context.emitChunk("子 Agent 返回: " + resumeCommand.replyData());
                return "success";
            }

            String text = String.valueOf(((AskAgentCommand) command).content());
            context.emitChunk("🎨 正在调度诗人 Agent...");

            context.callAgent("poet-agent", text, true);
            return "dispatched";
        }
    }
    ```

=== "TypeScript"

    ```typescript
    class OrchestratorWorker extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["orchestrator-agent"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            if (command instanceof ResumeCommand) {
                await context.emitChunk(`子 Agent 返回: ${command.replyData}`);
                return { status: "success" };
            }

            const text = String((command as AskAgentCommand).content);
            await context.emitChunk("🎨 正在调度诗人 Agent...");

            await context.callAgent({
                targetAgentType: "poet-agent",
                content: text,
                waitForReply: true,
            });

            return { status: "dispatched" };
        }
    }

    runWorker(OrchestratorWorker, { workerId: "orchestrator-01" });
    ```

## 启动方式

=== "Python"

    ```bash
    # Terminal 1: 启动执行层
    uv run python sub_worker.py

    # Terminal 2: 启动协调层
    uv run python orchestrator.py
    ```

=== "Java"

    ```bash
    # Terminal 1: 启动执行层
    java -jar sub-worker.jar

    # Terminal 2: 启动协调层
    java -jar orchestrator.jar
    ```

=== "TypeScript"

    ```bash
    # Terminal 1: 启动执行层
    npx ts-node sub_worker.ts

    # Terminal 2: 启动协调层
    npx ts-node orchestrator.ts
    ```

## 观察点

- Orchestrator 终端：显示 `🎨 正在调度诗人 Agent...`
- SubWorker 终端：收到并处理任务
- SubWorker 完成后，Orchestrator 收到 ResumeCommand 并输出最终结果
