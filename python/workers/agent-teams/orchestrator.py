import os
import json
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from dotenv import load_dotenv

from by_framework.core.protocol.commands import (
    GatewayCommand, 
    AskAgentCommand, 
    ResumeCommand
)
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.tools import tool

load_dotenv()


class AgentState(TypedDict):
    """LangGraph 状态定义"""
    messages: Annotated[list, add_messages]
    task_group_id: Optional[str]
    tool_call_id_map: Dict[str, str]


class HierarchicalOrchestrator(GatewayWorker):
    """
    软件研发中心 - 首席协调官 (Top Supervisor)
    使用 LangGraph interrupt + checkpoint 实现异步专家组调度。
    """

    def get_agent_types(self) -> List[str]:
        return ["orchestrator-agent"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    def _format_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """适配严苛网关要求的多模态格式转换（含 tool_calls 安全校验）"""
        system_prompt = (
            "你是一个软件研发中心的首席协调官。\n"
            "你的职责是根据用户需求，调度合适的专家团队：\n"
            "1. 如果需要技术调研、方案比较或搜索信息，请调用 `call_research_team`。\n"
            "2. 如果需要具体编写代码、实现功能或修复 Bug，请调用 `call_coder_team`。\n"
            "3. **并行能力**: 如果用户的需求包含多个独立子项，系统会自动并行执行它们。\n"
            "4. 当所有子团队完成工作后，请汇总他们的成果给用户一个完美的总结。"
        )
        formatted = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}]

        for m in messages:
            if isinstance(m, HumanMessage): role = "user"
            elif isinstance(m, ToolMessage): role = "tool"
            elif isinstance(m, AIMessage): role = "assistant"
            else: role = "user"

            raw_text = m.content if hasattr(m, "content") else str(m)
            final_text = str(raw_text)

            # --- 根据角色决定 content 格式 ---
            if role == "tool":
                # OpenAI/MiniMax 要求 tool 消息的 content 是纯字符串
                msg_dict = {
                    "role": "tool",
                    "content": final_text,
                    "tool_call_id": m.tool_call_id
                }
            elif role == "assistant":
                has_tool_calls = hasattr(m, "tool_calls") and m.tool_calls

                if not final_text.strip():
                    final_text = "\n"

                # 有 tool_calls 时 content 用纯字符串
                if has_tool_calls:
                    msg_dict = {"role": "assistant", "content": final_text}
                else:
                    msg_dict = {"role": "assistant", "content": [{"type": "text", "text": final_text}]}

                # tool_calls 转换为 OpenAI API 标准格式
                if has_tool_calls:
                    api_tool_calls = []
                    for tc in m.tool_calls:
                        api_tool_calls.append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"], ensure_ascii=False)
                            }
                        })
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

    def _build_graph(self, context: AgentContext):
        from langgraph.types import interrupt

        @tool
        async def call_research_team(requirement: str):
            """调度研究专家团队进行深度调研。"""
            return f"RESEARCH_TASK:{requirement}"

        @tool
        async def call_coder_team(spec: str):
            """调度编码专家团队进行功能开发任务。"""
            return f"CODER_TASK:{spec}"

        tools = [call_research_team, call_coder_team]
        llm = self._get_llm().bind_tools(tools)

        # --- 节点 1：Supervisor (LLM 规划) ---
        async def supervisor_node(state: AgentState):
            msgs = self._format_messages(state["messages"])

            # 调试日志
            for i, msg in enumerate(msgs):
                role = msg.get("role", "?")
                tc = msg.get("tool_calls")
                tc_id = msg.get("tool_call_id")
                content_preview = str(msg.get("content", ""))[:80]
                extra = ""
                if tc: extra = f" tool_calls=[{', '.join(t.get('id','?') for t in tc)}]"
                if tc_id: extra = f" tool_call_id={tc_id}"
                self.logger.info(f"[Orchestrator] 📨 msg[{i}] role={role}{extra} content={content_preview}")

            resp = await llm.ainvoke(msgs)
            return {"messages": [resp]}

        # --- 节点 2：Dispatch (分发远程任务) ---
        async def dispatch_node(state: AgentState):
            last_msg = state["messages"][-1]
            tool_calls = last_msg.tool_calls

            remote_tasks = []
            remote_tc_ordered = []

            for tc in tool_calls:
                target_type = "research-team-supervisor" if tc["name"] == "call_research_team" else "coder-team-supervisor"
                content = tc["args"].get("requirement") or tc["args"].get("spec") or str(tc["args"])
                remote_tasks.append({"target_agent_type": target_type, "content": content})
                remote_tc_ordered.append(tc)

            if len(remote_tasks) == 1:
                # 单任务：使用 call_agent
                tc = remote_tc_ordered[0]
                target_type = "research-team-supervisor" if tc["name"] == "call_research_team" else "coder-team-supervisor"
                content = tc["args"].get("requirement") or tc["args"].get("spec") or str(tc["args"])
                await context.emit_chunk(f"📡 [Orchestrator] 正在下发单项任务...", content_type="text")
                result = await context.call_agent(target_agent_type=target_type, content=content)

                # call_agent 是同步等待结果的，直接返回
                reply = str(result.get("reply_data", "专家未返回有效内容")) if isinstance(result, dict) else str(result)
                return {
                    "messages": [ToolMessage(content=reply, tool_call_id=tc["id"])],
                    "task_group_id": None,
                    "tool_call_id_map": {}
                }
            else:
                # 多任务：使用 dispatch_group + interrupt
                self.logger.info(f"[Orchestrator] 🚀 并行分发 {len(remote_tasks)} 个专家团队任务...")
                await context.emit_chunk(f"🚀 [Orchestrator] 并行分发 {len(remote_tasks)} 个专家团队任务...", content_type="text")

                dispatch_res = await context.dispatch_group(remote_tasks)
                task_group_id = dispatch_res["task_group_id"]
                dispatched_tasks = dispatch_res["dispatched_tasks"]

                # 建立映射表：message_id -> tool_call_id
                tc_map = {}
                for i, d_task in enumerate(dispatched_tasks):
                    m_id = str(d_task["message_id"])
                    t_id = str(remote_tc_ordered[i].get("id") or f"tc-{i}")
                    tc_map[m_id] = t_id
                    self.logger.info(f"[Orchestrator] 🔗 映射: {m_id} -> {t_id}")

                # 持久化到 Redis
                redis_key = f"orch_tc_map:{context.session_id}:{task_group_id}"
                await context.redis.set(redis_key, json.dumps(tc_map), ex=3600)

                return {
                    "messages": [],
                    "task_group_id": task_group_id,
                    "tool_call_id_map": tc_map
                }

        # --- 节点 3：Collect (等待中断 + 聚合结果) ---
        async def collect_node(state: AgentState):
            group_id = state.get("task_group_id")
            if not group_id:
                # 单任务已经在 dispatch 中直接返回结果了，无需再收集
                return {"messages": []}

            # 挂起图执行，等待外部唤醒
            interrupt(f"WAIT_GROUP:{group_id}")

            # 唤醒后收集结果
            self.logger.info(f"[Orchestrator] 📥 专家组完成回调，开始聚合结果...")
            group_results = await context.collect_group_results(group_id)

            tc_map = state.get("tool_call_id_map", {})

            # 容错：从 Redis 恢复
            if not tc_map:
                redis_key = f"orch_tc_map:{context.session_id}:{group_id}"
                raw_map = await context.redis.get(redis_key)
                if raw_map: tc_map = json.loads(raw_map)

            tool_msgs = []
            for res in group_results:
                msg_id = str(res.get("message_id"))
                t_id = tc_map.get(msg_id) or f"fallback-{msg_id[:8]}"
                ans = str(res.get("reply_data", "专家未返回有效内容"))

                display = ans[:200] + "..." if len(ans) > 200 else ans
                await context.emit_chunk(f"\n📥 专家反馈 (摘要)：\n{display}\n", content_type="text")

                tool_msgs.append(ToolMessage(tool_call_id=t_id, content=ans))

            return {
                "messages": tool_msgs,
                "task_group_id": None,
                "tool_call_id_map": {}
            }

        # --- 构建图 ---
        workflow = StateGraph(AgentState)
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("dispatch", dispatch_node)
        workflow.add_node("collect", collect_node)

        workflow.add_edge(START, "supervisor")
        workflow.add_conditional_edges("supervisor", tools_condition, {"tools": "dispatch", END: END})
        workflow.add_edge("dispatch", "collect")
        workflow.add_edge("collect", "supervisor")

        # 持久化 Checkpointer
        if not hasattr(self, "_memory_saver"):
            self._memory_saver = MemorySaver()

        return workflow.compile(checkpointer=self._memory_saver)

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        from langgraph.types import Command

        config = {"configurable": {"thread_id": context.session_id}}
        graph = self._build_graph(context)

        if isinstance(command, AskAgentCommand):
            await context.emit_chunk("🏢 软件研发中心上线...", content_type="text")

            final = await graph.ainvoke(
                {"messages": [HumanMessage(content=command.content)]},
                config=config
            )

            last_msg = final["messages"][-1]
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                return "Tasks dispatched, waiting for experts."

            final_answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            await context.emit_chunk(f"\n✨ [报告要点]:\n{final_answer}", content_type="text")
            return final_answer

        elif isinstance(command, ResumeCommand):
            self.logger.info(f"[Orchestrator] 📥 收到 Resume，唤醒图...")

            final = await graph.ainvoke(Command(resume="WAKE_UP"), config=config)

            last_msg = final["messages"][-1]
            final_answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            await context.emit_chunk(f"\n✨ [报告要点]:\n{final_answer}", content_type="text")
            return final_answer


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hierarchical Orchestrator Worker")
    parser.add_argument("--worker-id", default="orchestrator-1", help="Specify the worker ID")
    args = parser.parse_args()
    run_worker(
        HierarchicalOrchestrator,
        worker_id=args.worker_id,
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
    )
