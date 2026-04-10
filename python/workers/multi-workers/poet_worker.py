import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

# 加载环境
load_dotenv()

class PoetWorker(GatewayWorker):
    """
    首席诗人进程。
    具备 LLM 能力，专注于根据主题进行流式诗歌创作。
    """

    def get_agent_types(self):
        return ["poet-agent"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    async def process_command(self, command: GatewayCommand, context: AgentContext):
        topic = str(command.content)
        self.logger.info(f"[Poet-Worker] 🖌️ 接到作诗请求：{topic}")
        
        llm = self._get_llm()
        full_poem = ""

        # 1. 立即给前端一个响应提示
        await context.emit_chunk(f"\n🎨 [诗人正在斟酌字句... 题目：{topic}]\n", content_type="text")

        # 2. 调用 astream 开始流式生成
        try:
            async for chunk in llm.astream([HumanMessage(content=f"请围绕主题“{topic}”创作一首意境优美的诗词。直接开始作诗内容，不要有前言。")]):
                if chunk.content:
                    # 关键：将每一块 token 即时推送到前端 (作为推理日志输出)
                    await context.emit_chunk(chunk.content, content_type="text", event_type="REASONING_LOG_DELTA")
                    full_poem += chunk.content
            
            self.logger.info(f"[Poet-Worker] ✅ 创作完成。")
            
            # 返回完整的诗篇给 Orchestrator
            return full_poem
            
        except Exception as e:
            self.logger.error(f"[Poet-Worker] ❌ 创作异常：{e}")
            return f"灵感枯竭了：{str(e)}"

if __name__ == "__main__":
    run_worker(
        PoetWorker,
        worker_id="poet-worker-1",
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
        redis_username=os.getenv("BYAI_REDIS_USERNAME")
    )
