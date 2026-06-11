import os
import asyncio
from typing import Annotated, Any, List
from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker
from by_framework_history_byclaw import ByClawHistoryBackend
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, add_messages

# 加载 .env 文件中的环境变量，确保无论从哪个目录启动都能正确读取
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


class AgentState(Annotated[dict, "AgentState"]):
    messages: Annotated[list[BaseMessage], add_messages]


class LangGraphWorker(GatewayWorker):
    """
    基于 LangGraph 实现的 Gateway Worker 示例。
    """

    def get_agent_types(self) -> List[str]:
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

        # 1. 健壮地提取 content 文本，兼容 string / dict / list 等不同来源的消息格式
        raw_content = command.content
        prompt_text = ""
        if isinstance(raw_content, str):
            prompt_text = raw_content
        elif isinstance(raw_content, dict):
            inner_content = raw_content.get("content")
            if isinstance(inner_content, dict):
                prompt_text = inner_content.get("text", "")
            else:
                prompt_text = str(inner_content or "")
        elif isinstance(raw_content, list) and raw_content:
            first_item = raw_content[0]
            if isinstance(first_item, dict):
                inner_content = first_item.get("content")
                if isinstance(inner_content, dict):
                    prompt_text = inner_content.get("text", "")
                else:
                    prompt_text = str(inner_content or "")
            else:
                prompt_text = str(first_item)
        else:
            prompt_text = str(raw_content or "")

        # 2. 初始化状态
        initial_state = {"messages": [HumanMessage(content=prompt_text)]}

        # 3. 构建图
        graph = self._build_graph()

        history = await context.agent_runtime_state.session_manager.history.get_history()

        # 4. 从基类 Context 中获取配置并挂载的 Langfuse 追踪 Callback
        callback = context.langfuse_callback
        config = {"callbacks": [callback]} if callback else {}

        full_response = ""
        # 5. 使用 astream 执行并传入 callback 监控
        async for event in graph.astream(initial_state, stream_mode="messages", config=config):
            message, metadata = event
            if message.content:
                full_response += message.content
                # 通过 context.emit_chunk 发送流式分片到前端
                await context.emit_chunk(message.content, content_type="1002")

        return full_response


if __name__ == "__main__":
    # 使用 by-framework 提供的快捷入口启动 Worker
    # 参数优先从环境变量中读取，如果没有则使用默认值
    run_worker(
        LangGraphWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "langgraph-worker-1"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("REDIS_PORT", 6379)),
        redis_db=int(os.getenv("REDIS_DB", 0)),
        redis_username=os.getenv("REDIS_USERNAME"),
        redis_password=os.getenv("REDIS_PASSWORD"),
    )
