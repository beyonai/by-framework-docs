import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

# 加载环境
load_dotenv()

class PoetSubWorker(GatewayWorker):
    """
    流式诗人进程 (Worker B)。
    该节点具备 LLM 能力，并会在生成过程中通过 emit_chunk 实时将诗歌流推送到前端。
    """

    def get_capabilities(self):
        return ["sub-worker-agent"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    async def process_command(self, command: GatewayCommand, context: AgentContext):
        prompt = str(command.content)
        self.logger.info(f"[Poet-Worker] 🖌️ 接到作诗请求：{prompt}")
        
        llm = self._get_llm()
        full_poem = ""

        # 1. 立即给前端一个响应提示
        await context.emit_chunk(f"\n🎨 [诗人正在斟酌字句... 题目：{prompt}]\n", content_type="text")

        # 2. 调用 astream 开始流式生成
        try:
            async for chunk in llm.astream([HumanMessage(content=f"请围绕主题“{prompt}”创作一首意境优美的诗词。直接开始作诗内容，不要有前言。")]):
                if chunk.content:
                    self.logger.info(f"[Poet-Worker] 🎨 流式输出: {chunk.content}")
                    # 关键：将每一块 token 即时推送到前端
                    await context.emit_chunk(chunk.content, content_type="text")
                    full_poem += chunk.content
            
            self.logger.info(f"[Poet-Worker] ✅ 创作完成并全量返回。长度: {len(full_poem)}")
            
            # 返回完整的诗篇给 Orchestrator 用于最后的处理
            return full_poem
            
        except Exception as e:
            self.logger.error(f"[Poet-Worker] ❌ 创作异常：{e}")
            return f"灵感枯竭了：{str(e)}"

if __name__ == "__main__":
    run_worker(
        PoetSubWorker,
        worker_id="poet-worker-process-1",
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
        redis_username=os.getenv("BYAI_REDIS_USERNAME")
    )
