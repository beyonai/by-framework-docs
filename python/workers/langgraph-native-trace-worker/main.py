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
       LangGraph 内部的 LLM / tool span 自动嵌套在框架 span 之下。

运行前提：
    pip install by-framework by-framework-trace-langfuse
    pip install langgraph langchain-core langchain-openai python-dotenv

环境变量（见 .env.example）：
    BYAI_WORKER_ID, BYAI_REDIS_HOST, OPENAI_API_KEY, LLM_MODEL
    LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST（或 LANGFUSE_BASE_URL）
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from importlib import import_module
from typing import Annotated, Any, Iterator

from dotenv import load_dotenv
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages
from langgraph.prebuilt import create_react_agent

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, ByaiWorker, run_worker

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


# ── Token 统计 Callback ───────────────────────────────────────────────────────

class _TokenCallback(BaseCallbackHandler):
    """把 LLM token 用量写入 AgentContext，供框架 trace 统计。"""

    def __init__(self, context: AgentContext) -> None:
        super().__init__()
        self._ctx = context
        self._seen: set = set()

    def on_llm_end(self, response: Any, *, run_id: Any = None, **_: Any) -> None:
        if run_id and run_id in self._seen:
            return
        prompt, completion = self._extract(response)
        if not (prompt or completion):
            return
        if run_id:
            self._seen.add(run_id)
        try:
            self._ctx.record_token_usage(
                prompt_tokens=prompt,
                completion_tokens=completion,
            )
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _extract(response: Any) -> tuple[int, int]:
        prompt = completion = 0
        for key in ("token_usage", "usage"):
            usage = (getattr(response, "llm_output", None) or {}).get(key) or {}
            if usage:
                prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
                completion = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
                break
        if prompt or completion:
            return prompt, completion
        for gen_list in getattr(response, "generations", []) or []:
            for gen in (gen_list if isinstance(gen_list, list) else [gen_list]):
                meta = getattr(getattr(gen, "message", None), "usage_metadata", None)
                if meta:
                    prompt += int(meta.get("input_tokens") or meta.get("prompt_tokens") or 0)
                    completion += int(meta.get("output_tokens") or meta.get("completion_tokens") or 0)
        return prompt, completion


# ── Langfuse Scope Context Manager ────────────────────────────────────────────
# 用法：
#   with _langfuse_scope(context, run_name) as callbacks:
#       config = {..., "callbacks": callbacks}
#       await graph.ainvoke(state, config)
#
# 嵌套策略（与 LangGraphAdapter 完全对齐）：
#   优先路径：context.langfuse_callback 返回带显式 trace_id / parent_observation_id 的 handler
#   Fallback：bare CallbackHandler() + langfuse.start_as_current_observation 设置 OTel context
#             使 LangGraph span 正确嵌套在框架 _langfuse_observation 之下

