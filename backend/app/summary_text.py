"""摘要展示与框架包装分离；用户纠正正文时保留原文档案的引用。"""


def summary_parts(text: str) -> tuple[str, str, str]:
    marker = "\n<summary>\n"
    if text.startswith("You are in the middle of a conversation that has been summarized."):
        start, end = text.find(marker), text.rfind("\n</summary>")
        if start >= 0 and end > start and text[end:] == "\n</summary>":
            start += len(marker)
            return text[:start], text[start:end], text[end:]
    prefix = "Here is a summary of the conversation to date:\n\n"
    if text.startswith(prefix):
        return prefix, text[len(prefix) :], ""
    return "", text, ""
