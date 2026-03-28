import os
import uuid
import json
from typing import Annotated, Any, Dict, List, TypedDict, Union
from dotenv import load_dotenv

from by_framework.core.protocol.commands import (
    GatewayCommand, 
    AskAgentCommand, 
    ResumeCommand
)
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage, SystemMessage
from langchain_core.tools import tool

load_dotenv()

class AgentState(TypedDict):
    """LangGraph 状态定义"""
    messages: Annotated[list, add_messages]

class HierarchicalOrchestrator(GatewayWorker):
    """
    软件研发中心 - 首席协调官 (Top Supervisor)
    集成并发调度能力 (dispatch_group) 并利用新版 collect_group_results 获取结果。
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
        """适配严苛网关要求的多模态格式转换"""
        system_prompt = (
            "你是一个软件研发中心的首席协调官。\n"
            "你的职责是根据用户需求，调度合适的专家团队：\n"
            "1. 如果需要技术调研、方案比较或搜索信息，请调用 `call_research_team`。\n"
            "2. 如果需要具体编写代码、实现功能或修复 Bug，请调用 `call_coder_team`。\n"
            "3. **并行能力**: 如果用户的需求包含多个独立子项，系统会自动并行执行它们。\n"
            "4. 当所有子团队完成工作后，请汇总他们的成果给用户一个完美的总结。"
        )
        formatted = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}]
        for m in messages:
            if isinstance(m, HumanMessage): role = "user"
            elif isinstance(m, AIMessage): role = "assistant"
            elif isinstance(m, ToolMessage): role = "tool"
            else: role = "user"
            
            raw_text = m.content if hasattr(m, "content") else str(m)
            msg_dict = {"role": role, "content": [{"type": "text", "text": str(raw_text)}]}
            if isinstance(m, ToolMessage): msg_dict["tool_call_id"] = m.tool_call_id
            if role == "assistant" and hasattr(m, "tool_calls"): msg_dict["tool_calls"] = m.tool_calls
            formatted.append(msg_dict)
        return formatted

    def _build_graph(self, context: AgentContext):
        @tool
        async def call_research_team(requirement: str):
            """调度研究专家团队进行深度调研。"""
            return f"RESEARCH_TASK:{requirement}"

        @tool
        async def call_coder_team(spec: str):
            """调度编码专家团队进行功能开发任务。"""
            return f"CODER_TASK:{spec}"

        tools = [call_research_team, call_coder_team]
        llm = self._get_llm().bind_tools(tools)

        async def supervisor_node(state: AgentState):
            msgs = self._format_messages(state["messages"])
            resp = await llm.ainvoke(msgs)
            return {"messages": [resp]}

        async def dynamic_tool_node(state: AgentState):
            """智能感知并行意图并使用 dispatch_group"""
            last_msg = state["messages"][-1]
            tool_calls = last_msg.tool_calls
            
            if len(tool_calls) == 1:
                tc = tool_calls[0]
                target_type = "research-team-supervisor" if tc["name"] == "call_research_team" else "coder-team-supervisor"
                content = tc["args"].get("requirement") or tc["args"].get("spec")
                await context.emit_chunk(f"📡 [Orchestrator] 正在下发单项任务...", content_type="text")
                await context.call_agent(target_agent_type=target_type, content=content)
                return {"messages": [ToolMessage(content="Dispatched.", tool_call_id=tc["id"])]}
            else:
                tasks = []
                for tc in tool_calls:
                    target_type = "research-team-supervisor" if tc["name"] == "call_research_team" else "coder-team-supervisor"
                    content = tc["args"].get("requirement") or tc["args"].get("spec")
                    tasks.append({"target_agent_type": target_type, "content": content})
                
                await context.emit_chunk(f"🚀 [Orchestrator] 并行分发 {len(tasks)} 个专家团队任务...", content_type="text")
                await context.dispatch_group(tasks)
                return {"messages": [ToolMessage(content="Parallel Dispatched.", tool_call_id=tc["id"]) for tc in tool_calls]}

        workflow = StateGraph(AgentState)
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("tools", dynamic_tool_node)
        workflow.add_edge(START, "supervisor")
        workflow.add_conditional_edges("supervisor", lambda state: "tools" if state["messages"][-1].tool_calls else END)
        workflow.add_edge("tools", END)
        return workflow.compile()

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        if isinstance(command, AskAgentCommand):
            await context.emit_chunk("🏢 软件研发中心上线...", content_type="text")
            graph = self._build_graph(context)
            await graph.ainvoke({"messages": [HumanMessage(content=command.content)]})
            return "Initialized."

        elif isinstance(command, ResumeCommand):
            tg_id = getattr(command.header, "task_group_id", None)
            
            if tg_id:
                # 🛠 利用新版 collect_group_results 获取聚合结果
                results = await context.collect_group_results(tg_id)
                tool_messages = []
                for i, r in enumerate(results):
                    res_val = str(r.get("reply_data", "No data"))
                    # 前端缩略展示：仅展示前 200 字
                    display_val = res_val[:200] + "..." if len(res_val) > 200 else res_val
                    await context.emit_chunk(f"\n📥 专家 {i+1} 反馈 (摘要)：\n{display_val}\n", content_type="text")
                    # 传给历史记录的必须是完整原稿 res_val
                    tool_messages.append(ToolMessage(content=res_val, tool_call_id=f"ptc_{i}"))
                
                history = [
                    HumanMessage(content=str(command.content)),
                    AIMessage(content="Parallel coordination.", tool_calls=[{"name":"pe","id":"gr","args":{}}]),
                    *tool_messages,
                    HumanMessage(content="请根据以上反馈生成最终方案。")
                ]
            else:
                res_val = str(command.reply_data)
                # 前端缩略展示：仅展示前 200 字
                display_val = res_val[:200] + "..." if len(res_val) > 200 else res_val
                await context.emit_chunk(f"\n📥 专家反馈 (摘要)：\n{display_val}\n", content_type="text")
                history = [
                    HumanMessage(content=str(command.content)),
                    AIMessage(content="Step coordination.", tool_calls=[{"name":"sc","id":"s1","args":{}}]),
                    ToolMessage(content=str(command.reply_data), tool_call_id="s1"),
                    HumanMessage(content="请基于此项反馈汇总。")
                ]
            
            final_resp = await self._build_graph(context).ainvoke({"messages": history})
            summary = final_resp["messages"][-1].content
            await context.emit_chunk(f"\n✨ [报告要点]:\n{summary}", content_type="text")
            return summary

if __name__ == "__main__":
    run_worker(HierarchicalOrchestrator, worker_id="orchestrator-1")
