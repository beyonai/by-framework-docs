import os
import asyncio
from typing import Annotated, Any, Dict, List, TypedDict
from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool

load_dotenv()

class CoderState(TypedDict):
    """编码团队状态"""
    messages: Annotated[list, add_messages]

class CoderTeamWorker(GatewayWorker):
    """
    编码专家团队 - 内部使用 LangGraph 管理开发流
    """

    def get_capabilities(self) -> List[str]:
        return ["coder-team-supervisor"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    def _build_graph(self, context: AgentContext):
        @tool
        async def code_generator(spec: str):
            """根据调研规格说明生成高质量的代码实现架构。"""
            await context.emit_chunk(f"💻 [Coder] 正在根据需求生成代码架构: {spec[:30]}...", content_type="text")
            return f"代码生成成功。建议使用 FastAPI 的依赖注入 (Depends) 模式实现业务解耦。"

        @tool
        async def unit_test_creator(code_context: str):
            """为生成的代码创建完善的单元测试用例。"""
            await context.emit_chunk(f"🧪 [Coder] 正在生成对应的单元测试模块...", content_type="text")
            return "单元测试生成完成，包含 Pytest 异步测试用例。"

        tools = [code_generator, unit_test_creator]
        llm = self._get_llm().bind_tools(tools)

        async def coder_node(state: CoderState):
            # 内部节点逻辑：确保系统提示词存在
            msgs = state["messages"]
            if not any(isinstance(m, SystemMessage) for m in msgs):
                sys_msg = SystemMessage(content="你是一名资深后端开发专家。请基于输入的需求规格，编写高效、可读性强的 Python 代码并附带测试建议。")
                msgs = [sys_msg] + msgs
            
            resp = await llm.ainvoke(msgs)
            
            # 实时流式反馈给前端用户
            if resp.content:
                await context.emit_chunk(resp.content, content_type="text")
            
            return {"messages": [resp]}

        workflow = StateGraph(CoderState)
        workflow.add_node("coder", coder_node)
        workflow.add_node("tools", ToolNode(tools))
        
        workflow.add_edge(START, "coder")
        workflow.add_conditional_edges("coder", tools_condition)
        workflow.add_edge("tools", "coder")
        
        return workflow.compile()

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        self.logger.info(f"Coder Team processing: {command.content}")
        graph = self._build_graph(context)
        
        # 运行内部图逻辑
        initial_state = {"messages": [HumanMessage(content=command.content)]}
        final_state = await graph.ainvoke(initial_state)
        
        # 提取最终结论返回给 Orchestrator
        last_msg = final_state["messages"][-1]
        result = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        return result

if __name__ == "__main__":
    run_worker(CoderTeamWorker, worker_id="coder-team-1")
