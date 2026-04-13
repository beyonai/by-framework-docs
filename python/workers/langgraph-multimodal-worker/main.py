import os
import base64
from pathlib import Path
from typing import Annotated, Any, List
from dotenv import load_dotenv
import httpx

from by_framework.core.protocol import ByaiAskAgentCommand
from by_framework.core.protocol.byai_codec import deserialize_byai_content
from by_framework.core.protocol.message import BaiYingMessage, MessageContent
from by_framework.worker import AgentContext, ByaiWorker, run_worker
from by_framework_history_byclaw import ByClawHistoryBackend
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, add_messages

# 加载 .env 文件中的环境变量
load_dotenv(Path(__file__).parent / ".env")

# 支持作为图片处理的文件类型（含泛型 "image"）
IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image"}


class MultimodalState(Annotated[dict, "MultimodalState"]):
    """LangGraph state for multimodal conversations."""
    messages: Annotated[list[BaseMessage], add_messages]


def extract_text_and_images(content: Any) -> tuple[str, List[dict]]:
    """从 ByaiAskAgentCommand.content 中提取文本和图片。

    content 实际类型可能是：
    - str
    - BaiYingMessage（反序列化后的对象）
    - dict（wire format: {'role': 'user', 'content': {'text': ..., 'files': [...]}}）
    - list[上述类型]

    图片来自 content.files 中 fileType 为图片类型的 fileUrl。

    Returns:
        (text, image_blocks) 元组，image_blocks 为 langchain 格式的内容块。
    """
    normalized = deserialize_byai_content(content)

    if isinstance(normalized, str):
        return normalized, []

    if isinstance(normalized, BaiYingMessage):
        return _extract_from_message(normalized)

    if isinstance(normalized, dict):
        return _extract_from_dict(normalized)

    if isinstance(normalized, list):
        texts = []
        all_images = []
        for item in normalized:
            if isinstance(item, BaiYingMessage):
                text, images = _extract_from_message(item)
                if text:
                    texts.append(text)
                all_images.extend(images)
            elif isinstance(item, dict):
                text, images = _extract_from_dict(item)
                if text:
                    texts.append(text)
                all_images.extend(images)
            elif isinstance(item, str):
                texts.append(item)
        return "\n\n".join(texts), all_images

    return str(normalized), []


def _extract_from_message(message: BaiYingMessage) -> tuple[str, List[dict]]:
    """从 BaiYingMessage 对象中提取文本和图片。"""
    if isinstance(message.content, str):
        return message.content, []

    if isinstance(message.content, MessageContent):
        text = message.content.text or ""
        images = _extract_images_from_files(message.content.files)
        return text, images

    return str(message.content), []


def _extract_from_dict(msg: dict) -> tuple[str, List[dict]]:
    """从 wire format dict 中提取文本和图片。

    格式: {'role': 'user', 'content': {'text': '...', 'files': [...]}}
    """
    content = msg.get("content", {})
    if isinstance(content, str):
        return content, []

    text = content.get("text", "") or ""
    files = content.get("files", [])
    images = _extract_images_from_dicts(files)
    return text, images


def _extract_images_from_files(files: list) -> List[dict]:
    """从 MessageFile 列表中提取图片（同步，返回 URL 引用，后续统一转 base64）。"""
    result = []
    for f in files:
        file_type = f.fileType if hasattr(f, "fileType") else f.get("fileType", "")
        file_url = f.fileUrl if hasattr(f, "fileUrl") else f.get("fileUrl", "")
        if _is_image_file(file_type, file_url):
            result.append(file_url)
    return result


def _extract_images_from_dicts(files: list) -> List[dict]:
    """从 dict 格式的 files 列表中提取图片 URL。"""
    result = []
    for f in files:
        file_type = f.get("fileType", "") if isinstance(f, dict) else ""
        file_url = f.get("fileUrl", "") if isinstance(f, dict) else ""
        if _is_image_file(file_type, file_url):
            result.append(file_url)
    return result


# URL 后缀到 MIME 类型的映射
_MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def _mime_from_url(url: str) -> str:
    """从 URL 后缀推断 MIME 类型。"""
    path = url.lower().split("?")[0]
    for ext, mime in _MIME_MAP.items():
        if path.endswith(ext):
            return mime
    return "image/png"  # 默认


