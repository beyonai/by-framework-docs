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

    def make_invoke_poet_agent_tool(self, context: AgentContext):
        from langgraph.types import interrupt
        from langchain_core.tools import InjectedToolCallId
        from typing import Annotated

        @tool
        async def invoke_poet_agent(topic: str, tool_call_id: Annotated[str, InjectedToolCallId]):
            """
            【跨进程诗人调用】：调度专门的诗人 Agent（Process-B）进行流式创作。
            `topic` 是诗歌的主题或题目。
            """
            # 【基于 Redis 的完全分布式幂等防抖】：
            # 使用大模型生成的原生 tool_call_id 作为唯一标识，存入 Redis
            redis_key = f"dispatched_task:{context.session_id}:{tool_call_id}"
            
            # 如果 Redis 中不存在这个任务的下发记录，则真正发起跨进程派发
            is_dispatched = await context.redis.exists(redis_key)
            if not is_dispatched:
                self.logger.info(f"[Orchestrator] 🌐 正在连接并调度首席诗人执行任务（ID: {tool_call_id}）...")
                await context.emit_chunk(f"🎨 [Orchestrator] 已接洽首席诗人，正在根据主题“{topic}”挥毫泼墨...", content_type="text")

                await context.get_active_workers()
                
                # 分布式触发流式诗人，调用不阻塞，将任务发出
                await context.call_agent(
                    target_agent_type="sub-worker-agent",
                    content=topic
                )
                
                # 将下发记录标记入 Redis，设置过期时间为 24 小时（自动清理，防泄露）
                await context.redis.set(redis_key, 1, ex=86400)
            
            # 【正统 LangGraph 中断】：抛出中断，令 LangGraph 将图挂起
            # 直到收到 ResumeCommand 并用 Command(resume=) 唤醒时才会继续往下执行并返回
            poem_result = interrupt("Waiting for poet agent to finish.")
            
            return f"诗人的创作结果是：\n{poem_result}\n\n请在最终回复中仅针对此诗给出一段精简且有深度且充满文采的文学评价。并且如果必要，你可以先调用工具分析诗歌风格。"

        return invoke_poet_agent

    def _build_graph(self, context: AgentContext, command: GatewayCommand):
        # 通过工厂方法将上下文注入并创建被包裹的 Tool
        invoke_poet_agent = self.make_invoke_poet_agent_tool(context)
        
        @tool
        async def evaluate_poem_style(poem_text: str):
            """
            【本地工具】：分析诗歌的体裁和押韵风格。
            如果用户要求评论诗歌的风格或结构，你可以调用此工具。
            """
            await context.emit_chunk(f"🔍 [Orchestrator] 本地工具诊断：正在评估诗歌的文学风格...", content_type="text")
            
            if "山" in poem_text or "水" in poem_text:
                style = "山水田园诗，气韵生动"
            elif "剑" in poem_text or "战" in poem_text:
                style = "边塞风光，豪气干云"
            else:
                style = "抒情咏景，意境深远"
                
            return f"分析结果：{style}"

        tools = [invoke_poet_agent, evaluate_poem_style]
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
        workflow.add_edge("tools", "agent")
        
        # 使用持久化上下文以支持中断/恢复
        from langgraph.checkpoint.memory import MemorySaver
        if not hasattr(self, "_memory_saver"):
            self._memory_saver = MemorySaver()
            
        return workflow.compile(checkpointer=self._memory_saver)

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        from langgraph.types import Command
        
        # 必须为当前 Session 指定 Thread ID，这样 MemorySaver 才能恢复会话
        config = {"configurable": {"thread_id": context.session_id}}
        graph = self._build_graph(context, command)
        
        if isinstance(command, AskAgentCommand):
            await context.emit_chunk("✍️ 文学协调进程已就绪...", content_type="text")
            
            # 首轮启动，遇到 interrupt 则执行完毕（返回状态是被挂起）
            final = await graph.ainvoke({"messages": [HumanMessage(content=command.content)]}, config=config)
            
            last_msg = final["messages"][-1]
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                 return "Poetry session started and correctly suspended."
            else:
                 final_answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                 await context.emit_chunk(f"\n💡 {final_answer}", content_type="text")
                 return final_answer

        elif isinstance(command, ResumeCommand):
            poem_result = str(command.reply_data)
            self.logger.info(f"[Orchestrator] 📥 接收到完整诗篇 (Resume)，准备唤醒 LangGraph 流...")
            
            # 【正统 LangGraph 唤醒】：携带诗歌结果打醒之前挂起的 interrupt 工具
            final = await graph.ainvoke(Command(resume=poem_result), config=config)
            
            # 若后续图继续跑完且不再抛出大模型 tool_calls
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