@contextmanager
def _langfuse_scope(
    context: AgentContext,
    run_name: str,
) -> Iterator[list[Any]]:
    """
    Yields a callbacks list，可直接传入 LangGraph config["callbacks"]。

    同步 context manager，可在 async 函数里用 `with`（不需要 `async with`）。
    """
    callbacks: list[Any] = [_TokenCallback(context)]

    # ── 优先路径：context.langfuse_callback ─────────────────────────────────
    # 读取 LANGFUSE_SECRET_KEY / LANGFUSE_PUBLIC_KEY / LANGFUSE_BASE_URL，
    # 生成带 trace_id + parent_observation_id 的 handler。
    langfuse_cb = context.langfuse_callback
    if langfuse_cb is not None:
        callbacks.append(langfuse_cb)
        yield callbacks
        return

    # ── Fallback 路径：bare CallbackHandler + start_as_current_observation ──
    # 触发条件：LANGFUSE_BASE_URL 未设置但 LANGFUSE_HOST 已设置，
    #           或 by_framework_trace_langfuse 通过其他 env var 配置了 Langfuse。
    # 此时创建 bare CallbackHandler()（由 Langfuse SDK 自动读取 env vars），
    # 并通过 start_as_current_observation 将 OTel span context 设为框架 observation，
    # 使 LangGraph span 正确嵌套在 LangfusePlugin 创建的 agent.task span 下。
    try:
        langfuse_config = import_module("by_framework_trace_langfuse").LangfuseConfig
        if langfuse_config.from_env() is None:
            yield callbacks
            return

        callback_handler_cls = import_module("langfuse.langchain").CallbackHandler
        get_client = import_module("langfuse").get_client
    except (ImportError, AttributeError):
        yield callbacks
        return

    callbacks.append(callback_handler_cls())

    # _langfuse_observation 由 LangfusePlugin.on_task_start 设置在 context 上。
    # 有它才能做 parent nesting；没有则直接 yield（span 会挂在 trace 根部）。
    framework_obs = getattr(context, "_langfuse_observation", None)
    if framework_obs is None:
        yield callbacks
        return

    langfuse = get_client()
    with langfuse.start_as_current_observation(
        as_type="span",
        name=run_name,
        trace_context={
            "trace_id": context.trace_id,
            "parent_span_id": framework_obs.id,
        },
        metadata={
            "langfuse_session_id": context.session_id,
            "by_framework_trace_id": context.trace_id,
            "by_framework_message_id": context.message_id,
        },
    ):
        # 防止 OTel span 被 Langfuse 提升为 trace root
        try:
            from opentelemetry import trace as otel_trace
            span = otel_trace.get_current_span()
            if span and hasattr(span, "set_attribute"):
                span.set_attribute("langfuse.internal.as_root", False)
        except Exception:  # noqa: BLE001
            pass
        yield callbacks


# ── Worker 实现 ───────────────────────────────────────────────────────────────

@tool
def calculate(expression: str) -> str:
    """计算一个简单的数学表达式，例如 '2 + 3 * 4'。"""
    try:
        allowed = set("0123456789+-*/.(). ")
        if not all(c in allowed for c in expression):
            return "错误：仅支持基本算术运算"
        return str(eval(expression))  # noqa: S307
    except Exception as exc:  # noqa: BLE001
        return f"计算错误: {exc}"


class AgentState(dict):
    messages: Annotated[list[BaseMessage], add_messages]


class NativeTraceWorker(ByaiWorker):
    """
    原生 LangGraph Worker。

    继承 ByaiWorker（不使用 LangGraphWorker），在 process_command 中手动构建并运行图。
    Trace 接入通过 _langfuse_scope() context manager 统一处理，与业务逻辑解耦。
    """

    def get_agent_types(self) -> list[str]:
        return ["native-trace-agent"]

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
        raw = command.content
        if isinstance(raw, str):
            prompt_text = raw
        elif isinstance(raw, list) and raw:
            first = raw[0]
            prompt_text = (
                first.get("content", {}).get("text", "") or str(first)
                if isinstance(first, dict)
                else str(first)
            )
        else:
            prompt_text = str(raw or "")

        graph = self._build_graph()
        header = getattr(command, "header", None)
        run_name = f"{getattr(context, 'current_agent_id', 'langgraph')}:langgraph"

        full_response = ""

        # _langfuse_scope 是同步 context manager，在 async 函数里用 `with` 即可
        with _langfuse_scope(context, run_name) as callbacks:
            config = {
                "configurable": {"thread_id": context.message_id or context.session_id},
                "callbacks": callbacks,
                "run_name": run_name,
                "metadata": {
                    "langfuse_session_id": context.session_id,
                    "langfuse_user_id": getattr(header, "user_code", "") or "",
                    "by_framework_trace_id": context.trace_id,
                    "by_framework_message_id": context.message_id,
                },
            }

            async for event in graph.astream_events(
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
        redis_db=int(os.getenv("REDIS_DB", 0)),
        redis_username=os.getenv("REDIS_USERNAME"),
        redis_password=os.getenv("REDIS_PASSWORD"),
    )
