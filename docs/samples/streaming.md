# 流式输出示例

## 字符级流式输出

=== "Python"

    ```python
    import asyncio
    from by_framework import GatewayWorker, AgentContext, run_worker

    class StreamingAgent(GatewayWorker):
        def get_agent_types(self):
            return ["streaming_demo"]

        async def process_command(self, command, context: AgentContext):
            text = "这是一段流式输出的示例文本，每个字符会逐个发送。"

            for char in text:
                await context.emit_chunk(char)
                await asyncio.sleep(0.05)  # 模拟打字效果

            return {"status": "done"}
    ```

=== "Java"

    ```java
    public class StreamingAgent extends GatewayWorker {
        public StreamingAgent(String workerId) { super(workerId); }

        @Override
        public List<String> getAgentTypes() {
            return List.of("streaming_demo");
        }

        @Override
        public Object processCommand(GatewayCommand command, AgentContext context) {
            String text = "这是一段流式输出的示例文本，每个字符会逐个发送。";

            for (char c : text.toCharArray()) {
                context.emitChunk(String.valueOf(c));
                try { Thread.sleep(50); } catch (InterruptedException e) { break; }
            }

            return "done";
        }
    }
    ```

=== "TypeScript"

    ```typescript
    class StreamingAgent extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["streaming_demo"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            const text = "这是一段流式输出的示例文本，每个字符会逐个发送。";

            for (const char of text) {
                await context.emitChunk(char);
                await new Promise(resolve => setTimeout(resolve, 50));
            }

            return { status: "done" };
        }
    }
    ```

## 带思考过程的流式输出

=== "Python"

    ```python
    import asyncio
    from by_framework import GatewayWorker, AgentContext, run_worker

    class ThinkingAgent(GatewayWorker):
        def get_agent_types(self):
            return ["thinking_agent"]

        async def process_command(self, command, context: AgentContext):
            user_input = str(command.content)

            # 思考中状态
            await context.emit_state("thinking")
            await context.emit_chunk("让我想想...\n")
            await asyncio.sleep(1)

            # 推理过程
            await context.emit_state("reasoning")
            await context.emit_chunk("首先，我需要分析这个问题...\n")
            await asyncio.sleep(0.5)

            # 生成回答
            await context.emit_state("generating")
            await context.emit_chunk(f"关于 '{user_input}' 的回答是：\n")
            await asyncio.sleep(0.5)

            # 最终答案
            await context.emit_chunk("这是最终的流式回答！")

            return {"status": "success"}
    ```

=== "Java"

    ```java
    public class ThinkingAgent extends GatewayWorker {
        public ThinkingAgent(String workerId) { super(workerId); }

        @Override
        public List<String> getAgentTypes() {
            return List.of("thinking_agent");
        }

        @Override
        public Object processCommand(GatewayCommand command, AgentContext context) {
            String userInput = String.valueOf(((AskAgentCommand) command).content());

            context.emitState("thinking");
            context.emitChunk("让我想想...\n");

            context.emitState("reasoning");
            context.emitChunk("首先，我需要分析这个问题...\n");

            context.emitState("generating");
            context.emitChunk("关于 '" + userInput + "' 的回答是：\n");
            context.emitChunk("这是最终的流式回答！");

            return "success";
        }
    }
    ```

=== "TypeScript"

    ```typescript
    class ThinkingAgent extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["thinking_agent"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            const userInput = String((command as AskAgentCommand).content);

            await context.emitState({ state: "thinking" });
            await context.emitChunk("让我想想...\n");
            await new Promise(resolve => setTimeout(resolve, 1000));

            await context.emitState({ state: "reasoning" });
            await context.emitChunk("首先，我需要分析这个问题...\n");
            await new Promise(resolve => setTimeout(resolve, 500));

            await context.emitState({ state: "generating" });
            await context.emitChunk(`关于 '${userInput}' 的回答是：\n`);
            await context.emitChunk("这是最终的流式回答！");

            return { status: "success" };
        }
    }
    ```
