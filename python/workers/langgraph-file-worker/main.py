import os
import asyncio
from typing import Annotated, Any, List
from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.core.protocol.events import StreamChunkEvent
from by_framework.worker import AgentContext, GatewayWorker, run_worker
from by_framework.core.runtime.file_manager import LocalFileStorage
from by_framework_history_byclaw import ByClawHistoryBackend
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, add_messages
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

# 加载 .env 文件中的环境变量
load_dotenv()


class LangGraphFileWorker(GatewayWorker):
    """
    基于 LangGraph 和 By-Framework 实现的文件管理智能体。
    它将 `file_manager` 包装成了 langgraph 的 tools。
    """

    def get_agent_types(self) -> List[str]:
        """返回此 Worker 支持的智能体类型列表。"""
        return ["langgraph-file-agent"]

    async def process_command(
        self, command: GatewayCommand, context: AgentContext
    ) -> Any:
        """处理来自 Gateway 的命令。"""
        self.logger.info(f"Processing command: {command.header.message_id}")

        file_manager = context.agent_runtime_state.session_manager.file_manager
        session_id = file_manager.session_id

        # --- 将文件管理 API 包装成 LangChain Tools ---
        @tool(description="""Read content from a file in the workspace.
            - Your session_id is: {session_id}
            - Example path: sessions/{session_id}/file.txt
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/'.
            - Traversal: '../' is prohibited.
            - Images: Returns metadata (type, base64) for common image extensions.
            """.format(session_id=session_id))
        async def read_file(filename: str, offset: int = 0, limit: int | None = None, encoding: str = "utf-8") -> str:
            try:
                response = await file_manager.read_file(filename, offset=offset, limit=limit, encoding=encoding)
                if response["success"]:
                    data = response["data"]
                    if isinstance(data, dict):
                        import json
                        return f"SUCCESS (Media Detached): {json.dumps(data, ensure_ascii=False)}"
                    return str(data)
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to read file: {e}"

        @tool(description="""Edit a file by replacing a substring.
            - Your session_id is: {session_id}
            - Example path: sessions/{session_id}/file.txt
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/'.
            Use this for selective modifications. 'old_string' must match exactly.
            - Success response includes the number of occurrences replaced.
            """.format(session_id=session_id))
        async def edit_file(filename: str, old_string: str, new_string: str, replace_all: bool = False, encoding: str = "utf-8") -> str:
            try:
                response = await file_manager.edit_file(filename, old_string, new_string, replace_all=replace_all, encoding=encoding)
                if response["success"]:
                    occurrences = response["data"].get("occurrences", 0)
                    return f"{response['message']} (Replaced {occurrences} occurrences)"
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to edit file: {e}"

        @tool(description="""Search for 'pattern' in files within the sandboxed workspace.
            - Your session_id is: {session_id}
            - ONLY these root paths are allowed:
              * sessions/{session_id}/   (your private session files)
              * public/                   (shared public files)
            - glob_pattern MUST start with one of the above roots, e.g., 'sessions/{session_id}/*.py' or 'public/*.md'
            - DO NOT use absolute paths or paths outside these roots.
            """.format(session_id=session_id))
        async def grep_files(pattern: str, glob_pattern: str = "*") -> str:
            try:
                response = await file_manager.grep_files(pattern, glob_pattern)
                if response["success"]:
                    matches = response["data"]
                    if not matches:
                        return "No matches found."
                    result = []
                    for m in matches:
                        result.append(f"{m['file']}:{m['line_number']}: {m['content']}")
                    return f"Found {len(matches)} matches:\n" + "\n".join(result)
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to search files: {e}"

        @tool(description="""Write content to a file in the workspace.
            - Your session_id is: {session_id}
            - Example path: sessions/{session_id}/file.txt
            - Path prefix: Must start with 'sessions/{session_id}/' or 'public/'.
            - Traversal: '../' is prohibited.
            """.format(session_id=session_id))
        async def write_file(filename: str, content: str, encoding: str = "utf-8") -> str:
            try:
                response = await file_manager.write_file(filename, content, encoding=encoding)
                if response["success"]:
                    return response["message"]
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to write file: {e}"

        @tool(description="""List files and directories in the sandboxed workspace.
            - Your session_id is: {session_id}
            - ONLY these root paths are allowed:
              * sessions/{session_id}/   (your private session files)
              * public/                   (shared public files)
            - directory MUST start with 'sessions/{session_id}/' or be 'public/' or empty for root
            - Examples: 'sessions/{session_id}', 'sessions/{session_id}/subdir', 'public', ''
            """.format(session_id=session_id))
        async def list_files(directory: str = "") -> str:
            try:
                response = await file_manager.list_files(directory)
                if response["success"]:
                    items = response["data"]
                    if not items:
                        return "(Empty directory)"
                    return "\n".join(items)
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to list files: {e}"

        @tool(description="""Find files matching a glob pattern in the sandboxed workspace.
            - Your session_id is: {session_id}
            - ONLY these root paths are allowed:
              * sessions/{session_id}/   (your private session files)
              * public/                   (shared public files)
            - pattern MUST start with one of the above roots, e.g., 'sessions/{session_id}/**/*.py' or 'public/**/*.md'
            - Supports * (single dir) and ** (recursive).
            - DO NOT use absolute paths or paths outside these roots.
            """.format(session_id=session_id))
        async def glob_files(pattern: str) -> str:
            try:
                response = await file_manager.glob_files(pattern)
                if response["success"]:
                    data = response["data"]
                    # Handle evicted response (large results stored to file)
                    if isinstance(data, dict) and data.get("evicted"):
                        return f"{response['message']}\nPreview: {data.get('preview', '')}\nFull results stored at: {data.get('path', '')}"
                    items = data if isinstance(data, list) else []
                    if not items:
                        return "No files matched the pattern."
                    return "\n".join(items)
                return f"Error: {response['error']}"
            except Exception as e:
                return f"Failed to glob files: {e}"

        tools = [read_file, edit_file, grep_files, write_file, list_files, glob_files]

        # 获取 LLM
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

        # 构建拥有工具能力的 react agent
        agent_executor = create_react_agent(llm, tools)

        # 因为需要处理多轮上下文，我们从 session 中获取历史
        # history = await context.agent_runtime_state.session_manager.history.get_history()
        
        # 提取历史消息 (简单实现：过滤出 user 和 assistant 的消息)
        messages = []
        # for msg in history:
        #     role = msg.get("role")
        #     content = msg.get("content")
        #     if role == "user":
        #         messages.append(("human", content))
        #     elif role == "assistant":
        #         messages.append(("ai", content))
                
        # 加上当前用户的新内容
        messages.append(("human", str(command.content)))

        initial_state = {"messages": messages}

        full_response = ""
        # 流式执行 graph
        async for event in agent_executor.astream_events(initial_state, version="v2"):
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
                import json
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
                    content=str(tool_output),
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
        storage=LocalFileStorage(base_dir="/Users/xiaozhongcheng/workspace")
        # history_backend=ByClawHistoryBackend(base_url="http://10.45.134.185:8086")
    )
