import os
import asyncio
import json
import uuid
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from by_framework.common.redis_client import init_redis
from by_framework.core.registry import WorkerRegistry
from by_framework.client.byai_client import ByaiGatewayClient
from by_framework.common.constants import RedisKeys

# 加载环境变量
load_dotenv()

async def main():
    # 1. 配置参数 (可通过 .env 设置)
    redis_host = os.getenv("BYAI_REDIS_HOST", "127.0.0.1")
    redis_port = int(os.getenv("BYAI_REDIS_PORT", 6379))
    redis_db = int(os.getenv("BYAI_REDIS_DB", 0))
    redis_username = os.getenv("BYAI_REDIS_USERNAME")
    redis_password = os.getenv("BYAI_REDIS_PASSWORD")
    
    # 目标 Agent 类型 (参考 workers/langgraph-worker/main.py 中的 get_capabilities)
    target_worker_id = "langgraph-worker-1"
    target_agent_type = "langgraph-agent"
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    print(f"[*] 正在连接 Redis: {redis_host}:{redis_port} (DB: {redis_db})")
    
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
    
    # 3. 发送消息
    user_input = "你好，请自我介绍一下。"
    print(f"[*] 发送消息到 {target_worker_id}: '{user_input}'")
    
    response = await client.send_message(
        target_agent_type=target_agent_type,
        target_worker_id=target_worker_id,
        session_id=session_id,
        content=user_input,
    )
    
    if response.success:
        print(f"[+] 发送成功!")
        print(f"    Message ID: {response.message_id}")
        print(f"    Trace ID: {response.trace_id}")
        print(f"    Worker ID: {response.target_worker_id}")

    else:
        print(f"[-] 发送失败: {response.status}")
        if not response.target_worker_id:
            print(f"    [!] 未找到能处理类型为 '{target_agent_type}' 的 Worker，请确保 Worker 已启动并注册。")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
