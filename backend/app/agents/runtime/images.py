"""图片在模型请求边界展开为多模态块；检查点与摘要只保存文本标记。"""

import asyncio
import hashlib

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import HumanMessage

from app.modules.chat.image_attachments import (
    expand_image_messages,
    path_marker,
    view_image_paths,
)


class ImageAttachments(AgentMiddleware):
    """每次模型请求读取图片；同一运行内按标记缓存编码结果。

    store 提供聊天附件，workspace 提供项目内图片（view_image 的调用记录）。
    view_image 只返回文本，这里在下一轮模型请求前统一注入一条图片消息，
    保证并行工具调用时 tool_use 后面仍紧跟全部 tool_result。
    """

    def __init__(self, store=None, workspace=None):
        self.store = store
        self.workspace = workspace
        self.cache = {}

    async def awrap_model_call(self, request, handler):
        base = list(request.messages)
        paths = view_image_paths(base) if self.workspace is not None else []
        if paths:
            text = "已通过 view_image 查看的项目图片：\n" + "\n".join(
                path_marker(path) for path in paths
            )
            digest = hashlib.sha1("\n".join(paths).encode("utf-8")).hexdigest()[:12]
            base.append(HumanMessage(content=text, id=f"view-images-{digest}"))
        messages = await asyncio.to_thread(
            expand_image_messages,
            base,
            self.store,
            self.cache,
            self.workspace,
        )
        return await handler(request.override(messages=messages))
