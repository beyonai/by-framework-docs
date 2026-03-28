import os
import asyncio
from typing import List, Any, Dict
from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

from langchain_openai import ChatOpenAI

load_dotenv()

class ResearchTeamWorker(GatewayWorker):
    """
    研究专家团队 - 直接通过大模型生成调研报告。
    """

    def get_capabilities(self) -> List[str]:
        return ["research-team-supervisor"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    async def process_command(self, command: GatewayCommand, context: AgentContext) -> Any:
        self.logger.info(f"Research Team processing: {command.content}")
        
        llm = self._get_llm()
        
        # 适配网关/LLM 要求的格式：content 必须是包含 type='text' 的列表
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "你是一名资深技术研究员。请针对用户提出的需求，直接提供一份详尽、准确的技术调研方案，无需多言。"}]
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

if __name__ == "__main__":
    run_worker(ResearchTeamWorker, worker_id="research-team-1")
