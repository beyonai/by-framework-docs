import os
import random
from typing import List

from by_framework.worker import run_worker
from by_framework_history_byclaw import ByClawHistoryBackend
from by_framework_langgraph import LangGraphWorker
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# 加载同目录下的环境变量
load_dotenv()

@tool
def get_current_weather(city: str) -> str:
    """获取指定城市当前的天气情况。"""
    cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安"]
    target_city = "当地"
    for c in cities:
        if c in city:
            target_city = c
            break
            
    temperature = random.randint(10, 32)
    conditions = random.choice(["晴朗", "多云", "阴天", "阵雨", "雷阵雨"])
    humidity = random.randint(30, 80)
    
    return (
        f"{target_city}当前的天气情况如下：\n"
        f"- 天气状况：{conditions}\n"
        f"- 当前气温：{temperature}℃\n"
        f"- 空气湿度：{humidity}%\n"
        f"这是一个由 weather-agent 通过工具调用提供的实时模拟数据。"
    )

@tool
def get_current_date() -> str:
    """获取当前的日期和星期。当需要确定今天是哪一天或星期几时，应调用此工具。"""
    from datetime import datetime
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]
    return f"今天是：{now.strftime('%Y-%m-%d')}，{weekday}。"

class WeatherWorker(LangGraphWorker):
    """
    一个使用 LangGraph 和工具调用的模拟天气智能体。
    
    作为配套服务，它演示了跨 Agent 调用与内部工具调用功能。
    当 langgraph-extension-demo 智能体需要查询天气时，会调用此智能体。
    """

    def get_agent_types(self) -> List[str]:
        """注册为 weather-agent 类型。"""
        return ["weather-agent"]

    def get_thread_id(self, context) -> str:
        """Keep each remote weather request isolated from previous session turns."""
        return context.message_id or context.session_id

    def build_graph(self, context, command):
        """
        构建并返回编译后的 LangGraph。
        每次处理命令时（包括 ResumeCommand）都会调用此方法。
        """
        # 初始化大语言模型
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True,
            stream_options={"include_usage": True},
        )

        # 构建图并绑定工具
        agent_graph = create_react_agent(
            llm,
            tools=[get_current_weather, get_current_date],
            checkpointer=self.get_checkpointer(),
            prompt=(
                "你是一个天气与日期查询助手。\n"
                "用户查询天气时，最多调用一次 get_current_weather。\n"
                "用户查询日期时，最多调用一次 get_current_date。\n"
                "工具返回结果后，必须直接把工具结果整理成最终回答，不要再次调用同一个工具。"
            )
        )

        return agent_graph

if __name__ == "__main__":
    # 启动 Worker
    run_worker(
        WeatherWorker,
        worker_id=os.getenv("BYAI_WEATHER_WORKER_ID", "mock-weather-worker"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME", "myuser"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD", "mypassword"),
        history_backend=ByClawHistoryBackend(
            base_url=os.getenv("BYAI_HISTORY_URL", "http://10.45.134.185:8086")
        )
    )
