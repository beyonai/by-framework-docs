"""Test script for multimodal worker."""

import asyncio
from by_framework.core.protocol.message import BaiYingMessage, BaiYingMessageRole, MessageContent, MessageFile
from main import (
    LangGraphMultimodalWorker,
    extract_text_and_images,
    _extract_from_dict,
    _is_image_file,
    _looks_like_image,
    _mime_from_url,
    convert_image_urls_to_base64,
    IMAGE_TYPES,
)
from by_framework.worker import ByaiWorker


def test_extract_from_str():
    """纯文本提取。"""
    text, images = extract_text_and_images("你好")
    assert text == "你好"
    assert images == []
    print("✅ extract_from_str passed")


def test_extract_from_baiying_message_with_image():
    """BaiYingMessage 包含图片文件，返回 URL 列表。"""
    content = MessageContent(
        text="描述一下这张图片",
        files=[
            MessageFile(fileId=1, fileUrl="https://example.com/photo.jpg", fileType="image/jpeg", fileName="photo.jpg"),
            MessageFile(fileId=2, fileUrl="https://example.com/doc.pdf", fileType="application/pdf", fileName="doc.pdf"),
        ],
    )
    msg = BaiYingMessage(role=BaiYingMessageRole.USER, content=content)
    text, image_urls = extract_text_and_images(msg)
    assert text == "描述一下这张图片"
    assert len(image_urls) == 1
    assert image_urls[0] == "https://example.com/photo.jpg"
    print("✅ extract_from_baiying_message_with_image passed")


def test_extract_from_dict_wire_format():
    """测试实际 wire format dict，返回 URL 列表。"""
    msg = {
        "role": "user",
        "content": {
            "text": "分析一下这个图片",
            "files": [
                {
                    "fileId": 1776060904691,
                    "fileUrl": "http://localhost:9000/test.png",
                    "fileType": "image",
                    "fileName": "test.png",
                }
            ],
        },
    }
    text, image_urls = extract_text_and_images(msg)
    assert text == "分析一下这个图片"
    assert image_urls == ["http://localhost:9000/test.png"]
    print("✅ extract_from_dict_wire_format passed")


def test_is_image_file():
    """测试图片判断逻辑。"""
    assert _is_image_file("image", "http://x.com/a.png") is True
    assert _is_image_file("image/jpeg", "http://x.com/a") is True
    assert _is_image_file("application/pdf", "http://x.com/a.pdf") is False
    assert _is_image_file("", "http://x.com/a.png") is True
    assert _is_image_file("", "http://x.com/a.pdf") is False
    print("✅ is_image_file passed")


def test_mime_from_url():
    """测试 MIME 类型推断。"""
    assert _mime_from_url("http://x.com/a.jpg") == "image/jpeg"
    assert _mime_from_url("http://x.com/a.png?w=100") == "image/png"
    assert _mime_from_url("http://x.com/a.webp") == "image/webp"
    assert _mime_from_url("http://x.com/unknown") == "image/png"  # 默认
    print("✅ mime_from_url passed")


def test_worker_class_methods():
    assert issubclass(LangGraphMultimodalWorker, ByaiWorker)
    assert LangGraphMultimodalWorker.get_agent_types(None) == ["langgraph-multimodal-agent"]
    print("✅ worker class methods test passed")


if __name__ == "__main__":
    test_extract_from_str()
    test_extract_from_baiying_message_with_image()
    test_extract_from_dict_wire_format()
    test_is_image_file()
    test_mime_from_url()
    test_worker_class_methods()
    print("\n🎉 All tests passed!")