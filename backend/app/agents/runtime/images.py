"""图片在模型请求边界展开为多模态块；检查点与摘要只保存文本标记。"""

import asyncio

from langchain.agents.middleware.types import AgentMiddleware

from app.modules.chat.image_attachments import expand_image_messages


class ImageAttachments(AgentMiddleware):
    """每次模型请求读取图片；同一运行内按标记缓存编码结果。

    store 提供聊天附件，workspace 提供项目内图片（view_image 的标记）。
    """

    def __init__(self, store=None, workspace=None):
        self.store = store
        self.workspace = workspace
        self.cache = {}

    async def awrap_model_call(self, request, handler):
        messages = await asyncio.to_thread(
            expand_image_messages,
            request.messages,
            self.store,
            self.cache,
            self.workspace,
        )
        return await handler(request.override(messages=messages))
