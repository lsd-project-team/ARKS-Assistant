"""未知供应商 tokenizer 的保守预算，避免中文按四字符估算而严重低估。"""

from langchain_core.messages.utils import count_tokens_approximately


def estimate_tokens(messages) -> int:
    rows = list(messages)
    approximate = count_tokens_approximately(rows)
    byte_estimate = sum(
        len(str(getattr(row, "content", row)).encode("utf-8")) / 3 + 8 for row in rows
    )
    return max(approximate, int(byte_estimate))
