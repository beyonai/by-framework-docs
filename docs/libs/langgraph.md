# LangGraph 集成

by-framework 提供了对 LangGraph 的深度集成，允许你利用图形化编排能力来构建复杂的 Agent 工作流。

## 安装

=== "Python"

    ```bash
    pip install by-framework-langgraph
    ```

=== "TypeScript"

    ```bash
    npm install @langchain/langgraph byclaw-gateway-sdk
    ```

## 核心模式：interrupt + resume

by-framework 与 LangGraph 集成的核心在于处理**异步挂起**。当 Agent 需要等待外部输入或其他 Agent 返回时，利用 LangGraph 的 `interrupt` 能力挂起状态，并在收到 `ResumeCommand` 时恢复。

=== "Python"

    ```python
    from langgraph.types import interrupt, Command
    from by_framework_langgraph import LangGraphWorker

    class MyAgent(LangGraphWorker):
        def create_graph(self, state):
            # ...
            # 挂起执行
            result = interrupt("Waiting for user input")
            # ...
    ```

=== "TypeScript"

    ```typescript
    import { interrupt, Command } from "@langchain/langgraph";
    import { GatewayWorker } from "byclaw-gateway-sdk";

    // TypeScript 推荐直接在 processCommand 中编排 Graph
    ```

## 完整示例

=== "Python"

    ```python
    from by_framework_langgraph import LangGraphWorker
    from langgraph.graph import StateGraph, END
    from typing import TypedDict, List

    class AgentState(TypedDict):
        messages: List[str]

    class MyLangGraphAgent(LangGraphWorker):
        def get_agent_types(self):
            return ["my_langgraph_agent"]

        def create_graph(self, state: AgentState):
            graph = StateGraph(AgentState)
            # 添加节点和逻辑...
            return graph.compile()
    ```

=== "TypeScript"

    ```typescript
    import { GatewayWorker, AgentContext, AskAgentCommand } from "byclaw-gateway-sdk";
    import { StateGraph, START, END } from "@langchain/langgraph";

    class LangGraphAgent extends GatewayWorker {
        getAgentTypes() { return ["langgraph-agent"]; }

        async processCommand(command: any, context: AgentContext) {
            const workflow = new StateGraph({
                channels: { messages: { reducer: (a, b) => a.concat(b) } }
            })
            .addNode("agent", async (state) => {
                await context.emitChunk("Thinking...");
                return { messages: ["Hello from TS LangGraph"] };
            })
            .addEdge(START, "agent")
            .addEdge("agent", END);

            const app = workflow.compile();
            const result = await app.invoke({ messages: [] });
            return result.messages.join("\n");
        }
    }
    ```

## 特性对比

| 特性 | Python (`by-framework-langgraph`) | TypeScript (`native`) |
|------|-----------------------------------|-----------------------|
| 自动状态同步 | ✅ | 需手动处理 |
| 异步挂起 (interrupt) | ✅ | ✅ |
| 流式 Chunk 转发 | ✅ | ✅ |
| 检查点持久化 (Redis) | ✅ | ✅ |
