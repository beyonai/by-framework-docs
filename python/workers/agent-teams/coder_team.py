import os
import asyncio
from typing import List, Any, Dict
from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from langchain_openai import ChatOpenAI

load_dotenv()

class CoderTeamWorker(GatewayWorker):
    """
    编码专家团队 - 直接通过大模型生成代码。
    """

    def get_agent_types(self) -> List[str]:
        return ["coder-team-supervisor"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        self.logger.info(f"Coder Team processing: {command.content}")
        
        llm = self._get_llm()
        
        # 适配网关/LLM 要求的格式：content 必须是包含 type='text' 的列表
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "你是一名资深后端开发专家。请根据输入的需求规格，直接编写高效、可读性强的代码实现，无需多言。"}]
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": str(command.content)}]
            }
        ]

        full_response = ""
        # 1. 使用 astream 进行流式处理
        async for chunk in llm.astream(messages):
            if chunk.content:
                # 2. 实时推送分片给前端用户
                await context.emit_chunk(chunk.content, content_type="text")
                full_response += chunk.content

        # 3. 返回最终完整结果给 Orchestrator
        return full_response

import argparse
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Coder Team Worker")
    parser.add_argument("--worker-id", default="coder-team-1", help="Specify the worker ID")
    args = parser.parse_args()
    run_worker(CoderTeamWorker, worker_id=args.worker_id,         redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),)

if __name__ == "__main__":
    main()
