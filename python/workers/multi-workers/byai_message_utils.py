"""Helpers for extracting text from typed Byai command content."""

from __future__ import annotations

from typing import Any

from by_framework.core.protocol.byai_codec import deserialize_byai_content
from by_framework.core.protocol.message import BaiYingMessage, MessageContent


def extract_byai_text(content: Any) -> str:
    """Flatten Byai or wire-format content into a plain-text payload."""

    normalized = deserialize_byai_content(content)
    return _extract_any_text(normalized)


def _extract_any_text(content: Any) -> str:
    """Extract text from supported Byai content shapes."""

    if isinstance(content, str):
        return content

    if isinstance(content, BaiYingMessage):
        return _extract_message_text(content)

    if isinstance(content, dict):
        payload = content.get("content", "")
        if isinstance(payload, dict):
            return str(payload.get("text", ""))
        return str(payload)

    if isinstance(content, list):
        return "\n\n".join(
            text for text in (_extract_any_text(item) for item in content) if text
        )

    if content is None:
        return ""

    return str(content)

def _extract_message_text(message: BaiYingMessage) -> str:
    """Extract user-visible text from a single BaiYing message."""

    if isinstance(message.content, MessageContent):
        return message.content.text
    return _extract_any_text(message.content)
