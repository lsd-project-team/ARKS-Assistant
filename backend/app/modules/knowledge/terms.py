"""本地知识检索分词，短设备标识保持精确匹配。"""

import re
import unicodedata


def terms(text: str) -> set[str]:
    text = unicodedata.normalize("NFKC", text).casefold()
    result = set(re.findall(r"[a-z_][a-z0-9_]+", text))
    ignored = {"源码", "代码", "项目", "函数", "解释", "什么", "如何", "一下", "请问", "问题"}
    ignored |= {
        "cs",
        "md",
        "ts",
        "js",
        "py",
        "json",
        "the",
        "and",
        "is",
        "to",
        "of",
        "in",
        "on",
        "an",
        "as",
        "by",
        "or",
    }
    for fragment in re.findall(r"[\u4e00-\u9fff]+", text):
        result.update(fragment[index : index + 2] for index in range(len(fragment) - 1))
    return result - ignored
