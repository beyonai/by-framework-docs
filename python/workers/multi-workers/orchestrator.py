import os
import asyncio
import json
from typing import Annotated, Any, Dict, List, TypedDict, Optional
from dotenv import load_dotenv

from by_framework.core.protocol.commands import (
    GatewayCommand, 
    AskAgentCommand, 
    ResumeCommand
)
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, AIMessage
from langchain_core.tools import tool

# 加载环境变量
load_dotenv()

class AgentState(TypedDict):
    """LangGraph 状态定义"""
    messages: Annotated[list, add_messages]
    task_group_id: Optional[str]
    tool_call_id_map: Dict[str, str]

class OrchestratorWorker(GatewayWorker):
    """
    诗歌分层创作工作室 (Worker A)。
    通过并行专家组协调诗人、翻译和评论专家的工作。
    """

    def get_capabilities(self) -> List[str]:
        return ["orchestrator-agent"]

    def _get_llm(self):
        model_name = os.getenv("LLM_MODEL", "gpt-4o")
        llm_kwargs = {
            "model": model_name,
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("OPENAI_BASE_URL"),
            "streaming": True
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
            if isinstance(m, HumanMessage): role = "user"
            elif isinstance(m, ToolMessage): role = "tool"
            elif isinstance(m, AIMessage): role = "assistant"
            else: role = "user"
            
            raw_text = m.content if hasattr(m, "content") else str(m)
            
            # MiniMax 适配：assistant 消息 content 不能为空，至少使用 "\n" 占位
            final_text = str(raw_text)
            if role == "assistant" and not final_text.strip():
                final_text = "\n"
                
            msg_dict = {"role": role, "content": [{"type": "text", "text": final_text}]}
            
            # --- MiniMax 思维链持久化核心逻辑 ---
            if role == "assistant":
                # 处理 reasoning_details (OpenAI 兼容模式)
                reasoning = m.additional_kwargs.get("reasoning_details")
                if reasoning:
                    msg_dict["reasoning_details"] = reasoning
                
                # 处理 tool_calls
                if hasattr(m, "tool_calls") and m.tool_calls:
                    msg_dict["tool_calls"] = m.tool_calls
            
            if role == "tool":
                msg_dict["tool_call_id"] = m.tool_call_id
                
            formatted.append(msg_dict)
        return formatted

    def _build_graph(self, context: AgentContext, command: GatewayCommand):
        from langgraph.types import interrupt

        # 1. LLM 规划工具
        from langchain_core.tools import StructuredTool
        def dummy_func(topic: str = "", content: str = ""): pass
        
        tools = [
            StructuredTool.from_function(func=dummy_func, name="invoke_poet_agent", description="创作诗歌。"),
            StructuredTool.from_function(func=dummy_func, name="invoke_translator_agent", description="翻译诗歌为英文。"),
            StructuredTool.from_function(func=dummy_func, name="invoke_critic_agent", description="进行深度风格点评。"),
            StructuredTool.from_function(func=lambda poem_text: "古典主义", name="evaluate_poem_style", description="分析诗歌文学风格。")
        ]
        
        llm = self._get_llm().bind_tools(tools)

        async def agent_node(state: AgentState):
            msgs = self._format_messages(state["messages"])
            resp = await llm.ainvoke(msgs)
            
            # 实时打印思维链（如果存在）
            reasoning = resp.additional_kwargs.get("reasoning_details")
            if reasoning:
                thought = reasoning[0].get("text") if isinstance(reasoning, list) and reasoning else ""
                if thought:
                    self.logger.info(f"[Orchestrator] 💭模型推理中: {thought[:100]}...")
            
            return {"messages": [resp]}

        # 2. 【分调节点】：执行本地工具并在后端分发并行组
        async def tools_dispatch(state: AgentState):
            last_msg = state["messages"][-1]
            tool_calls = last_msg.tool_calls
            
            tool_msgs = []
            remote_tasks = []
            remote_tc_ordered = [] # 记录顺序以匹配 ID
            
            for tc in tool_calls:
                if tc["name"] == "evaluate_poem_style":
                    await context.emit_chunk(f"🔍 [Orchestrator] 本地工具评估...", content_type="text")
                    res = "分析结果：气势宏大，具有浓郁的古典韵味。"
                    tool_msgs.append(ToolMessage(tool_call_id=tc["id"], content=res))
                
                elif tc["name"] in ["invoke_poet_agent", "invoke_translator_agent", "invoke_critic_agent"]:
                    target_agent = {
                        "invoke_poet_agent": "poet-agent",
                        "invoke_translator_agent": "translator-agent",
                        "invoke_critic_agent": "critic-agent"
                    }[tc["name"]]
                    
                    # 确定任务内容
                    task_content = tc["args"].get("topic") or tc["args"].get("content") or str(tc["args"])
                    
                    remote_tasks.append({
                        "target_agent_type": target_agent,
                        "content": task_content
                    })
                    remote_tc_ordered.append(tc)

            if remote_tasks:
                self.logger.info(f"[Orchestrator] 🚀 发起并行专家组调度... 规模: {len(remote_tasks)}")
                await context.emit_chunk(f"🚀 [Orchestrator] 正在同步调度诗人、翻译及评论专家...", content_type="text")
                
                dispatch_res = await context.dispatch_group(remote_tasks)
                task_group_id = dispatch_res["task_group_id"]
                dispatched_tasks = dispatch_res["dispatched_tasks"]
                
                # 建立内部映射表：message_id -> tool_call_id
                tc_map = {}
                for i, d_task in enumerate(dispatched_tasks):
                    m_id = str(d_task["message_id"])
                    t_id = str(remote_tc_ordered[i].get("id") or f"tc-{i}")
                    tc_map[m_id] = t_id
                    self.logger.info(f"[Orchestrator] 🔗 建立映射: {m_id} -> {t_id}")
                
                # 持久化备份至 Redis (ID: task_group_id)
                redis_key = f"orch_tc_map:{context.session_id}:{task_group_id}"
                await context.redis.set(redis_key, json.dumps(tc_map), ex=3600)

                return {
                    "messages": tool_msgs,
                    "task_group_id": task_group_id,
                    "tool_call_id_map": tc_map
                }
            
            return {"messages": tool_msgs}

        # 3. 【收集节点】：等待中断并聚合并行结果
        async def tools_collect(state: AgentState):
            group_id = state.get("task_group_id")
            if not group_id:
                return {"messages": []}
                
            # 【LangGraph 中断】：挂起执行
            interrupt(f"WAIT_GROUP:{group_id}")
            
            # 唤醒后收集结果
            self.logger.info(f"[Orchestrator] 📥 专家组完成回调，开始聚合结果...")
            group_results = await context.collect_group_results(group_id)
            
            tool_msgs = []
            tc_map = state.get("tool_call_id_map", {})
            
            # 容错：如果状态丢失，从 Redis 恢复
            if not tc_map:
                redis_key = f"orch_tc_map:{context.session_id}:{group_id}"
                raw_map = await context.redis.get(redis_key)
                if raw_map: tc_map = json.loads(raw_map)

            for res in group_results:
                msg_id = str(res.get("message_id"))
                t_id = tc_map.get(msg_id) or f"fallback-{msg_id[:4]}"
                ans = str(res.get("reply_data", "专家未返回有效内容"))
                tool_msgs.append(ToolMessage(tool_call_id=t_id, content=ans))
            
            # 清理
            return {
                "messages": tool_msgs,
                "task_group_id": None,
                "tool_call_id_map": {}
            }

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("dispatch", tools_dispatch)
        workflow.add_node("collect", tools_collect)
        
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition, {"tools": "dispatch", END: END})
        workflow.add_edge("dispatch", "collect")
        workflow.add_edge("collect", "agent")
        
        # 持久化 Checkpointer
        from langgraph.checkpoint.memory import MemorySaver
        if not hasattr(self, "_memory_saver"):
            self._memory_saver = MemorySaver()
            
        return workflow.compile(checkpointer=self._memory_saver)

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        from langgraph.types import Command
        
        # 必须为当前 Session 指定 Thread ID
        config = {"configurable": {"thread_id": context.session_id}}
        graph = self._build_graph(context, command)
        
        if isinstance(command, AskAgentCommand):
            await context.emit_chunk("✍️ [文学工作室] 正式开始处理您的需求...", content_type="text")
            
            # 演示：子步骤层级化日志的最佳实践
            async with context.sub_step("准备阶段") as (sub_id, parent_id):
                await context.emit_chunk("🔐 level 1 正在验证本地 Framework 运行环境...")
                await context.emit_chunk("✅ level 1 环境验证通过。")
                async with context.sub_step("准备阶段") as (sub_id, parent_id):
                    await context.emit_chunk("🔐 level 2 正在验证本地 Framework 运行环境...")
                    await context.emit_chunk("✅ level 2 环境验证通过。")
                    async with context.sub_step("准备阶段") as (sub_id, parent_id):
                        await context.emit_chunk("🔐 level 3 正在验证本地 Framework 运行环境...")
                        await context.emit_chunk("✅ level 3 环境验证通过。")
                    
            final = await graph.ainvoke({"messages": [HumanMessage(content=command.content)]}, config=config)
            
            last_msg = final["messages"][-1]
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                 return "Tasks dispatched to parallel experts."
            else:
                 final_answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                 await context.emit_chunk(f"\n💡 {final_answer}", content_type="text")
                 return final_answer

        elif isinstance(command, ResumeCommand):
            self.logger.info(f"[Orchestrator] 📥 专家组任务集齐，唤醒图中...")
            final = await graph.ainvoke(Command(resume="WAKE_UP"), config=config)
            
            last_msg = final["messages"][-1]
            final_answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            await context.emit_chunk(f"\n💡 [文学协调员总结]：\n{final_answer}", content_type="text")
            return final_answer

if __name__ == "__main__":
    run_worker(
        OrchestratorWorker,
        worker_id="orchestrator-poet-manager-1",
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD")
    )
