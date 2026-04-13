import os
import json
from typing import Any, List, Literal
from dotenv import load_dotenv
from prompting import build_file_agent_system_prompt

from by_framework.core.protocol.commands import (
    GatewayCommand,
    AskAgentCommand,
    ResumeCommand,
)
from by_framework.core.protocol.events import StreamChunkEvent
from by_framework.worker import AgentContext, run_worker, ByaiWorker
from by_framework.core.runtime.filestore.local import LocalFileStorage
from by_framework_history_postgres import PostgresHistoryBackend
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool

# 加载 .env 文件中的环境变量
load_dotenv()


ScopeName = Literal["private", "shared"]


def format_path_entries(entries: list[dict[str, Any]]) -> str:
    """Render structured path entries for human-readable tool output."""

    return "\n".join(
        "{path} ({absolute_path})".format(
            path=entry.get("path", ""),
            absolute_path=entry.get("absolute_path", ""),
        ).strip()
        for entry in entries
    )


class LangGraphFileWorker(ByaiWorker):
    """
    基于 LangGraph 和 By-Framework 实现的文件管理智能体。
    它将 `file_manager` 包装成了 langgraph 的 tools。
    支持 checkpoint + 内存存储，实现同 session 的多轮对话记忆。
    """

    def get_agent_types(self) -> List[str]:
        """返回此 Worker 支持的智能体类型列表。"""
        return ["langgraph-file-agent"]

    def _get_memory_saver(self) -> MemorySaver:
        """获取或创建 MemorySaver 单例，用于 checkpoint 持久化。"""
        if not hasattr(self, "_memory_saver"):
            self._memory_saver = MemorySaver()
        return self._memory_saver

    async def process_command(
        self, command: GatewayCommand, context: AgentContext
    ) -> Any:
        """处理来自 Gateway 的命令。"""
        self.logger.info(f"Processing command: {command.header.message_id}")

        session_manager = context.agent_runtime_state.session_manager
        session_id = session_manager.file_manager.session_id
        system_prompt = build_file_agent_system_prompt(session_id)

        def get_file_manager(scope: ScopeName):
            if scope == "shared":
                return session_manager.shared_file_manager
            return session_manager.private_file_manager

        @tool(name_or_callable="read_file", description="""Read content from a file.
            - Your session_id is: {session_id}
            - Example path: sessions/{session_id}/file.txt
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/'.
            - Use scope='private' by default.
            - Use scope='shared' only for cross-agent shared files.
            - Traversal: '../' is prohibited.
            - Images: Returns metadata (type, base64) for common image extensions.
            """.format(session_id=session_id))
        async def read_file(
            filename: str,
            scope: ScopeName = "private",
            offset: int = 0,
            limit: int | None = None,
            encoding: str = "utf-8",
        ) -> str:
            file_manager = get_file_manager(scope)
            try:
                response = await file_manager.read_file(
                    filename,
                    offset=offset,
                    limit=limit,
                    encoding=encoding,
                )
                if response["success"]:
                    data = response["data"]
                    if isinstance(data, dict):
                        return json.dumps(data, ensure_ascii=False, indent=2)
                    return str(data)
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to read file: {e}"

        @tool(name_or_callable="edit_file", description="""Edit a file by replacing a substring.
            - Your session_id is: {session_id}
            - Example path: sessions/{session_id}/file.txt
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/'.
            - Use scope='private' by default.
            - Use scope='shared' only for cross-agent shared files.
            Use this for selective modifications. 'old_string' must match exactly.
            """.format(session_id=session_id))
        async def edit_file(
            filename: str,
            old_string: str,
            new_string: str,
            scope: ScopeName = "private",
            replace_all: bool = False,
            encoding: str = "utf-8",
        ) -> str:
            file_manager = get_file_manager(scope)
            try:
                response = await file_manager.edit_file(
                    filename,
                    old_string,
                    new_string,
                    replace_all=replace_all,
                    encoding=encoding,
                )
                if response["success"]:
                    occurrences = response["data"].get("occurrences", 0)
                    return f"{response['message']} (Replaced {occurrences} occurrences)"
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to edit file: {e}"

        @tool(name_or_callable="grep_files", description="""Search for text in files.
            - Your session_id is: {session_id}
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/'.
            - Use scope='private' by default.
            - Use scope='shared' only for cross-agent shared files.
            - Use output_mode='files_with_matches' when you want to save tokens and inspect matching files later with read_file.
            """.format(session_id=session_id))
        async def grep_files(
            pattern: str,
            scope: ScopeName = "private",
            glob_pattern: str = "*",
            output_mode: str = "content",
        ) -> str:
            file_manager = get_file_manager(scope)
            try:
                response = await file_manager.grep_files(
                    pattern,
                    glob_pattern,
                    output_mode=output_mode,
                )
                if response["success"]:
                    data = response["data"]
                    if isinstance(data, dict) and data.get("evicted"):
                        return (
                            f"{response['message']}\n"
                            f"Preview: {data.get('preview', '')}\n"
                            f"Full results stored at: {data.get('path', '')}\n"
                            f"Absolute path: {data.get('absolute_path', '')}"
                        )
                    if not data:
                        return "No matches found."
                    if output_mode == "files_with_matches":
                        return format_path_entries(data)
                    if output_mode == "count":
                        return json.dumps(data, ensure_ascii=False, indent=2)
                    return "Found {count} matches:\n{lines}".format(
                        count=len(data),
                        lines="\n".join(
                            f"{match['path']}:{match['line_number']}: {match['content']} ({match.get('absolute_path', '')})"
                            for match in data
                        ),
                    )
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to search files: {e}"

        @tool(name_or_callable="write_file", description="""Write content to a file.
            - Your session_id is: {session_id}
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/'.
            - Use scope='private' by default.
            - Use scope='shared' only for cross-agent shared files.
            """.format(session_id=session_id))
        async def write_file(
            filename: str,
            content: str,
            scope: ScopeName = "private",
            encoding: str = "utf-8",
        ) -> str:
            file_manager = get_file_manager(scope)
            try:
                response = await file_manager.write_file(
                    filename,
                    content,
                    encoding=encoding,
                )
                if response["success"]:
                    details = response.get("data", {})
                    bytes_written = details.get("bytes_written")
                    if bytes_written is not None:
                        return f"{response['message']} ({bytes_written} bytes written)"
                    return response["message"]
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to write file: {e}"

        @tool(name_or_callable="list_files", description="""List files and directories.
            - Your session_id is: {session_id}
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/' or be empty for root.
            - Use scope='private' by default.
            - Use scope='shared' only for cross-agent shared files.
            """.format(session_id=session_id))
        async def list_files(directory: str = "", scope: ScopeName = "private") -> str:
            file_manager = get_file_manager(scope)
            try:
                response = await file_manager.list_files(directory)
                if response["success"]:
                    items = response["data"]
                    if not items:
                        return "(Empty directory)"
                    return format_path_entries(items)
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to list files: {e}"

        @tool(name_or_callable="delete_file", description="""Delete a file or directory.
            - Your session_id is: {session_id}
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/'.
            - Use scope='private' by default.
            - Use scope='shared' only for cross-agent shared files.
            """.format(session_id=session_id))
        async def delete_file(filename: str, scope: ScopeName = "private") -> str:
            file_manager = get_file_manager(scope)
            try:
                response = await file_manager.delete_file(filename)
                if response["success"]:
                    return response["message"]
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to delete file: {e}"

        @tool(name_or_callable="glob_files", description="""Find files matching a glob pattern.
            - Your session_id is: {session_id}
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/'.
            - Use scope='private' by default.
            - Use scope='shared' only for cross-agent shared files.
            - Supports * (single dir) and ** (recursive).
            """.format(session_id=session_id))
        async def glob_files(pattern: str, scope: ScopeName = "private") -> str:
            file_manager = get_file_manager(scope)
            try:
                response = await file_manager.glob_files(pattern)
                if response["success"]:
                    data = response["data"]
                    if isinstance(data, dict) and data.get("evicted"):
                        return (
                            f"{response['message']}\n"
                            f"Preview: {data.get('preview', '')}\n"
                            f"Full results stored at: {data.get('path', '')}\n"
                            f"Absolute path: {data.get('absolute_path', '')}"
                        )
                    items = data if isinstance(data, list) else []
                    if not items:
                        return "No files matched the pattern."
                    return format_path_entries(items)
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to glob files: {e}"

        tools = [
            read_file,
            edit_file,
            grep_files,
            write_file,
            list_files,
            glob_files,
            delete_file,
        ]

        # 获取 LLM
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

        # 构建拥有工具能力的 react agent，并挂载 checkpoint
        # 使用 prompt 注入系统提示词（适配当前版本的 create_react_agent）
        agent_executor = create_react_agent(
            llm, 
            tools, 
            checkpointer=self._get_memory_saver(),
            prompt=system_prompt
        )

        # 使用 session_id 作为 thread_id，实现同 session 多轮对话记忆
        config = {"configurable": {"thread_id": context.session_id}}

        if isinstance(command, ResumeCommand):
            # ResumeCommand：从 checkpoint 恢复中断的任务
            from langgraph.types import Command as LGCommand
            resume_data = (
                str(command.reply_data)
                if hasattr(command, "reply_data") and command.reply_data
                else "任务已完成。"
            )
            self.logger.info(
                f"Resume received, waking LangGraph (data length: {len(resume_data)})..."
            )
            final = await agent_executor.ainvoke(
                LGCommand(resume=resume_data), config=config
            )
            last_msg = final["messages"][-1]
            final_answer = (
                last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            )
            if final_answer:
                await context.emit_chunk(final_answer, content_type="1002")
            return final_answer or "任务已恢复完成。"

        # AskAgentCommand 或普通命令：首轮 / 多轮对话
        # Checkpoint 会自动检索之前的对话历史，我们只需传递当前的新消息
        initial_state = {"messages": [("human", str(command.content))]}

        full_response = ""
        # 流式执行 graph（带 checkpoint config）
        async for event in agent_executor.astream_events(
            initial_state, version="v2", config=config
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    full_response += chunk.content
                    # 发送流式分片到前端
                    await context.emit_chunk(chunk.content, content_type="1002")
            elif kind == "on_tool_start":
                tool_name = event["name"]
                tool_input = event["data"].get("input")
                chunk_event = StreamChunkEvent(
                    tool_calls=[{
                        "id": event.get("run_id", "local_call"),
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_input, ensure_ascii=False) if isinstance(tool_input, dict) else str(tool_input)
                        }
                    }]
                )
                await context.emit_chunk(chunk_event)
            elif kind == "on_tool_end":
                tool_name = event["name"]
                tool_output = event["data"].get("output")
                chunk_event = StreamChunkEvent(
                    role="tool",
                    tool_responses=[{
                        "tool_call_id": event.get("run_id", "local_call"),
                        "content": str(tool_output)
                    }],
                    metadata={"tool_name": tool_name}
                )
                await context.emit_chunk(chunk_event)

        return full_response


if __name__ == "__main__":
    # 使用 by-framework 提供的快捷入口启动 Worker
    run_worker(
        LangGraphFileWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "langgraph-file-worker-1"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
        storage=LocalFileStorage(base_dir="/Users/xiaozhongcheng/workspace"),
        history_backend=PostgresHistoryBackend(dsn=os.getenv("BYAI_HISTORY_DSN", "postgresql://postgres:postgres@localhost:5432/postgres"))
    )
