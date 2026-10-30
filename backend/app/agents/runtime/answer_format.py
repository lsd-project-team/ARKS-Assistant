"""只校验模型选择的展示协议，保留原文交给前端渲染或降级。"""

from langchain.agents.middleware.types import AgentMiddleware

from app.agents.runtime.answer_completion import final_message
from app.modules.chat.rich_presentation import rich_documents


class AnswerFormatValidation(AgentMiddleware):
    def __init__(self, emit):
        self.emit = emit

    async def awrap_model_call(self, request, handler):
        response = await handler(request)
        answer = final_message(response)
        if answer is None or answer.tool_calls:
            return response
        documents = list(rich_documents(answer.text, include_incomplete=True))
        errors = [
            {"start": start, "end": end, "code": "invalid_or_incomplete_rich_content"}
            for start, end, document in documents
            if document is None
        ]
        # 格式问题不触发模型改稿，也不投影或截断正文；前端已有原文降级展示。
        self.emit(
            "answer_format_validation",
            {"passed": not errors, "blocks": len(documents), "errors": errors},
        )
        return response
