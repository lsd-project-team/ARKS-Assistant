"""输入框斜杠命令的公共解析；只认消息开头的独立命令，正文中的斜杠不算。"""

import re

# 内置命令占用这些词，MCP 触发命令不能重名，避免同一句话有两种含义。
RESERVED = frozenset({"context", "compact", "记录问题", "record-issue", "修改代码"})
TRIGGER = re.compile(r"^[A-Za-z0-9_\-\u4e00-\u9fff]{1,20}$")
LEADING = re.compile(r"^\s*/(?P<word>[^\s/]{1,20})(?=\s|$)")


def normalize_trigger(value: str) -> str:
    """校验触发命令并去掉前导斜杠；空字符串表示按问题自动选择。"""
    text = (value or "").strip()
    if text.startswith("/"):
        text = text[1:].strip()
    if not text:
        return ""
    if not TRIGGER.fullmatch(text):
        raise ValueError("触发命令只能使用中文、字母、数字、下划线或短横线，长度 1–20")
    if text.casefold() in {item.casefold() for item in RESERVED}:
        raise ValueError("触发命令与内置命令重名")
    return text


def split_command(content: str, triggers) -> tuple[str | None, str]:
    """拆出消息开头的 MCP 触发命令，返回 (命令, 去掉命令后的正文)。

    没有命中任何已配置命令时命令为 None，正文原样返回。
    """
    text = content or ""
    match = LEADING.match(text)
    if not match:
        return None, text
    word = match.group("word").casefold()
    for trigger in triggers:
        if trigger and trigger.casefold() == word:
            return trigger, text[match.end() :].strip()
    return None, text


def used_triggers(texts, triggers) -> set[str]:
    """消息序列里出现过的触发命令；用于在对话内保持该命令对应的来源。"""
    found = set()
    for text in texts:
        trigger, _rest = split_command(text, triggers)
        if trigger:
            found.add(trigger)
    return found
