import os
from typing import Annotated, Any, Dict, List, TypedDict
from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, AIMessage
from langchain_core.tools import tool

load_dotenv()

class TeamState(TypedDict):
    """子团队状态"""
    messages: Annotated[list, add_messages]

class ResearchTeamWorker(GatewayWorker):
    """
    研究专家团队 - 内部使用 LangGraph 管理调研流
    """

    def get_capabilities(self) -> List[str]:
        return ["research-team-supervisor"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    def _build_graph(self, context: AgentContext):
        @tool
        async def web_search(query: str):
            """对给定的主题进行深度互联网搜索，获取最新技术趋势。"""
            await context.emit_chunk(f"🔍 [Research] 正在全局搜索: {query}...", content_type="text")
            return f"关于 '{query}' 的搜索结果：FastAPI 结合 Pydantic V2 是目前高性能 Web 开发的首选方案。"

        @tool
        async def competitor_analysis(product: str):
            """分析相关产品的技术栈和优缺点。"""
            await context.emit_chunk(f"📊 [Research] 正在分析竞品技术栈: {product}...", content_type="text")
            return f"针对 '{product}' 的竞品分析完成：主要瓶颈在于同步 IO 处理，建议采用异步架构优化。"

        tools = [web_search, competitor_analysis]
        llm = self._get_llm().bind_tools(tools)

        async def researcher_node(state: TeamState):
            # 内部节点逻辑：确保系统提示词存在
            msgs = state["messages"]
            if not any(isinstance(m, SystemMessage) for m in msgs):
                sys_msg = SystemMessage(content="你是一名资深技术研究员。请利用搜索和分析工具提供详尽、准确的技术调研报告。")
                msgs = [sys_msg] + msgs
            
            resp = await llm.ainvoke(msgs)
            
            # 实时流式反馈给前端用户
            if resp.content:
                await context.emit_chunk(resp.content, content_type="text")
            
            return {"messages": [resp]}

        workflow = StateGraph(TeamState)
        workflow.add_node("researcher", researcher_node)
        workflow.add_node("tools", ToolNode(tools))
        
        workflow.add_edge(START, "researcher")
        workflow.add_conditional_edges("researcher", tools_condition)
        workflow.add_edge("tools", "researcher")
        
        return workflow.compile()

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        self.logger.info(f"Research Team processing: {command.content}")
        graph = self._build_graph(context)
        
        # 运行内部图逻辑
        initial_state = {"messages": [HumanMessage(content=command.content)]}
        final_state = await graph.ainvoke(initial_state)
        
        # 提取最终结论返回给 Orchestrator
        last_msg = final_state["messages"][-1]
        result = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        return result

if __name__ == "__main__":
    run_worker(ResearchTeamWorker, worker_id="research-team-1")
