import os
from typing import List

from by_framework.worker import run_worker
from by_framework_history_byclaw import ByClawHistoryBackend
from by_framework_langgraph import LangGraphWorker
from by_framework_langgraph.tools import make_ask_user_tool, make_remote_agent_tool
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# 加载环境变量 (需要 OPENAI_API_KEY, LLM_MODEL 等)
load_dotenv()

class ExtensionDemoWorker(LangGraphWorker):
    """
    基于 by-framework-langgraph 扩展库实现的示例 Worker。
    
    该示例展示了：
    1. 如何继承 LangGraphWorker 自动获得流式输出和生命周期管理能力。
    2. 如何利用 make_remote_agent_tool 定义远程智能体调用工具。
    3. 如何利用 make_ask_user_tool 定义与前端用户交互的工具。
    """

    def get_agent_types(self) -> List[str]:
        """定义此 Worker 提供的智能体类型。"""
        return ["langgraph-extension-demo"]

    def build_graph(self, context, command):
        """
        构建并返回编译后的 LangGraph。
        
        每次处理命令时（包括 ResumeCommand）都会调用此方法。
        """
        
        # 1. 创建远程智能体调用工具
        # 该工具被调用时，会自动挂起当前图执行，并向 Gateway 发送调用 weather-agent 的指令。
        # 当回复到达时，图会自动从挂起点恢复。
        weather_tool = make_remote_agent_tool(
            context=context,
            tool_name="query_weather",
            target_agent_type="weather-agent",
            description="查询指定城市的天气。当用户询问天气相关问题时调用此工具。"
        )

        # 2. 创建用户交互工具
        # 该工具被调用时，会向前端发送表单请求。用户回复后，图执行将继续。
        ask_user_tool = make_ask_user_tool(
            context=context,
            tool_name="ask_user_for_confirmation",
            description="当需要用户决策或确认某些敏感信息时使用。"
        )

        # 3. 初始化大语言模型
        # 建议开启 streaming=True 以便 LangGraphWorker 进行分片推送。
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True,
        )

        # 4. 构建图
        # 我们这里使用高度封装的 ReAct Agent，它会自动根据提示选择工具。
        # 注意：必须传入 self.get_checkpointer() 以便支持跨命令的挂起与恢复。
        agent_graph = create_react_agent(
            llm,
            tools=[weather_tool, ask_user_tool],
            checkpointer=self.get_checkpointer(),
            prompt="你是一个由 by-framework赋能的 AI 助手。你可以查询天气或直接向用户提问。"
        )

        return agent_graph


if __name__ == "__main__":
    # 使用框架自带的 run_worker 启动
    # 配置信息通常建议从环境变量中读取
    run_worker(
        ExtensionDemoWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "langgraph-ext-worker"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME", ""),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD", ""),
        history_backend=ByClawHistoryBackend(
            base_url=os.getenv("BYAI_HISTORY_URL", "http://10.45.134.185:8086")
        )
    )
