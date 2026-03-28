import os
import asyncio
from typing import Annotated, Any, Dict, List, TypedDict, Optional
from dotenv import load_dotenv

from by_framework.core.protocol.commands import (
    GatewayCommand, 
    AskAgentCommand, 
    ResumeCommand
)
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, AIMessage
from langchain_core.tools import tool

# 加载环境变量
load_dotenv()

class AgentState(TypedDict):
    """LangGraph 状态定义"""
    messages: Annotated[list, add_messages]

class OrchestratorWorker(GatewayWorker):
    """
    诗歌系统协调者 (Worker A)。
    负责识别用户的诗歌需求，并调度远程“执行层诗人”进行创作。
    """

    def get_capabilities(self) -> List[str]:
        return ["orchestrator-agent"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    def _format_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """多模态格式转换，适配严苛网关要求"""
        system_prompt = (
            "你是一个文学创作系统的协调员。\n"
            "如果你收到写诗、创作诗词的需求，请务必使用 `invoke_poet_agent` 工具将任务分发给专业的 AI 诗人。\n"
            "在诗人创作完成后，你的职责是根据其内容给出一句简洁且充满文学气息的简评。"
        )
        formatted = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}]
        for m in messages:
            if isinstance(m, HumanMessage): role = "user"
            elif isinstance(m, ToolMessage): role = "tool"
            elif isinstance(m, AIMessage): role = "assistant"
            else: role = "user"
            
            raw_text = m.content if hasattr(m, "content") else str(m)
            msg_dict = {"role": role, "content": [{"type": "text", "text": str(raw_text)}]}
            if isinstance(m, ToolMessage): msg_dict["tool_call_id"] = m.tool_call_id
            if role == "assistant" and hasattr(m, "tool_calls"): msg_dict["tool_calls"] = m.tool_calls
            formatted.append(msg_dict)
        return formatted

    def _build_graph(self, context: AgentContext):
        @tool
        async def invoke_poet_agent(topic: str):
            """
            【跨进程诗人调用】：调度专门的诗人 Agent（Process-B）进行流式创作。
            `topic` 是诗歌的主题或题目。
            """
            self.logger.info(f"[Orchestrator] 🌐 正在连接并调度首席诗人执行任务：{topic}")
            await context.emit_chunk(f"🎨 [Orchestrator] 已接洽首席诗人，正在根据主题“{topic}”挥毫泼墨...", content_type="text")

            # 修复 RuntimeWarning: 确保 await
            await context.get_active_workers()
            
            # 分布式触发流式诗人
            await context.call_agent(
                target_agent_type="sub-worker-agent",
                content=topic
            )
            return f"任务已交给诗人节点处理。正在为您同步流式灵感数据。"

        tools = [invoke_poet_agent]
        llm = self._get_llm().bind_tools(tools)

        async def agent_node(state: AgentState):
            msgs = self._format_messages(state["messages"])
            resp = await llm.ainvoke(msgs)
            return {"messages": [resp]}

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", ToolNode(tools))
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", END)
        return workflow.compile()

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        if isinstance(command, AskAgentCommand):
            await context.emit_chunk("✍️ 文学协调进程已就绪...", content_type="text")
            graph = self._build_graph(context)
            await graph.ainvoke({"messages": [HumanMessage(content=command.content)]})
            return "Poetry session started."

        elif isinstance(command, ResumeCommand):
            poem_result = str(command.reply_data)
            self.logger.info(f"[Orchestrator] 📥 接收到完整诗篇 (Resume)")
            
            fake_id = "poet_" + context.session_id[-4:]
            # 强化 Resume 逻辑：追加总结指令，让 AI 给诗歌评价
            history = [
                HumanMessage(content=str(command.content)),
                AIMessage(content="", tool_calls=[{"name": "invoke_poet_agent", "args": {"topic": str(command.content)}, "id": fake_id}]),
                ToolMessage(content=poem_result, tool_call_id=fake_id),
                HumanMessage(content="这是诗人完成的最终作品，请仅针对此诗给出一段精简且有深度且充满文采的文学评价。")
            ]
            
            graph = self._build_graph(context)
            final = await graph.ainvoke({"messages": history})
            
            # 安全提取模型响应
            last_msg = final["messages"][-1]
            final_answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            
            if not final_answer or final_answer.strip() == "":
                final_answer = f"鉴赏心得：此作意境非凡，不愧为佳品。"

            self.logger.info(f"[Orchestrator] 📥 最终评价: {final_answer}")
            await context.emit_chunk(f"\n💡 [文学鉴赏]：\n{final_answer}", content_type="text")
            return final_answer

if __name__ == "__main__":
    run_worker(
        OrchestratorWorker,
        worker_id="orchestrator-poet-manager-1",
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD")
    )
