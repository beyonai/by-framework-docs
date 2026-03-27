import os
import asyncio
from typing import Annotated, Any, List
from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, add_messages

# 加载 .env 文件中的环境变量
load_dotenv()


class AgentState(Annotated[dict, "AgentState"]):
    messages: Annotated[list[BaseMessage], add_messages]


class LangGraphWorker(GatewayWorker):
    """
    基于 LangGraph 实现的 Gateway Worker 示例。
    """

    def get_capabilities(self) -> List[str]:
        """返回此 Worker 支持的智能体类型列表。"""
        return ["langgraph-agent"]

    def _build_graph(self):
        """构建一个简单的 LangGraph 图。"""
        workflow = StateGraph(AgentState)

        # 定义一个简单的节点，调用 LLM
        async def call_model(state: AgentState):
            # 获取 LLM 配置，也可以从环境变量读取
            llm = ChatOpenAI(
                model=os.getenv("LLM_MODEL", "gpt-4o"),
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
                streaming=True
            )
            response = await llm.ainvoke(state["messages"])
            return {"messages": [response]}

        workflow.add_node("agent", call_model)
        workflow.set_entry_point("agent")
        workflow.set_finish_point("agent")

        return workflow.compile()

    async def process_command(
        self, command: GatewayCommand, context: AgentContext
    ) -> Any:
        """处理来自 Gateway 的命令。"""
        self.logger.info(f"Processing command: {command.header.message_id}")

        # 1. 初始化状态
        initial_state = {"messages": [HumanMessage(content=command.content)]}

        # 2. 构建并运行图
        graph = self._build_graph()

        full_response = ""
        # 3. 使用 astream 获取流式输出
        async for event in graph.astream(initial_state, stream_mode="messages"):
            message, metadata = event
            if message.content:
                full_response += message.content
                # 通过 context.emit_chunk 发送流式分片到前端
                await context.emit_chunk(message.content)

        return full_response


if __name__ == "__main__":
    # 使用 by-framework 提供的快捷入口启动 Worker
    # 参数优先从环境变量中读取，如果没有则使用默认值
    run_worker(
        LangGraphWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "langgraph-worker-1"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
    )
