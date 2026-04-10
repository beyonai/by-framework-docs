"""
Claude Agent Worker (by-framework)
===================================

将 Claude Agent SDK（含 Agent Teams）封装为 by-framework GatewayWorker。

核心思路：
  - 使用 ClaudeSDKClient 维护持久化会话连接
  - Worker 负责：接收命令 → 调用 client.query() → 流式转发输出到前端
  - Claude Code 内部自动管理工具调用和子代理（Agent Teams）
  - 通过 ClaudeSDKClient 的 session_id 参数自然支持多会话隔离，无需 Redis 映射

用法：
  uv run python claude_agent_worker.py

环境变量：
  - CLAUDE_AGENT_CWD: Claude Code 工作目录（默认当前目录）
  - CLAUDE_MAX_TURNS: 最大交互轮次（默认 200）
  - CLAUDE_SYSTEM_PROMPT: 自定义系统提示词（可选）
  - CLAUDE_CLI_PATH: Claude CLI 路径（可选，SDK 默认自带）
"""

import os
import json
import time
from typing import Any, List, Optional
from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand, AskAgentCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker
from by_framework_history_postgres import PostgresHistoryBackend

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

load_dotenv()


class ClaudeAgentWorker(GatewayWorker):
    """
    Claude Agent SDK Worker（ClaudeSDKClient 模式）。

    使用 ClaudeSDKClient 维护持久化会话，支持多轮对话的上下文续接。
    通过 session_id 参数隔离不同 framework session 的对话上下文，
    无需手动管理 Redis session 映射。

    会话管理：
    - ClaudeSDKClient 内部维护多个 session 的对话上下文
    - 同一 framework session_id 的多次请求自动续接 Claude 对话
    - 支持通过 client.interrupt() 中断正在执行的任务
    """

    # ClaudeSDKClient 实例（懒初始化，进程级复用）
    _client: Optional[ClaudeSDKClient] = None

    def get_agent_types(self) -> List[str]:
        return ["claude-agent"]

    def _build_options(self) -> ClaudeAgentOptions:
        """构建 ClaudeAgentOptions 全局配置"""
        cwd = os.path.abspath(os.getenv("CLAUDE_AGENT_CWD", "."))
        max_turns = int(os.getenv("CLAUDE_MAX_TURNS", "200"))
        system_prompt = os.getenv("CLAUDE_SYSTEM_PROMPT")
        cli_path = os.getenv("CLAUDE_CLI_PATH")

        opts = {
            "permission_mode": "bypassPermissions",
            "cwd": cwd,
            "env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"},
            "max_turns": max_turns,
        }

        if system_prompt:
            opts["system_prompt"] = system_prompt

        if cli_path:
            opts["cli_path"] = cli_path

        return ClaudeAgentOptions(**opts)

    async def _ensure_client(self) -> ClaudeSDKClient:
        """确保 ClaudeSDKClient 已连接（懒初始化）

        客户端在首次调用时创建并连接，后续请求复用同一连接。
        若连接异常断开，会自动重建。
        """
        if self._client is None:
            options = self._build_options()
            self._client = ClaudeSDKClient(options)
            await self._client.connect()
            self.logger.info(
                f"[ClaudeAgent] 🔌 ClaudeSDKClient 已连接 (cwd={options.cwd})"
            )
        return self._client

    async def _reset_client(self) -> None:
        """断开并重置客户端（用于异常恢复）"""
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
            self.logger.info("[ClaudeAgent] 🔄 ClaudeSDKClient 已重置")

    def _extract_tool_result_text(self, content) -> str:
        """从 ToolResultBlock 的 content 中提取文本"""
        if not content:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                elif hasattr(item, "text"):
                    text = getattr(item, "text", None)
                else:
                    text = None
                if text:
                    parts.append(text)
            return "\n".join(parts)
        return str(content)

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        """
        处理来自 Gateway 的命令。

        使用 ClaudeSDKClient 的 session_id 参数自然隔离不同 framework session：
        - 同一 session_id 的多次 query() 自动续接对话上下文
        - 不同 session_id 之间互不干扰
        - 取消时调用 client.interrupt() 中断 Claude 执行
        """
        if not isinstance(command, AskAgentCommand):
            self.logger.warning("[ClaudeAgent] 收到非 AskAgent 命令，忽略")
            return "IGNORED"

        prompt = str(command.content)
        session_id = context.session_id

        # --- 确保 Client 就绪 ---
        client = await self._ensure_client()

        self.logger.info(f"[ClaudeAgent] 🚀 启动任务 (session={session_id}): {prompt[:100]}...")

        await context.emit_chunk(
            "🤖 Claude Agent 已上线，正在处理您的请求...\n",
            content_type="text"
        )

        final_result = ""
        task_count = 0
        start_time = time.time()

        try:
            # 发送查询，使用 framework session_id 隔离 Claude 对话上下文
            await client.query(prompt, session_id=session_id)

            # 流式接收当前查询的响应
            async for msg in client.receive_response():
                # --- 检查取消请求 ---
                try:
                    await context.check_cancelled()
                except Exception:
                    # 框架请求取消 → 中断 Claude 执行
                    self.logger.info("[ClaudeAgent] ⏹️ 收到取消请求，中断 Claude 执行")
                    await client.interrupt()
                    raise

                # =============================================
                # AssistantMessage：流式内容 + 工具调用
                # =============================================
                if isinstance(msg, AssistantMessage):
                    is_subagent = (
                        hasattr(msg, "parent_tool_use_id")
                        and msg.parent_tool_use_id
                    )

                    if not hasattr(msg, "content") or not msg.content:
                        continue

                    for block in msg.content:
                        # ----- 1. 文本输出 → 流式推送到前端 -----
                        if isinstance(block, TextBlock):
                            text = block.text
                            if text and text.strip():
                                if is_subagent:
                                    # 子代理输出 → 推理日志
                                    await context.emit_chunk(
                                        text,
                                        content_type="text",
                                        event_type="REASONING_LOG_DELTA"
                                    )
                                else:
                                    # 主代理输出 → 正式回答
                                    await context.emit_chunk(
                                        text,
                                        content_type="text"
                                    )

                        # ----- 2. 工具调用 → 推理日志 -----
                        elif isinstance(block, ToolUseBlock):
                            tool_name = block.name
                            tool_input = block.input if hasattr(block, "input") else {}

                            if tool_name == "Task":
                                # Agent Teams 子任务派发
                                task_count += 1
                                sa_type = tool_input.get("subagent_type", "general")
                                desc = tool_input.get("description", "subtask")
                                prompt_preview = str(tool_input.get("prompt", ""))[:120]

                                self.logger.info(
                                    f"[ClaudeAgent] 🚀 子任务 #{task_count}: [{sa_type}] {desc}"
                                )
                                await context.emit_chunk(
                                    f"\n🚀 派发子任务 #{task_count} [{sa_type}]: {desc}\n",
                                    content_type="text",
                                    event_type="REASONING_LOG_DELTA"
                                )
                                if prompt_preview:
                                    await context.emit_chunk(
                                        f"   📝 {prompt_preview}...\n",
                                        content_type="text",
                                        event_type="REASONING_LOG_DELTA"
                                    )
                            else:
                                # 其他工具（Read/Write/Bash 等）
                                compact_input = json.dumps(tool_input, default=str, ensure_ascii=False)
                                if len(compact_input) > 150:
                                    compact_input = compact_input[:150] + "..."
                                self.logger.info(f"[ClaudeAgent] 🔧 {tool_name}: {compact_input}")
                                await context.emit_chunk(
                                    f"🔧 {tool_name}\n",
                                    content_type="text",
                                    event_type="REASONING_LOG_DELTA"
                                )

                        # ----- 3. 工具结果 → 推理日志（摘要） -----
                        elif isinstance(block, ToolResultBlock):
                            result_text = self._extract_tool_result_text(
                                block.content if hasattr(block, "content") else None
                            )
                            if result_text:
                                preview = result_text[:200] + "..." if len(result_text) > 200 else result_text
                                await context.emit_chunk(
                                    f"📋 返回: {preview}\n",
                                    content_type="text",
                                    event_type="REASONING_LOG_DELTA"
                                )

                        # ----- 4. 思维链 → 推理日志 -----
                        elif getattr(block, "type", None) == "thinking":
                            thinking = getattr(block, "thinking", "")
                            if thinking:
                                preview = thinking[:300] + "..." if len(thinking) > 300 else thinking
                                await context.emit_chunk(
                                    f"💭 {preview}\n",
                                    content_type="text",
                                    event_type="REASONING_LOG_DELTA"
                                )

                # =============================================
                # ResultMessage：任务完成
                # =============================================
                elif isinstance(msg, ResultMessage):
                    result_text = getattr(msg, "result", "")
                    cost = getattr(msg, "cost_usd", None)
                    status = getattr(msg, "subtype", "unknown")

                    if result_text:
                        final_result = result_text

                    self.logger.info(
                        f"[ClaudeAgent] ✅ 任务完成 (status={status}, cost=${(cost or 0):.4f})"
                    )

        except Exception as e:
            self.logger.error(f"[ClaudeAgent] ❌ Claude Agent SDK 执行异常: {e}")
            await context.emit_chunk(
                f"\n❌ 执行异常: {str(e)}\n",
                content_type="text"
            )
            # 连接级异常时重置客户端，以便下次重建
            if not isinstance(e, (KeyboardInterrupt, SystemExit)):
                await self._reset_client()
            raise

        # --- 最终总结 ---
        duration = time.time() - start_time
        self.logger.info(
            f"[ClaudeAgent] 📊 总计: {duration:.1f}s, 子任务: {task_count}"
        )

        return final_result or "Task completed"


if __name__ == "__main__":
    run_worker(
        ClaudeAgentWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "claude-agent-worker-1"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
        history_backend=PostgresHistoryBackend(dsn=os.getenv("BYAI_HISTORY_DSN", "postgresql://postgres:postgres@localhost:5432/postgres"))
    )
