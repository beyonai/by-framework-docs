"""
原生 LangGraph Worker + by-framework Trace 接入示例
=====================================================

适用场景：
    你已有一个原生 LangGraph 图（StateGraph / create_react_agent / CompiledGraph），
    不想继承 LangGraphWorker，只继承 ByaiWorker / GatewayWorker。

接入方式：
    1. 安装 by-framework-trace-langfuse —— 自动注册 LangfusePlugin，
       框架层的 agent.workflow / worker.execute / agent.task span 由插件全程接管。
    2. 在 process_command 里用 _langfuse_scope() context manager 包住图调用，
       LangGraph 内部的 LLM / tool span 自动嵌套在框架 agent.task span 之下。

运行前提：
    pip install by-framework by-framework-trace-langfuse
    pip install langgraph langchain-core langchain-openai python-dotenv

环境变量（见 .env.example）：
    BYAI_WORKER_ID, BYAI_REDIS_HOST, OPENAI_API_KEY, LLM_MODEL
    LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL
"""

from __future__ import annotations

import ast
import operator
import os
from contextlib import contextmanager
from functools import cached_property
from typing import Annotated, Any, Callable, Iterator

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages
from langgraph.prebuilt import create_react_agent

from by_framework.core.protocol.byai_codec import deserialize_byai_content
from by_framework.core.protocol.commands import GatewayCommand
from by_framework.core.protocol.message import BaiYingMessage, MessageContent
from by_framework.worker import AgentContext, ByaiWorker, run_worker

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


# ── Langfuse Scope Context Manager ────────────────────────────────────────────
# 用法：
#   with _langfuse_scope(context) as callbacks:
#       config = {..., "callbacks": callbacks}
#       await graph.ainvoke(state, config)
#
# 嵌套策略（与 LangGraphAdapter 完全对齐）：
#   by-framework-langgraph 只知道“我需要一个 LangChain callback”；
#   by-framework-trace-langfuse 负责用最新 Langfuse SDK 参数构造 CallbackHandler。

@contextmanager
def _langfuse_scope(
    context: AgentContext,
) -> Iterator[list[Any]]:
    """
    Yields a callbacks list，可直接传入 LangGraph config["callbacks"]。

    同步 context manager，可在 async 函数里用 `with`（不需要 `async with`）。
    """
    callbacks: list[Any] = []

    parent_observation_id = context.get_trace_parent_observation_id()
    if not parent_observation_id:
        yield callbacks
        return

    try:
        from by_framework_trace_langfuse import build_langchain_callback
    except (ImportError, AttributeError):
        yield callbacks
        return

    langfuse_cb = build_langchain_callback(
        trace_id=context.trace_id,
        parent_observation_id=parent_observation_id,
    )
    if langfuse_cb is not None:
        callbacks.append(langfuse_cb)
    yield callbacks


# ── Worker 实现 ───────────────────────────────────────────────────────────────

_BINARY_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval_arithmetic(expression: str) -> float:
    """Evaluate a small arithmetic expression without exposing Python builtins."""

    def eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp):
            operation = _BINARY_OPERATORS.get(type(node.op))
            if operation is None:
                raise ValueError("仅支持 +、-、*、/ 运算")
            return operation(eval_node(node.left), eval_node(node.right))
        if isinstance(node, ast.UnaryOp):
            operation = _UNARY_OPERATORS.get(type(node.op))
            if operation is None:
                raise ValueError("仅支持正负号")
            return operation(eval_node(node.operand))
        raise ValueError("仅支持数字、括号和基本算术运算")

    tree = ast.parse(expression, mode="eval")
    return eval_node(tree)


@tool
def calculate(expression: str) -> str:
    """计算一个简单的数学表达式，例如 '2 + 3 * 4'。"""
    try:
        result = _safe_eval_arithmetic(expression)
        return str(int(result) if result.is_integer() else result)
    except Exception as exc:  # noqa: BLE001 - tool errors should be returned to LLM
        return f"计算错误: {exc}"


class AgentState(dict):
    messages: Annotated[list[BaseMessage], add_messages]


def _extract_text(content: Any) -> str:
    """Flatten Byai wire/domain content into a prompt string."""
    normalized = deserialize_byai_content(content)
    return _extract_any_text(normalized)


def _extract_any_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, BaiYingMessage):
        return _extract_any_text(content.content)
    if isinstance(content, MessageContent):
        return content.text
    if isinstance(content, dict):
        payload = content.get("content", content)
        if isinstance(payload, dict):
            return str(payload.get("text", "") or payload)
        return str(payload)
    if isinstance(content, list):
        return "\n\n".join(
            text for text in (_extract_any_text(item) for item in content) if text
        )
    if content is None:
        return ""
    return str(content)


def _build_langgraph_config(
    *,
    context: AgentContext,
    command: GatewayCommand,
    callbacks: list[Any],
) -> dict[str, Any]:
    """Build LangGraph runtime config with trace-friendly metadata."""
    header = getattr(command, "header", None)
    agent_id = getattr(context, "current_agent_id", "") or "langgraph"
    metadata = {
        "langfuse_session_id": context.session_id,
        "langfuse_user_id": getattr(header, "user_code", "") or "",
        "by_framework_trace_id": context.trace_id,
        "by_framework_message_id": context.message_id,
        "by_framework_parent_message_id": getattr(context, "parent_message_id", ""),
        "by_framework_agent_id": agent_id,
    }
    return {
        "configurable": {"thread_id": context.message_id or context.session_id},
        "callbacks": callbacks,
        "run_name": f"{agent_id}:langgraph",
        "metadata": {key: value for key, value in metadata.items() if value},
    }


class NativeTraceWorker(ByaiWorker):
    """
    原生 LangGraph Worker。

    继承 ByaiWorker（不使用 LangGraphWorker），在 process_command 中手动构建并运行图。
    Trace 接入通过 _langfuse_scope() context manager 统一处理，与业务逻辑解耦。
    """

    def get_agent_types(self) -> list[str]:
        return ["native-trace-agent"]

    @cached_property
    def _build_graph(self):
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True,
            stream_options={"include_usage": True},  # OpenAI 流式 token 统计必须
        )
        return create_react_agent(llm, tools=[calculate])

    async def process_command(
        self, command: GatewayCommand, context: AgentContext
    ) -> Any:
        prompt_text = _extract_text(command.content)
        full_response = ""

        # _langfuse_scope 是同步 context manager，在 async 函数里用 `with` 即可
        with _langfuse_scope(context) as callbacks:
            config = _build_langgraph_config(
                context=context,
                command=command,
                callbacks=callbacks,
            )
            async for event in self._build_graph.astream_events(
                {"messages": [HumanMessage(content=prompt_text)]},
                config,
                version="v2",
            ):
                kind = event.get("event", "")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    content = getattr(chunk, "content", "") if chunk else ""
                    if content:
                        full_response += content
                        await context.emit_chunk(content)
                elif kind == "on_chat_model_end":
                    output = event.get("data", {}).get("output")
                    usage = getattr(output, "usage_metadata", None) if output else None
                    if usage:
                        context.record_token_usage(
                            prompt_tokens=int(usage.get("input_tokens") or 0),
                            completion_tokens=int(usage.get("output_tokens") or 0),
                        )

        return full_response


# ── 启动入口 ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_worker(
        NativeTraceWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "native-trace-worker-1"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
    )