async def _url_to_base64_data_url(url: str) -> str:
    """下载图片并转为 base64 data URL。"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.content
    mime = resp.headers.get("content-type", "") or _mime_from_url(url)
    if not mime.startswith("image/"):
        mime = _mime_from_url(url)
    b64 = base64.b64encode(data).decode()
    return f"data:{mime};base64,{b64}"


async def convert_image_urls_to_base64(image_urls: List[str]) -> List[dict]:
    """将图片 URL 列表下载并转为 base64 格式的 langchain content blocks。"""
    blocks = []
    for url in image_urls:
        try:
            data_url = await _url_to_base64_data_url(url)
            blocks.append({"type": "image_url", "image_url": {"url": data_url}})
        except Exception:
            # 下载失败则回退到原始 URL（某些 API 可能支持）
            blocks.append({"type": "image_url", "image_url": {"url": url}})
    return blocks


def _is_image_file(file_type: str, url: str) -> bool:
    """判断文件是否为图片（通过 fileType 或 URL 后缀）。"""
    if file_type and (file_type in IMAGE_TYPES or file_type.startswith("image/")):
        return True
    return _looks_like_image(url)


def _looks_like_image(url: str) -> bool:
    """通过 URL 后缀判断是否为图片。"""
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    return any(url.lower().split("?")[0].endswith(ext) for ext in image_extensions)


class LangGraphMultimodalWorker(ByaiWorker):
    """
    基于 LangGraph 实现的多模态问答 Worker。

    支持：
    - 文本问答
    - 图片理解（通过 vision 模型）
    - 多轮对话记忆（checkpoint）
    - 流式输出
    """

    def get_agent_types(self) -> List[str]:
        """返回此 Worker 支持的智能体类型列表。"""
        return ["langgraph-multimodal-agent"]

    def _get_memory_saver(self) -> MemorySaver:
        """获取或创建 MemorySaver 单例，用于 checkpoint 持久化。"""
        if not hasattr(self, "_memory_saver"):
            self._memory_saver = MemorySaver()
        return self._memory_saver

    def _get_llm(self) -> ChatOpenAI:
        """获取 LLM 实例。默认使用支持 vision 的模型。"""
        return ChatOpenAI(
            model=os.getenv("MULTIMODAL_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=True,
        )

    def _build_graph(self):
        """构建 LangGraph 图。"""
        workflow = StateGraph(MultimodalState)

        async def analyze_multimodal(state: MultimodalState):
            """分析多模态输入并生成回复。"""
            llm = self._get_llm()
            response = await llm.ainvoke(state["messages"])
            return {"messages": [response]}

        workflow.add_node("analyzer", analyze_multimodal)
        workflow.set_entry_point("analyzer")
        workflow.set_finish_point("analyzer")

        return workflow.compile(checkpointer=self._get_memory_saver())

    async def process_command(
        self, command: ByaiAskAgentCommand, context: AgentContext
    ) -> Any:
        """处理来自 Gateway 的命令。"""
        self.logger.info(f"[Multimodal-Worker] Processing command: {command.header.message_id}")

        # 1. 提取文本和图片 URL
        text, image_urls = extract_text_and_images(command.content)

        self.logger.info(
            f"[Multimodal-Worker] 📥 收到请求 - 文本长度: {len(text)}, 图片数量: {len(image_urls)}"
        )

        # 2. 将图片 URL 转为 base64 data URL（兼容不支持 URL 的模型）
        if image_urls:
            image_blocks = await convert_image_urls_to_base64(image_urls)
            content_blocks = [{"type": "text", "text": text}] + image_blocks
            human_message = HumanMessage(content=content_blocks)
            self.logger.info(f"[Multimodal-Worker] 🖼️ 包含 {len(image_blocks)} 张图片进行视觉分析")
        else:
            human_message = HumanMessage(content=text)

        # 3. 构建并运行图
        graph = self._build_graph()
        config = {"configurable": {"thread_id": context.session_id}}

        initial_state = {"messages": [human_message]}

        full_response = ""

        # 4. 流式执行
        async for event in graph.astream(initial_state, config=config, stream_mode="messages"):
            message, metadata = event
            if message.content:
                full_response += message.content
                await context.emit_chunk(message.content, content_type="1002")

        self.logger.info(f"[Multimodal-Worker] ✅ 回复完成 - 响应长度: {len(full_response)}")
        return full_response


if __name__ == "__main__":
    run_worker(
        LangGraphMultimodalWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "langgraph-multimodal-worker-1"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
        history_backend=ByClawHistoryBackend(base_url=os.getenv("BYAI_HISTORY_URL", "http://10.45.134.185:8086"))
    )
