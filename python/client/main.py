import os
import asyncio
import json
import uuid
import logging
import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 配置统一日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Client")

from by_framework.common.redis_client import init_redis
from by_framework.core.registry import WorkerRegistry
from by_framework.client.byai_client import ByaiGatewayClient
from by_framework.common.constants import RedisKeys

# 加载环境变量
load_dotenv()

class SyncGatewayClient:
    """提供同步阻塞体验的 Gateway 客户端，封装了底层事件流监听能力"""
    
    def __init__(self, client: ByaiGatewayClient, redis_client):
        self.client = client
        self.redis_client = redis_client
        self.logger = logging.getLogger("SyncGatewayClient")

    async def send_message(
        self,
        session_id: str,
        target_agent_type: str,
        content: str,
        target_worker_id: Optional[str] = None
    ):
        """直接异步发送消息，不阻塞等待流式回复"""
        self.logger.info(f"直接发送消息到 {target_worker_id or target_agent_type}: '{content}'")
        response = await self.client.send_message(
            target_agent_type=target_agent_type,
            target_worker_id=target_worker_id,
            session_id=session_id,
            content=content,
        )
        if response.success:
            self.logger.info(f"发送成功! Message ID: {response.message_id}")
        else:
            self.logger.error(f"发送失败: {response.status}")
        return response

    async def subscribe_data_queue(self, session_id: str, timeout_seconds: int = 60) -> str:
        """订阅会话数据队列，监听返回的事件和数据包，返回最终拼接的完整回答"""
        self.logger.info(f"开始监听数据队列 (Session ID: {session_id})")
        stream_name = RedisKeys.session_data_stream(session_id)
        last_id = "0-0"
        full_answer = ""
        
        last_receive_time = time.time()
        
        try:
            while True:
                # 阻塞读取，超时 1000 毫秒
                messages = await self.redis_client.xread({stream_name: last_id}, count=10, block=1000)
                if not messages:
                    if time.time() - last_receive_time >= timeout_seconds:
                        self.logger.warning(f"接收消息超时 ({timeout_seconds}秒未收到新数据)，自动退出监听。")
                        return full_answer
                    continue
                    
                last_receive_time = time.time()
                    
                for _, msg_list in messages:
                    for msg_id, fields in msg_list:
                        last_id = msg_id.decode('utf-8') if isinstance(msg_id, bytes) else msg_id
                        
                        # 兼容可能为 bytes 或 str 的 key 和 value
                        data_raw = fields.get(b"data") or fields.get("data")
                        if not data_raw:
                            continue
                            
                        try:
                            data_str = data_raw.decode('utf-8') if isinstance(data_raw, bytes) else data_raw
                            event = json.loads(data_str)
                            event_type = event.get("event_type")
                            
                            # 解析 OpenAI 格式的增量输出
                            if event_type == "answerDelta":
                                delta = event.get("data", {}).get("choices", [{}])[0].get("delta", {}).get("content", "")
                                full_answer += delta
                                # 保持流式输出
                                print(delta, end="", flush=True)
                            elif event_type == "reasoningLogDelta":
                                delta = event.get("data", {}).get("choices", [{}])[0].get("delta", {}).get("content", "")
                                print(f"\n[思考]: {delta}", flush=True)
                            elif event_type in ("done", "appStreamResponse"):
                                self.logger.info(f"接收到结束事件 ({event_type})。")
                                return full_answer
                            else:
                                # 打印其他类型的事件日志
                                pass
                        except Exception as e:
                            self.logger.error(f"解析事件失败: {e}")
                            
        except asyncio.CancelledError:
            self.logger.info("停止监听数据队列")
            return full_answer

    async def send_message_sync(
        self,
        session_id: str,
        target_agent_type: str,
        content: str,
        target_worker_id: Optional[str] = None,
        timeout_seconds: int = 60
    ) -> Optional[str]:
        """同步调用方法：发送消息并阻塞等待完整回复"""
        response = await self.client.send_message(
            target_agent_type=target_agent_type,
            target_worker_id=target_worker_id,
            session_id=session_id,
            content=content,
        )
        
        if response.success:
            # 阻塞等待结果
            answer = await self.subscribe_data_queue(session_id, timeout_seconds=timeout_seconds)
            return answer
        else:
            self.logger.error(f"发送失败: {response.status}")
            if not response.target_worker_id:
                self.logger.warning(f"未找到能处理类型为 '{target_agent_type}' 的 Worker，请确保 Worker 已启动并注册。")
            return None

async def chat_with_agent(
    sync_client: SyncGatewayClient,
    target_agent_type: str,
    session_id: str,
    user_input: str,
    target_worker_id: Optional[str] = None,
):
    """发送消息测试的业务逻辑"""
    logger.info(f"同步发送消息到 {target_worker_id or target_agent_type}: '{user_input}'")
    
    # 使用封装好的同步调用方法
    final_answer = await sync_client.send_message_sync(
        session_id=session_id,
        target_agent_type=target_agent_type,
        content=user_input,
        target_worker_id=target_worker_id
    )
    
    if final_answer is not None:
        logger.info(f"\n{'='*40}\n[最终回复内容]:\n{final_answer}\n{'='*40}")

async def main():
    # 1. 配置参数 (可通过 .env 设置)
    redis_host = os.getenv("BYAI_REDIS_HOST", "127.0.0.1")
    redis_port = int(os.getenv("BYAI_REDIS_PORT", 6379))
    redis_db = int(os.getenv("BYAI_REDIS_DB", 0))
    redis_username = os.getenv("BYAI_REDIS_USERNAME")
    redis_password = os.getenv("BYAI_REDIS_PASSWORD")
    
    # 目标 Agent 类型 (参考 workers/langgraph-worker/main.py 中的 get_capabilities)
    target_worker_id = "langgraph-worker-1"
    target_agent_type = "langgraph-extension-demo"
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"正在连接 Redis: {redis_host}:{redis_port} (DB: {redis_db})")
    
    # 2. 初始化核心组件
    redis_client = init_redis(
        redis_host,
        redis_port,
        redis_db,
        redis_password,
        redis_username
    )
    
    # Registry 用于查找 Worker 路由
    registry = WorkerRegistry(redis_client)
    
    # ByaiGatewayClient 会自动包含处理 BaiYingMessage 的拦截器
    client = ByaiGatewayClient(registry=registry, redis_client=redis_client)
    
    # 实例化同步客户端包装器
    sync_client = SyncGatewayClient(client=client, redis_client=redis_client)
    
    # 3. 发送消息测试
    user_input = "你好，请自我介绍一下。"
    await chat_with_agent(
        sync_client=sync_client,
        target_agent_type=target_agent_type,
        # target_worker_id=target_worker_id,
        session_id=session_id,
        user_input=user_input
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
