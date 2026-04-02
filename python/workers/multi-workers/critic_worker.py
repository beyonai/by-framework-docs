import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker

# 加载环境
load_dotenv()

class CriticWorker(GatewayWorker):
    """
    文学评论进程。
    具备 LLM 能力，专注于对文学作品进行风格、意蕴和艺术水平的专业点评。
    """

    def get_capabilities(self):
        return ["critic-agent"]

    def _get_llm(self):
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True
        )

    async def process_command(self, command: GatewayCommand, context: AgentContext):
        poem_text = str(command.content)
        self.logger.info(f"[Critic-Worker] 🧐 接到点评请求，诗作长度：{len(poem_text)}")
        
        llm = self._get_llm()
        full_critique = ""

        # 1. 立即给前端一个响应提示
        await context.emit_chunk(f"\n🧐 [评论家正在深度鉴赏中...]\n", content_type="text")

        # 2. 调用 astream 开始流式生成
        try:
            prompt = f"你是一个毒舌但专业的文学评论家。请对以下这首诗进行深度点评，包括其意向、押韵、格调以及艺术水平：\n\n{poem_text}"
            async for chunk in llm.astream([HumanMessage(content=prompt)]):
                if chunk.content:
                    # 关键：将每一块 token 即时推送到前端 (作为推理日志输出)
                    await context.emit_chunk(chunk.content, content_type="text", event_type="REASONING_LOG_DELTA")
                    full_critique += chunk.content
            
            self.logger.info(f"[Critic-Worker] ✅ 点评完成。")
            
            # 返回完整的评论内容
            return full_critique
            
        except Exception as e:
            self.logger.error(f"[Critic-Worker] ❌ 点评异常：{e}")
            return f"点评卡壳了：{str(e)}"

if __name__ == "__main__":
    run_worker(
        CriticWorker,
        worker_id="critic-worker-1",
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
        redis_username=os.getenv("BYAI_REDIS_USERNAME")
    )
