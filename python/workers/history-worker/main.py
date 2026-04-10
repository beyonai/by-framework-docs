import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.core.runtime.history import InMemoryHistoryBackend
from by_framework.worker import AgentContext, GatewayWorker, run_worker
from by_framework_history_byclaw import ByClawHistoryBackend
from by_framework_history_postgres import PostgresHistoryBackend
from dotenv import load_dotenv
from langchain_core.messages import AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


HistoryBackendType = Literal["in_memory", "byclaw", "postgres"]


@dataclass(frozen=True)
class HistoryWorkerConfig:
    worker_id: str = "history-worker"
    capability: str = "history_worker"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_username: str | None = None
    redis_password: str | None = None
    workspace_dir: str = "/tmp/by-framework-samples"
    consumer_group: str = "agent_engines"
    history_backend: HistoryBackendType = "in_memory"
    byclaw_base_url: str | None = None
    postgres_dsn: str | None = None
    llm_model: str = "gpt-4o"
    openai_api_key: str | None = None
    openai_base_url: str | None = None

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> "HistoryWorkerConfig":
        load_dotenv(env_path or Path(__file__).with_name(".env"), override=False)
        return cls(
            worker_id=os.environ.get("WORKER_ID", "history-worker"),
            capability=os.environ.get("WORKER_CAPABILITY", "history_worker"),
            redis_host=os.environ.get("REDIS_HOST", "localhost"),
            redis_port=int(os.environ.get("REDIS_PORT", "6379")),
            redis_db=int(os.environ.get("REDIS_DB", "0")),
            redis_username=os.environ.get("REDIS_USERNAME"),
            redis_password=os.environ.get("REDIS_PASSWORD"),
            workspace_dir=os.environ.get("WORKSPACE_DIR", "/tmp/by-framework-samples"),
            consumer_group=os.environ.get("CONSUMER_GROUP", "agent_engines"),
            history_backend=os.environ.get("HISTORY_BACKEND", "in_memory"),
            byclaw_base_url=os.environ.get("BYCLAW_HISTORY_BASE_URL"),
            postgres_dsn=os.environ.get("BYAI_HISTORY_PG_DSN"),
            llm_model=os.environ.get("LLM_MODEL", "gpt-4o"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            openai_base_url=os.environ.get("OPENAI_BASE_URL"),
        )


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def build_history_backend(config: HistoryWorkerConfig) -> Any:
    if config.history_backend == "in_memory":
        return InMemoryHistoryBackend()
    if config.history_backend == "byclaw":
        if not config.byclaw_base_url:
            raise ValueError("BYCLAW_HISTORY_BASE_URL is required for byclaw backend")
        return ByClawHistoryBackend(base_url=config.byclaw_base_url)
    if config.history_backend == "postgres":
        if not config.postgres_dsn:
            raise ValueError("BYAI_HISTORY_PG_DSN is required for postgres backend")
        return PostgresHistoryBackend(dsn=config.postgres_dsn)
    raise ValueError(f"unsupported history backend: {config.history_backend}")


class HistoryWorker(GatewayWorker):
    def __init__(self, *, capability: str = "history_worker", llm_config: HistoryWorkerConfig, **kwargs):
        super().__init__(**kwargs)
        self._capability = capability
        self._llm_config = llm_config

    def get_agent_types(self) -> list[str]:
        return [self._capability]

    def _get_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self._llm_config.llm_model,
            api_key=self._llm_config.openai_api_key,
            base_url=self._llm_config.openai_base_url,
            streaming=True,
        )

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        llm = self._get_llm()

        async def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
            response = await llm.ainvoke(state["messages"])
            return {"messages": [response]}

        workflow.add_node("agent", call_model)
        workflow.add_edge(START, "agent")
        workflow.add_edge("agent", END)
        return workflow.compile()

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        self.logger.info("Processing command: %s", command.header.message_id)

        history_items = await context.agent_runtime_state.session_manager.history.get_history(limit=10)
        history_text = "\n".join(
            f"{item.get('role', 'unknown')}: {item.get('content', '')}"
            for item in history_items
            if item.get("content")
        )
        system_prompt = (
            "You are a sample history-aware assistant. "
            "Use the conversation history when it is relevant to answer consistently."
        )
        if history_text:
            system_prompt += f"\n\nRecent history:\n{history_text}"

        initial_state = {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=command.content),
            ]
        }

        graph = self._build_graph()
        full_response = ""
        async for event in graph.astream(initial_state, stream_mode="messages"):
            message, _metadata = event
            if isinstance(message, AIMessageChunk) and message.content:
                full_response += message.content
                await context.emit_chunk(message.content, content_type="1002")

        return full_response


def main() -> None:
    config = HistoryWorkerConfig.from_env()
    history_backend = build_history_backend(config)
    run_worker(
        HistoryWorker,
        worker_id=config.worker_id,
        redis_host=config.redis_host,
        redis_port=config.redis_port,
        redis_db=config.redis_db,
        redis_username=config.redis_username,
        redis_password=config.redis_password,
        workspace_dir=config.workspace_dir,
        consumer_group=config.consumer_group,
        history_backend=history_backend,
        capability=config.capability,
        llm_config=config,
    )


if __name__ == "__main__":
    main()
