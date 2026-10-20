"""无模型排版：只改分段和强调，不丢弃答案、不改变事实内容。"""

import re

from app.modules.knowledge.citations import CODE


def parameter_list(line):
    """只把带名称的多项数值组合换成列表，公式、符号运算及原文引述不进入这里。"""
    if (
        line.count("+") < 3
        or "|" in line
        or "**" in line
        or re.search(r"[。！？；=<>]|\d\s*[*/]\s*\d", line)
    ):
        return line
    match = re.fullmatch(r"(\s*)(?:[-*]\s+)?(.+)", line)
    if not match:
        return line
    indent, body = match.groups()
    label = ""
    first, separator, rest = body.partition("：")
    if separator and "+" not in first and len(first) <= 20:
        label, body = first + separator, rest
    if not re.search(r"参数|组合|方案|配置|设置", label):
        return line
    items = [part.strip() for part in body.split("+")]
    if not all(
        len(item) <= 45
        and re.search(r"\d", item)
        and len(re.findall(r"[\u4e00-\u9fff]", item)) >= 2
        for item in items
    ):
        return line
    prefix = indent + ("  " if label else "")
    listing = "\n".join(prefix + "- " + item for item in items)
    return (indent + "- " + label + "\n" if label else "") + listing


def present(answer, question):
    if re.search(r"原文|逐字|提取|保留格式|保持格式|整段加粗|全部加粗|一段话|不要分段", question):
        return answer
    protected = []

    def keep(match):
        protected.append(match.group())
        return f"\x00{len(protected) - 1}\x00"

    text = CODE.sub(keep, answer)
    text = re.sub(r"(?m)^\s*>.*$", keep, text)
    text = re.sub(r"\[[^\]\n]*\]\([^\n)]+\)", keep, text)
    text = re.sub(r"\*\*([^*\n]{48,})\*\*", r"\1", text)
    text = "\n".join(parameter_list(line) for line in text.split("\n"))
    blocks = []
    for block in re.split(r"\n\s*\n", text):
        # 引用、列表、表格、代码与标题保留结构；只在完整句子之间拆长正文。
        if len(block) > 180 and not re.search(r"(?m)^\s*(?:[-*#>|]|\d+[.)、]|\x00\d+\x00$)", block):
            group = ""
            for sentence in re.split(r"(?<=[。！？])", block):
                if group and len(group) + len(sentence) > 150:
                    blocks.append(group)
                    group = ""
                group += sentence
            blocks.append(group)
        else:
            blocks.append(block)
    text = "\n\n".join(blocks)
    return re.sub(r"\x00(\d+)\x00", lambda match: protected[int(match[1])], text)


def format_answer(answer, question, emit):
    """在执行器最终返回处排版，不能被稍后读取的检查点原稿覆盖。"""
    try:
        formatted = present(answer, question)
    except Exception:
        emit("answer_presentation", {"changed": False, "code": "formatting_failed"})
        return answer
    if formatted != answer:
        emit("answer_presentation", {"changed": True, "scope": "仅分段与强调"})
    return formatted
