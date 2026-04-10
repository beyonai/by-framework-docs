import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

# 加载环境
load_dotenv()

class TranslatorWorker(GatewayWorker):
    """
    文学翻译进程。
    具备 LLM 能力，专注于将中文诗歌翻译为优雅的英文。
    """

    def get_agent_types(self):
        return ["translator-agent"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    async def process_command(self, command: GatewayCommand, context: AgentContext):
        content = str(command.content)
        self.logger.info(f"[Translator-Worker] 🔠 接到翻译请求，原文长度：{len(content)}")
        
        llm = self._get_llm()
        full_translation = ""

        # 1. 立即给前端一个响应提示
        await context.emit_chunk(f"\n🔠 [翻译专家正在推敲译风...]\n", content_type="text")

        # 2. 调用 astream 开始流式生成
        try:
            prompt = f"你是一个精通中英诗歌互译的文学家。请将以下内容翻译成优雅、富有韵律的英文，并保留原文的意境：\n\n{content}"
            async for chunk in llm.astream([HumanMessage(content=prompt)]):
                if chunk.content:
                    # 关键：将每一块 token 即时推送到前端 (作为推理日志输出)
                    await context.emit_chunk(chunk.content, content_type="text", event_type="REASONING_LOG_DELTA")
                    full_translation += chunk.content
            
            self.logger.info(f"[Translator-Worker] ✅ 翻译完成。")
            
            # 返回完整的翻译结果
            return full_translation
            
        except Exception as e:
            self.logger.error(f"[Translator-Worker] ❌ 翻译异常：{e}")
            return f"译思断电了：{str(e)}"

if __name__ == "__main__":
    run_worker(
        TranslatorWorker,
        worker_id="translator-worker-1",
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
        redis_username=os.getenv("BYAI_REDIS_USERNAME")
    )
