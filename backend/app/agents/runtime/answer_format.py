"""校验展示协议；损坏JSON/围栏最多修正一次，不进行事实或排版复核。"""

import json

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import HumanMessage

from app.agents.runtime.answer_completion import final_message
from app.modules.chat.rich_presentation import FENCE, MAX_DOCUMENT_BYTES, rich_documents


def broken_syntax(fragment):
    if len(fragment.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        return False
    opening = FENCE.match(fragment)
    if not opening:
        return False
    body = fragment[opening.end() :].strip()
    marker = opening[1]
    last = body.splitlines()[-1].strip() if body else ""
    if not last or set(last) != {marker[0]} or len(last) < len(marker):
        return True
    body = body.rsplit("\n", 1)[0] if "\n" in body else ""
    try:
        json.loads(body)
    except ValueError:
        return True
    return False


class AnswerFormatValidation(AgentMiddleware):
    def __init__(self, emit):
        self.emit = emit
        self.repairs = 0

    async def awrap_model_call(self, request, handler):
        response = await handler(request)
        for _attempt in range(2):
            answer = final_message(response)
            if answer is None or answer.tool_calls:
                return response
            documents = list(rich_documents(answer.text, include_incomplete=True))
            errors = [
                {"start": start, "end": end, "code": "invalid_or_incomplete_rich_content"}
                for start, end, document in documents
                if document is None
            ]
            self.emit(
                "answer_format_validation",
                {"passed": not errors, "blocks": len(documents), "errors": errors},
            )
            complete = (
                answer.additional_kwargs.get("answer_completion", {}).get("output", "complete")
                == "complete"
            )
            if (
                not errors
                or self.repairs
                or not complete
                or not any(
                    document is None and broken_syntax(answer.text[start:end])
                    for start, end, document in documents
                )
            ):
                return response
            self.repairs += 1
            correction = HumanMessage(
                content=(
                    "系统展示语法校验（不是新的用户问题，不进行结论复核）："
                    "上一条回答的rich-content JSON或围栏语法损坏，无法渲染。"
                    "只修复JSON括号、引号、转义及围栏闭合，保持全部原文事实、块id、来源路径、版本和行号。"
                    "不要补造内容，不改变展示类型，不重新检索或解释修复过程；返回完整的修正后回答。"
                )
            )
            # 仍走原模型、引用与格式校验链；一次未恢复即交给原有局部降级，不无限重试。
            response = await handler(
                request.override(messages=[*request.messages, answer, correction])
            )
        return response
