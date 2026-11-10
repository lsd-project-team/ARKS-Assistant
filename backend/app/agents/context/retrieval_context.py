"""给独立筛选器有限的追问背景，不改写当前问题，也不引入其他聊天。"""

from app.agents.runtime.privacy import redact
from app.modules.projects.context import project_prompt


def retrieval_context(messages, selections=(), *, max_chars=6000):
    recent, remaining = [], max_chars
    # 只使用当前有效分支、当前问题之前的六轮；每条截断须显式说明。
    for row in reversed(messages[-12:]):
        if remaining <= 0:
            break
        original = redact(row["content"])
        text = original[: min(1200, remaining)]
        recent.append({"role": row["role"], "content": text, "partial": len(text) < len(original)})
        remaining -= len(text)
    return {
        "project": project_prompt().strip(),
        "recent": list(reversed(recent)),
        "selection_paths": [row["path"] for row in selections],
    }


def contextual_query(question, context):
    """本地召回补充近期对象线索；最终适用性仍由筛选器核对。"""
    if not context or not context.get("recent"):
        return question
    # 最新纠正靠前；兼顾较早轮次的对象名，避免连续几次“继续”让本地召回丢失主题。
    recent = [row["content"][:200] for row in reversed(context["recent"])]
    return question + "\n近期对话（历史线索，最新在前）：\n" + "\n".join(recent)
