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

class LLMOrchestratorWorker(GatewayWorker):
    """
    一个完整的基于 LLM 决策的多 Agent 协作 Worker 范例。
    
    该示例展示了：
    1. LLM 工具调用决策 (Function Calling)
    2. 分布式控制流 (由 Orchestrator 发起任务给 Sub-worker)
    3. 异步任务挂起与恢复 (Resume)
    4. 实时前端进度推送 (emit_chunk)
    """

    def get_capabilities(self) -> List[str]:
        return ["orchestrator-agent", "sub-worker-agent"]

    def _get_llm(self):
        """初始化大模型"""
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    def _format_messages_for_api(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """
        [重要] 消息格式化工具。
        由于部分 API 代理/网关对消息结构非常严苛（例如要求 Multi-modal 数组格式），
        在此统一将 LangChain 消息对象降级为最兼容的 OpenAI 字典格式。
        """
        system_prompt = (
            "你是一个高度智能的任务协调中心 (Orchestrator)。\n"
            "如果你识别到用户需要处理特定的文本（反转、大写），请务必调用 `call_sub_worker` 工具来委托专门的 Agent 处理。\n"
            "在处理过程中，请表现得专业且简洁。\n\n"
            "重要：禁止你自己模拟反转结果，所有转换必须通过工具完成。"
        )
        
        formatted = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}]
        
        for m in messages:
            if isinstance(m, HumanMessage): role = "user"
            elif isinstance(m, ToolMessage): role = "tool"
            elif isinstance(m, (AIMessage, BaseMessage)) and (getattr(m, "type", "") == "ai" or "ai" in str(type(m)).lower()): 
                role = "assistant"
            else: role = "user"

            # 统一包装成数组格式以适配严苛的网关参数校验
            text_content = m.content if hasattr(m, "content") else str(m)
            content_list = [{"type": "text", "text": str(text_content)}]
            
            msg_dict = {"role": role, "content": content_list}
            if isinstance(m, ToolMessage):
                msg_dict["tool_call_id"] = m.tool_call_id
            
            # 如果是 AI 消息且包含工具调用
            if role == "assistant" and hasattr(m, "tool_calls") and m.tool_calls:
                msg_dict["tool_calls"] = m.tool_calls

            formatted.append(msg_dict)
            
        return formatted

    def _build_orchestrator_graph(self, context: AgentContext):
        """构建协调员工作流图"""
        
        @tool
        async def call_sub_worker(content: str):
            """
            将文本内容委托给专门的子 Agent (sub-worker-agent) 进行高效的处理（反转+大写）。
            参数 `content` 是需要处理的原始字符串。
            """
            self.logger.info(f"[Orchestrator] 🚀 触发工具：调度子 Agent 处理 -> {content}")
            
            # 发送中间进度给前端
            await context.emit_chunk(
                f"🛠️ [决策] LLM 决定委派任务给子智能体处理：\n> \"{content}\"\n正在调度分布式计算资源...", 
                content_type="text"
            )
            
            # 发起跨 Agent 调用 (由于 wait_for_reply 默认为 True, 此处会自动进入挂起状态)
            await context.call_agent(
                target_agent_type="sub-worker-agent",
                content=content
            )
            
            return f"任务已提交给 sub-worker-agent，等待异步回调。输入内容：{content}"

        tools = [call_sub_worker]
        llm = self._get_llm().bind_tools(tools)

        async def call_model_node(state: AgentState):
            # 将消息序列格式化为高兼容性格式
            api_messages = self._format_messages_for_api(state["messages"])
            self.logger.info(f"[Node] call_model 运行，历史长度: {len(api_messages)}")
            
            try:
                response = await llm.ainvoke(api_messages)
                
                # 日志记录决策细节
                if response.tool_calls:
                    self.logger.info(f"[Decision] 逻辑分支：执行工具调用 {response.tool_calls[0]['name']}")
                else:
                    self.logger.info(f"[Decision] 逻辑分支：直接生成终端回复")
                    
                return {"messages": [response]}
            except Exception as e:
                self.logger.error(f"[Critical] 大模型请求异常: {e}")
                error_msg = f"❌ 对不起，AI 协调中心发生错误：{str(e)}"
                await context.emit_chunk(error_msg, content_type="text")
                return {"messages": [AIMessage(content=error_msg)]}

        # 组装状态机
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model_node)
        workflow.add_node("tools", ToolNode(tools))

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", END) # 调用完工具节点后，流程终止并“导出”其状态，待 Resume 时重新入场

        return workflow.compile()

    def _build_sub_worker_graph(self):
        """子 Agent 流程图：简单的计算型任务"""
        async def process_text_node(state: AgentState):
            text = state["messages"][-1].content
            # 执行核心计算逻辑
            result = str(text)[::-1].upper()
            return {"messages": [AIMessage(content=result)]}

        workflow = StateGraph(AgentState)
        workflow.add_node("proc", process_text_node)
        workflow.add_edge(START, "proc")
        workflow.add_edge("proc", END)
        return workflow.compile()

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        target_type = command.header.target_agent_type
        
        # --- 子智能体 (Sub-worker) 运行逻辑 ---
        if target_type == "sub-worker-agent":
            # 这里的输入处理增加了对 by-framework 发来的 content 字段的提取
            content = str(command.content)
            self.logger.info(f"[Sub-worker] 节点接收任务：{content}")
            
            inputs = {"messages": [HumanMessage(content=content)]}
            graph = self._build_sub_worker_graph()
            result = await graph.ainvoke(inputs)
            
            return result["messages"][-1].content

        # --- 协调智能体 (Orchestrator) 运行逻辑 ---
        if target_type == "orchestrator-agent":
            graph = self._build_orchestrator_graph(context)

            # A. 场景：新任务开启 (Ask)
            if isinstance(command, AskAgentCommand):
                self.logger.info(f"[Orchestrator] 🏁 收到用户新请求: {command.content}")
                await context.emit_chunk("🔍 正在规划任务路径...", content_type="text")
                
                inputs = {"messages": [HumanMessage(content=command.content)]}
                # 图会执行到 ToolNode 或直到生成文本结束
                await graph.ainvoke(inputs)
                return "Processing established..."

            # B. 场景：子任务返回 (Resume)
            elif isinstance(command, ResumeCommand):
                result_data = str(command.reply_data)
                self.logger.info(f"[Orchestrator] 📥 接收到原子任务返回：{result_data}")
                
                # 通过 emit_chunk 将中间产物同步到前端，增加即时感
                await context.emit_chunk(
                    f"✨ [结果接收] 子 Agent 返回结果：\n`{result_data}`\n正在整理详细摘要...", 
                    content_type="text"
                )

                # 重建对话历史，让 LLM 看到“工具已经运行并返回结果”的状态
                # 这里我们假设 ToolCall ID 和之前的调用能匹配，这仅作为结构化演示
                fake_id = "call_res_" + context.session_id[-6:]
                
                # 构造消息历史链条
                history = [
                    HumanMessage(content=str(command.content)), # 用户原始输入
                    AIMessage(
                        content="", 
                        tool_calls=[{"name": "call_sub_worker", "args": {"content": str(command.content)}, "id": fake_id}]
                    ), # 之前的 AI 决策
                    ToolMessage(content=result_data, tool_call_id=fake_id) # 本次接收到的工具返回
                ]

                # 重新将图交给 LLM 汇总最后结果
                final_state = await graph.ainvoke({"messages": history})
                
                # 最终输出清理
                final_answer = final_state["messages"][-1].content
                return final_answer

        return f"Unknown Target Agent: {target_type}"

if __name__ == "__main__":
    run_worker(
        LLMOrchestratorWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "multi-agent-sample-1"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD")
    )
