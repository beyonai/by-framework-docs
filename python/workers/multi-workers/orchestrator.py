import os
import json
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from dotenv import load_dotenv

from by_framework.worker import (
    ByaiAgentContext,
    ByaiAskAgentCommand,
    ByaiResumeCommand,
    ByaiWorker,
    run_worker,
)
from langgraph.graph.message import add_messages
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.tools import InjectedToolCallId, tool
from langchain_openai import ChatOpenAI

from byai_message_utils import extract_byai_text
from plugin import LoggingPlugin

# 加载环境变量
load_dotenv()


class AgentState(TypedDict):
    """LangGraph 状态定义"""
    messages: Annotated[list, add_messages]


class OrchestratorWorker(ByaiWorker):
    """
    诗歌分层创作工作室 (Worker A)。
    通过 interrupt + checkpoint 模式协调诗人、翻译和评论专家的工作。
    每个远程工具内部使用 interrupt() 挂起，框架 Resume 时自然唤醒。
    """

    def get_agent_types(self) -> List[str]:
        return ["orchestrator-agent"]

    def _get_llm(self):
        model_name = os.getenv("LLM_MODEL", "gpt-4o")
        llm_kwargs = {
            "model": model_name,
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL"),
            "streaming": True,
        }

        # 适配 MiniMax 的交错思维链 (Interleaved Thinking)
        if "minimax" in model_name.lower():
            self.logger.info(f"[Orchestrator] 🧠 检测到 MiniMax 模型，开启 reasoning_split=True")
            llm_kwargs["model_kwargs"] = {"extra_body": {"reasoning_split": True}}

        return ChatOpenAI(**llm_kwargs)

    def _format_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """将 LangChain 消息对象转换为 API 要求的字典格式"""
        system_prompt = (
            "你是一个高度专业的【文学创作工作组】协调员。\n"
            "你的团队包含以下专家：\n"
            "1. **诗人 (`invoke_poet_agent`)**: 负责一切诗词、文学创作任务。\n"
            "2. **翻译专家 (`invoke_translator_agent`)**: 负责将作品翻译成优雅的英文或其他语言。\n"
            "3. **评论专家 (`invoke_critic_agent`)**: 负责对作品进行深度文学鉴赏与风格点评。\n\n"
            "工作流程指导：\n"
            "- 如果用户要写诗，首先调用诗人。\n"
            "- 如果用户要求翻译或点评，请分别调用对应的专家工具。\n"
            "- 你可以根据用户需求组合多个工具（例如：写诗 -> 翻译 -> 点评）。\n"
            "- 所有专家返回后，你只需整合结果，给出一句充满温情的结束语。"
        )
        formatted = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}]
        for m in messages:
            if isinstance(m, HumanMessage):
                role = "user"
            elif isinstance(m, ToolMessage):
                role = "tool"
            elif isinstance(m, AIMessage):
                role = "assistant"
            else:
                role = "user"

            raw_text = m.content if hasattr(m, "content") else str(m)
            final_text = str(raw_text)

            # --- 根据角色决定 content 格式 ---
            if role == "tool":
                # OpenAI/MiniMax 要求 tool 消息的 content 是纯字符串
                msg_dict = {
                    "role": "tool",
                    "content": final_text,
                    "tool_call_id": m.tool_call_id,
                }
            elif role == "assistant":
                has_tool_calls = hasattr(m, "tool_calls") and m.tool_calls

                if not final_text.strip():
                    final_text = "\n"

                if has_tool_calls:
                    msg_dict = {"role": "assistant", "content": final_text}
                else:
                    msg_dict = {
                        "role": "assistant",
                        "content": [{"type": "text", "text": final_text}],
                    }

                # MiniMax 交错思维链
                reasoning = m.additional_kwargs.get("reasoning_details")
                if reasoning:
                    msg_dict["reasoning_details"] = reasoning

                # tool_calls 转换为 OpenAI API 标准格式
                if has_tool_calls:
                    api_tool_calls = []
                    for tc in m.tool_calls:
                        api_tool_calls.append(
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(
                                        tc["args"], ensure_ascii=False
                                    ),
                                },
                            },
                        )
                    msg_dict["tool_calls"] = api_tool_calls
            else:
                msg_dict = {"role": role, "content": [{"type": "text", "text": final_text}]}

            formatted.append(msg_dict)

        # --- 安全校验：剥离孤立的 tool_calls (无对应 tool response) ---
        all_tool_response_ids = {
            msg["tool_call_id"] for msg in formatted
            if msg.get("role") == "tool" and msg.get("tool_call_id")
        }
        for msg in formatted:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                orphaned = [tc for tc in msg["tool_calls"] if tc["id"] not in all_tool_response_ids]
                if orphaned:
                    self.logger.warning(
                        f"[Orchestrator] ⚠️ 剥离 {len(orphaned)} 个孤立 tool_call: "
                        f"{[tc['id'] for tc in orphaned]}"
                    )
                    msg["tool_calls"] = [tc for tc in msg["tool_calls"] if tc["id"] in all_tool_response_ids]
                    if not msg["tool_calls"]:
                        del msg["tool_calls"]

        return formatted

    # =====================================================================
    # 工具工厂方法：将 interrupt() 放在工具内部（参考已验证的正确模式）
    # =====================================================================

    def _make_remote_tool(
        self,
        context: ByaiAgentContext,
        tool_name: str,
        target_agent_type: str,
        description: str,
    ):
        """
        工厂方法：生成一个远程调用工具。
        核心模式：dispatch + interrupt（在工具函数内部），ToolNode 自动管理消息流。
        """
        from langgraph.types import interrupt

        @tool(tool_name, description=description)
        async def remote_tool(topic: str, tool_call_id: Annotated[str, InjectedToolCallId]):
            # 【Redis 幂等防抖】：checkpoint 恢复时不重复派发
            redis_key = f"dispatched_task:{context.session_id}:{tool_call_id}"
            is_dispatched = await context.redis.exists(redis_key)

            if not is_dispatched:
                self.logger.info(
                    "[Orchestrator] 🌐 派发远程任务 %s (ID: %s) -> %s",
                    tool_name,
                    tool_call_id,
                    target_agent_type,
                )
                await context.emit_chunk(
                    f"🎨 [Orchestrator] 已调度专家 {target_agent_type}，正在处理任务...",
                    content_type="text",
                )
                await context.call_agent(
                    target_agent_type=target_agent_type,
                    content=topic,
                )
                await context.redis.set(redis_key, 1, ex=86400)

            # 【正统 LangGraph 中断】：挂起工具执行，等待 ResumeCommand 唤醒
            result = interrupt(f"Waiting for {target_agent_type} to finish.")

            return f"专家 {target_agent_type} 的回复：\n{result}"

        return remote_tool

    def _build_graph(
        self,
        context: ByaiAgentContext,
        command: ByaiAskAgentCommand | ByaiResumeCommand,
    ):
        # --- 创建远程工具（每个工具内部含 interrupt） ---
        invoke_poet = self._make_remote_tool(
            context, "invoke_poet_agent", "poet-agent",
            "调度专业诗人进行诗歌创作。参数 topic 是创作主题。",
        )
        invoke_translator = self._make_remote_tool(
            context, "invoke_translator_agent", "translator-agent",
            "调度翻译专家将作品翻译成英文。参数 topic 是待翻译内容。",
        )
        invoke_critic = self._make_remote_tool(
            context, "invoke_critic_agent", "critic-agent",
            "调度评论专家进行深度文学鉴赏与风格点评。参数 topic 是待评论内容。",
        )

        # --- 本地工具（无 interrupt，即时返回） ---
        @tool
        async def evaluate_poem_style(poem_text: str):
            """【本地工具】：分析诗歌的体裁和押韵风格。"""
            await context.emit_chunk(
                "🔍 [Orchestrator] 本地工具：正在评估诗歌文学风格...",
                content_type="text",
            )
            if "山" in poem_text or "水" in poem_text:
                style = "山水田园诗，气韵生动"
            elif "剑" in poem_text or "战" in poem_text:
                style = "边塞风光，豪气干云"
            else:
                style = "抒情咏景，意境深远"
            return f"分析结果：{style}"

        tools = [invoke_poet, invoke_translator, invoke_critic, evaluate_poem_style]
        llm = self._get_llm().bind_tools(tools)

        # --- agent 节点：LLM 规划 ---
        async def agent_node(state: AgentState):
            msgs = self._format_messages(state["messages"])

            # 完整记录发送给 LLM 的消息列表（JSON 格式）
            self.logger.info(
                f"[Orchestrator] 📨 LLM 输入 ({len(msgs)} 条消息):\n"
                + json.dumps(msgs, ensure_ascii=False, indent=2)
            )

            resp = await llm.ainvoke(msgs)

            # 记录 LLM 返回
            resp_tc = resp.tool_calls if hasattr(resp, "tool_calls") and resp.tool_calls else []
            resp_content = resp.content if hasattr(resp, "content") else ""
            self.logger.info(f"[Orchestrator] 📩 LLM 输出: content={str(resp_content)[:200]}, "
                             f"tool_calls={json.dumps([{'id': tc.get('id'), 'name': tc.get('name')} for tc in resp_tc], ensure_ascii=False)}")

            # 打印思维链
            reasoning = resp.additional_kwargs.get("reasoning_details")
            if reasoning:
                thought = reasoning[0].get("text") if isinstance(reasoning, list) and reasoning else ""
                if thought:
                    self.logger.info(f"[Orchestrator] 💭推理中: {thought[:200]}...")

            return {"messages": [resp]}

        # --- 构建标准 ReAct 图：agent → tools → agent ---
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", ToolNode(tools))
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", "agent")

        # 持久化 Checkpointer
        from langgraph.checkpoint.memory import MemorySaver

        if not hasattr(self, "_memory_saver"):
            self._memory_saver = MemorySaver()

        return workflow.compile(checkpointer=self._memory_saver)

    async def process_command(
        self,
        command: ByaiAskAgentCommand | ByaiResumeCommand,
        context: ByaiAgentContext,
    ) -> Any:
        from langgraph.types import Command

        config = {"configurable": {"thread_id": context.session_id}}
        graph = self._build_graph(context, command)

        if isinstance(command, ByaiAskAgentCommand):
            await context.emit_chunk(
                "✍️ [文学工作室] 正式开始处理您的需求...",
                content_type="text",
            )

            # 演示：子步骤层级化日志
            async with context.sub_step("准备阶段") as (sub_id, parent_id):
                await context.emit_chunk("🔐 level 1 正在验证本地 Framework 运行环境...")
                await context.emit_chunk("✅ level 1 环境验证通过。")
                async with context.sub_step("准备阶段") as (sub_id, parent_id):
                    await context.emit_chunk("🔐 level 2 正在验证本地 Framework 运行环境...")
                    await context.emit_chunk("✅ level 2 环境验证通过。")
                    async with context.sub_step("准备阶段") as (sub_id, parent_id):
                        await context.emit_chunk("🔐 level 3 正在验证本地 Framework 运行环境...")
                        await context.emit_chunk("✅ level 3 环境验证通过。")

            # 首轮启动，遇到 interrupt 则图挂起返回
            user_input = extract_byai_text(command.content)
            final = await graph.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
            )

            last_msg = final["messages"][-1]
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                return "Tasks dispatched, graph suspended at interrupt."
            final_answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            await context.emit_chunk(f"\n💡 {final_answer}", content_type="text")
            return final_answer

        if isinstance(command, ByaiResumeCommand):
            # 获取专家返回的结果
            resume_data = (
                str(command.reply_data)
                if hasattr(command, "reply_data") and command.reply_data
                else "专家已完成任务。"
            )
            self.logger.info(f"[Orchestrator] 📥 收到 Resume，唤醒 LangGraph (数据长度: {len(resume_data)})...")

            # 【正统 LangGraph 唤醒】：携带结果打醒之前挂起的 interrupt
            final = await graph.ainvoke(Command(resume=resume_data), config=config)

            last_msg = final["messages"][-1]

            # 如果还有后续 tool_calls（LLM 决定继续调用其他工具），图会再次挂起
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                return "Resumed, but graph suspended again for next tool."

            final_answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

            if not final_answer or final_answer.strip() == "":
                final_answer = "所有专家已完成任务，工作流结束。"

            self.logger.info(f"[Orchestrator] ✨ 最终输出: {final_answer[:100]}...")
            await context.emit_chunk(f"\n💡 [文学协调员总结]：\n{final_answer}", content_type="text")
            return final_answer

        raise TypeError(f"Unsupported command type: {type(command)!r}")


if __name__ == "__main__":
    run_worker(
        OrchestratorWorker,
        worker_id="orchestrator-poet-manager-1",
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
        plugin_list=[LoggingPlugin()],
    )
