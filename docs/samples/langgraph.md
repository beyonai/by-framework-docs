# LangGraph 集成

!!! info "LangGraph 生态支持"
    LangGraph 目前提供 Python 和 TypeScript 两种语言版本的实现。Python 版本功能最为完善，TypeScript 版本（LangGraph.js）也已可用于生产。

## 核心模式：interrupt + resume

by-framework 与 LangGraph 深度集成，核心模式是：

1. **dispatch + interrupt**：在工具内部挂起 LangGraph 执行
2. **ResumeCommand**：子 Agent 完成后唤醒，恢复执行

=== "Python"

    ```python
    from langgraph.types import interrupt, Command

    # 工具内部挂起
    result = interrupt(f"Waiting for {target_agent_type} to finish")

    # 唤醒时携带结果
    final = await graph.ainvoke(Command(resume=resume_data), config=config)
    ```

=== "TypeScript"

    ```typescript
    import { interrupt, Command } from "@langchain/langgraph";

    // 工具内部挂起
    const result = interrupt(`Waiting for ${targetAgentType} to finish`);

    // 唤醒时携带结果
    const final = await graph.invoke(new Command({ resume: resumeData }), config);
    ```

## 完整示例

=== "Python"

    ```python
    import os
    from typing import Annotated, Any, List, TypedDict
    from by_framework.worker import (
        ByaiAgentContext, ByaiAskAgentCommand, ByaiResumeCommand, ByaiWorker, run_worker,
    )
    from langgraph.graph import END, START, StateGraph
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode, tools_condition
    from langchain_core.messages import HumanMessage
    from langchain_core.tools import InjectedToolCallId, tool

    class LangGraphAgent(ByaiWorker):
        def get_agent_types(self) -> List[str]:
            return ["langgraph-agent"]

        def _make_remote_tool(self, context, tool_name, target_agent_type, description):
            from langgraph.types import interrupt

            @tool(tool_name, description=description)
            async def remote_tool(topic: str, tool_call_id: Annotated[str, InjectedToolCallId]):
                redis_key = f"dispatched_task:{context.session_id}:{tool_call_id}"
                if not await context.redis.exists(redis_key):
                    await context.call_agent(target_agent_type=target_agent_type, content=topic)
                    await context.redis.set(redis_key, 1, ex=86400)
                result = interrupt(f"Waiting for {target_agent_type}")
                return f"专家回复：\n{result}"

            return remote_tool

        async def process_command(self, command, context: ByaiAgentContext) -> Any:
            from langgraph.types import Command

            config = {"configurable": {"thread_id": context.session_id}}
            graph = self._build_graph(context, command)

            if isinstance(command, ByaiAskAgentCommand):
                await context.emit_chunk("开始处理...")
                final = await graph.ainvoke(
                    {"messages": [HumanMessage(content=str(command.content))]}, config=config
                )
                last_msg = final["messages"][-1]
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    return "Tasks dispatched, graph suspended"
                return last_msg.content

            if isinstance(command, ByaiResumeCommand):
                resume_data = str(command.reply_data) if hasattr(command, "reply_data") else ""
                final = await graph.ainvoke(Command(resume=resume_data), config=config)
                return final["messages"][-1].content

            raise TypeError(f"Unsupported command type: {type(command)!r}")

        def _build_graph(self, context, command):
            class AgentState(TypedDict):
                messages: Annotated[list, add_messages]

            invoke_expert = self._make_remote_tool(context, "invoke_expert", "expert-agent", "调度专家处理任务")

            @tool
            async def evaluate(text: str):
                """本地评估工具"""
                return f"评估结果：{text[:50]}..."

            tools = [invoke_expert, evaluate]
            llm = self._get_llm().bind_tools(tools)

            async def agent_node(state: AgentState):
                resp = await llm.ainvoke(state["messages"])
                return {"messages": [resp]}

            workflow = StateGraph(AgentState)
            workflow.add_node("agent", agent_node)
            workflow.add_node("tools", ToolNode(tools))
            workflow.add_edge(START, "agent")
            workflow.add_conditional_edges("agent", tools_condition)
            workflow.add_edge("tools", "agent")

            from langgraph.checkpoint.memory import MemorySaver
            return workflow.compile(checkpointer=MemorySaver())
    ```

=== "TypeScript"

    ```typescript
    import {
        GatewayWorker, AgentContext, GatewayCommand,
        AskAgentCommand, ResumeCommand, runWorker
    } from '@byclaw/by-framework';
    import { StateGraph, START, END, MemorySaver } from '@langchain/langgraph';
    import { ChatOpenAI } from '@langchain/openai';
    import { ToolNode } from '@langchain/langgraph/prebuilt';
    import { HumanMessage } from '@langchain/core/messages';
    import { tool } from '@langchain/core/tools';
    import { z } from 'zod';

    class LangGraphAgent extends GatewayWorker {
        getAgentTypes(): string[] {
            return ["langgraph-agent"];
        }

        async processCommand(command: GatewayCommand, context: AgentContext) {
            if (command instanceof AskAgentCommand) {
                await context.emitChunk("开始处理...");

                // 构建 LangGraph
                const evaluateTool = tool(
                    async ({ text }) => `评估结果：${text.slice(0, 50)}...`,
                    { name: "evaluate", description: "本地评估工具", schema: z.object({ text: z.string() }) }
                );

                const llm = new ChatOpenAI({ model: "gpt-4" }).bindTools([evaluateTool]);
                // ... 构建 StateGraph 并执行
            }

            if (command instanceof ResumeCommand) {
                // 恢复执行
            }
        }
    }

    runWorker(LangGraphAgent, { workerId: "langgraph-worker-1" });
    ```

## 关键概念

| 概念 | 说明 |
|------|------|
| `interrupt()` | LangGraph 内部中断，等待外部唤醒 |
| `Command(resume=...)` | 携带数据唤醒被中断的图 |
| `MemorySaver` | Checkpointer，保存图状态用于恢复 |
| `thread_id` | 通常用 session_id，实现多会话隔离 |

## 配置

=== "Python"

    ```python
    run_worker(
        worker_class=LangGraphAgent,
        worker_id="langgraph-worker-1",
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
    )
    ```

=== "TypeScript"

    ```typescript
    runWorker(LangGraphAgent, {
        workerId: "langgraph-worker-1",
        redisHost: process.env.BYAI_REDIS_HOST || "127.0.0.1",
        redisPort: Number(process.env.BYAI_REDIS_PORT || 6379),
    });
    ```
