import os
import random
from typing import List

from by_framework.worker import ByaiWorker, run_worker
from by_framework_history_byclaw import ByClawHistoryBackend
from dotenv import load_dotenv

# 加载同目录下的环境变量
load_dotenv()

class WeatherWorker(ByaiWorker):
    """
    一个极其简易的模拟天气智能体。
    
    作为配套服务，它演示了跨 Agent 调用功能。
    当 langgraph-extension-demo 智能体需要查询天气时，会调用此智能体。
    """

    def get_agent_types(self) -> List[str]:
        """注册为 weather-agent 类型。"""
        return ["weather-agent"]

    async def process_command(self, command, context):
        """
        处理来自 Gateway 的天气查询命令。
        """
        input_text = str(command.content)
        self.logger.info(f"[Weather-Agent] 收到查询请求: {input_text}")
        
        # 识别中文城市名并生成随机天气
        cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安"]
        target_city = "当地"
        
        for city in cities:
            if city in input_text:
                target_city = city
                break
            
        temperature = random.randint(10, 32)
        conditions = random.choice(["晴朗", "多云", "阴天", "阵雨", "雷阵雨"])
        humidity = random.randint(30, 80)
        
        result = (
            f"{target_city}当前的天气情况如下：\n"
            f"- 天气状况：{conditions}\n"
            f"- 当前气温：{temperature}℃\n"
            f"- 空气湿度：{humidity}%\n"
            f"这是一个由 weather-agent 提供的实时模拟数据。"
        )
        
        self.logger.info(f"[Weather-Agent] 返回结果: {result}")
        return result

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
