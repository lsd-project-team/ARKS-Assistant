"""图片附件的校验、发送前压缩与消息标记；原图保留，只压缩发给模型的副本。"""

import base64
import html
import re
from pathlib import PurePosixPath

from app.infrastructure.images import (
    IMAGE_EXTENSIONS,
    MAX_SIDE,
    MEDIA_TYPES,
    SEND_MAX_BYTES,
    SEND_MAX_SIDE,
    inspect,
    media_type_of_file,
    prepare,
)

__all__ = [
    "IMAGE_EXTENSIONS",
    "MEDIA_TYPES",
    "MAX_SIDE",
    "SEND_MAX_BYTES",
    "SEND_MAX_SIDE",
    "describe",
    "expand_image_messages",
    "inspect",
    "is_image",
    "marker",
    "media_type_of_file",
    "path_marker",
    "prepare",
]

MARKER = re.compile(r"<attachment-image\b([^>]*?)/>")
ATTRIBUTE = re.compile(r'([a-z_]+)="([^"]*)"')


def is_image(filename):
    return PurePosixPath(filename).suffix.lower() in IMAGE_EXTENSIONS


def marker(identifier, filename):
    return f'<attachment-image id="{_attribute(identifier)}" name="{_attribute(filename)}" />'


def path_marker(path, filename=""):
    """项目内图片的标记；像素内容在模型请求边界才读取并展开。"""
    return (
        f'<attachment-image path="{_attribute(path)}" '
        f'name="{_attribute(filename or path)}" />'
    )


def _attribute(value):
    return html.escape(str(value), quote=True)


def describe(data):
    """图片的正文占位说明；像素内容只随消息发送，不写入正文档案。"""
    image_format, width, height, frames = inspect(data)
    frames_note = f"，共 {frames} 帧" if frames > 1 else ""
    content = (
        f"[图片] 格式 {image_format}，尺寸 {width}×{height}{frames_note}，"
        f"大小 {len(data) / (1024 * 1024):.1f} MB。\n"
        "图片已随消息直接提供给模型，可直接回答图片内容；正文读取工具不返回像素内容。"
    )
    notes = "原图保留并按上传内容显示；发送给模型前超过 2048 像素或 4 MB 时会在本机压缩。"
    return content, "readable", notes


def expand_image_messages(messages, store=None, cache=None, workspace=None):
    """在模型请求边界把图片标记换成多模态块；检查点只保存文本标记。"""
    cache = {} if cache is None else cache
    result = []
    for message in messages:
        if getattr(message, "type", "") != "human":
            result.append(message)
            continue
        text = (
            message.content
            if isinstance(message.content, str)
            else _text_of(message.content)
        )
        if not MARKER.search(text):
            result.append(message)
            continue
        blocks = [{"type": "text", "text": text}]
        for found in MARKER.finditer(text):
            attributes = {
                key: html.unescape(value) for key, value in ATTRIBUTE.findall(found.group(1))
            }
            key = found.group(0)
            try:
                media_type, encoded = (
                    cache[key] if key in cache else _load(store, workspace, attributes, cache, key)
                )
            except (FileNotFoundError, OSError, ValueError):
                name = attributes.get("name", "")
                blocks.append(
                    {
                        "type": "text",
                        "text": f"[图片{f' {name}' if name else ''}无法读取，未能发送给模型]",
                    }
                )
                continue
            blocks.append(
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{encoded}"}}
            )
        result.append(message.model_copy(update={"content": blocks}))
    return result


def _text_of(content):
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif isinstance(block, str):
            parts.append(block)
    return "\n".join(parts)


def _load(store, workspace, attributes, cache, key):
    if attributes.get("id"):
        if store is None:
            raise ValueError("图片附件不可用")
        path, _filename = store.download(attributes["id"])
        payload = path.read_bytes()
    elif attributes.get("path"):
        if workspace is None:
            raise ValueError("当前没有可读取的项目目录")
        payload = workspace.read_image(attributes["path"])["data"]
    else:
        raise ValueError("图片标记缺少定位信息")
    media_type, body = prepare(payload)
    cache[key] = (media_type, base64.b64encode(body).decode("ascii"))
    return cache[key]
