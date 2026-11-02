"""只追加一条核查说明，保留生成正文和来源文本，不执行改稿或补查。"""

import hashlib
import re

from langchain.agents.middleware.types import AgentMiddleware

from app.agents.runtime.answer_completion import final_message
from app.modules.knowledge.citations import CODE

SOURCE_LINK = re.compile(r"\[[^\]\n]*\]\((?:debug-issue|handover-source|source):[^\s)]+\)")
SOURCE_HEADING = re.compile(r"(?m)^[ \t]{0,3}来源[：:]")


def short_review_note(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing review note")
    value = re.sub(r"\s+", " ", value).strip()
    if (
        len(value) > 160
        or any(token in value for token in ("```", "~~~", "]("))
        or re.search(r"<[/!?]?[a-zA-Z]", value)
    ):
        raise ValueError("review note must be short plain text")
    # 只取第一个完整句子，避免复核说明变成另一份答案；保留小数与文件名中的英文句点。
    sentence = re.split(r"[。！？]", value, maxsplit=1)[0].rstrip("；;，,.!?")
    if not sentence:
        raise ValueError("review note must state a concrete issue")
    return sentence + "。"


def review_result(result):
    verdict = result.get("verdict")
    if verdict not in {"passed", "issues"}:
        raise ValueError("invalid review verdict")
    return {
        "verdict": verdict,
        "note": short_review_note(result.get("note")) if verdict == "issues" else "",
    }


def append_review_note(content, note):
    """仅插入说明；完整保留原有字符，尾部纯来源段仍放在最后。"""
    protected = [match.span() for match in CODE.finditer(content)]
    position = len(content)
    for match in reversed(list(SOURCE_HEADING.finditer(content))):
        if any(start <= match.start() < end for start, end in protected):
            continue
        tail = SOURCE_LINK.sub("", content[match.end() :])
        if not tail.strip(" \t\r\n-+*0123456789.,，、;；·|"):
            position = match.start()
            break
    before, after = content[:position], content[position:]
    newline = "\r\n" if "\r\n" in content else "\n"
    separator = "" if not before or before.endswith(newline * 2) else newline * 2
    return before + separator + note + (newline * 2 if after else "") + after


class AnswerReviewNote(AgentMiddleware):
    def __init__(self, emit=None):
        self.emit = emit

    async def awrap_model_call(self, request, handler):
        response = await handler(request)
        answer = final_message(response)
        if answer is None or answer.tool_calls:
            return response
        if (
            answer.additional_kwargs.get("answer_completion", {}).get("output", "complete")
            != "complete"
        ):
            return response
        # 优先具体事实问题，其次具体引用问题；没有问题不补“通过”或通用免责声明。
        note = answer.additional_kwargs.get(
            "knowledge_review_note"
        ) or answer.additional_kwargs.get("source_review_note")
        original = answer.text
        if note:
            try:
                note = short_review_note(note)
            except ValueError:
                return response
            if note not in answer.text:
                answer.content = append_review_note(answer.text, note)
        if self.emit:
            final = answer.text
            offset = 0
            while offset < len(original) and original[offset] == final[offset]:
                offset += 1
            self.emit(
                "answer_review_note",
                {
                    "note": note or "",
                    "original_sha256": hashlib.sha256(original.encode()).hexdigest(),
                    "insertion_start": offset,
                    "insertion_length": len(final) - len(original),
                },
            )
        return response
