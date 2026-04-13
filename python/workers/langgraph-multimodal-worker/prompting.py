"""System prompts for the multimodal Q&A agent."""

DEFAULT_MULTIMODAL_SYSTEM_PROMPT = """你是一个多模态智能助手，擅长理解和分析文本与图片内容。

你的能力包括：
1. 图像理解：能够分析图片内容、识别物体、场景、文字等
2. 文本问答：基于图片和文本进行综合分析和回答
3. 多轮对话：支持就同一话题进行深入讨论

请用清晰、专业且友好的方式回答用户的问题。"""


def build_multimodal_system_prompt(session_id: str = None) -> str:
    """Build system prompt with optional session context."""
    prompt = DEFAULT_MULTIMODAL_SYSTEM_PROMPT
    if session_id:
        prompt += f"\n\n当前会话ID: {session_id}"
    return prompt
