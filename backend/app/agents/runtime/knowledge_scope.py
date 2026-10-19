"""模型判断候选资料的相关性；程序核对固定版本与逐字摘录，保留回答范围。"""

import re
import unicodedata

from app.agents.runtime.privacy import redact
from app.modules.knowledge.citations import CODE

SELECTION_GUIDANCE = """
先逐条读 records，按 question 的设备、日期时间范围、试验阶段、所问事实判断相关性，
再复核 answer。检索命中只是候选；标题、关键词相似不代表符合要求，正文可跨日期，须定位所问阶段。
比较问法可选多个阶段；单阶段查询不可把其他日期的结果混入。历史记录缺少条件不代表当前已验证。
返回 selections 数组，每项为：
{"reference":"records中的完整reference","reason":"符合本题哪些条件",
 "excerpts":[{"field":"content中的字段名","text":"该字段内逐字连续原文"}]}。
只选支撑本题的原文片段，保留理解它必需的时间、条件、单位、结果和原因归属，不能改写摘录。
同一记录可选多段；用户明确索要完整原文时选对应原文字段的全文。
没有合适资料时 selections=[]，说明本轮资料不足，不能据此断言全库没有。
answer中的经验事实与引用必须属于选定范围；删除不相关阶段的内容与引用。
第一次复核无论passed还是revised，都必须填写选定摘录，不能把selections当作固定空数组。
再次复核时 records 已限制为上轮选定片段，不得扩大范围；selections=[]默认表示保持已选范围。
若终审确认整批所选资料都不符合本题，须明确返回scope_action="reject"并在reason说明依据。
用户要求原图时，引用选定记录的真实reference，页面负责展示该版本全部原图。
末尾允许一两句直接相关、有依据的延伸引导，以建议语气呈现，不强加、不重复、不编造已完成的事实；
用户只要原文、明确不要建议时不追加引导。不固定套用“还想了解什么”。
延伸引导以可继续了解的问题、可比较的资料、需核对的证据为主，不主动安排现场调参顺序或新的设备操作。
"""


def restored_excerpt(original, text):
    """容忍模型摘录的空格/全半角排版差异，最终总是还原来源中的连续原文。"""
    original = redact(original)
    if text in original:
        return text
    characters, positions = [], []
    for index, character in enumerate(original):
        for normalized in unicodedata.normalize("NFKC", character):
            if not normalized.isspace():
                characters.append(normalized)
                positions.append(index)
    needle = "".join(c for c in unicodedata.normalize("NFKC", text) if not c.isspace())
    start = "".join(characters).find(needle) if needle else -1
    if start < 0:
        raise ValueError("fabricated excerpt")
    return original[positions[start] : positions[start + len(needle) - 1] + 1]


def reference_target(value):
    matches = re.findall(r"debug-issue:[\w-]+/\d+", value) if isinstance(value, str) else []
    return matches[0] if len(matches) == 1 else None


def selected_records(result, records):
    """拒绝未知版本、伪造或空摘录；相关性仍是模型判断，不把出处校验称为语义证明。"""
    choices = result.get("selections")
    if not isinstance(choices, list) or len(choices) > len(records):
        raise ValueError("invalid selection")
    available = {reference_target(row["reference"]): row for row in records}
    selected, seen = [], set()
    for item in choices:
        reference = reference_target(item["reference"])
        if reference not in available or reference in seen or not item.get("reason"):
            raise ValueError("unknown selection")
        row, content = available[reference], {}
        excerpts = item.get("excerpts")
        if not isinstance(excerpts, list) or not excerpts or len(excerpts) > 30:
            raise ValueError("empty selection")
        for excerpt in excerpts:
            field, text = excerpt["field"], excerpt["text"]
            original = row["content"].get(field)
            if not isinstance(text, str) or not text.strip() or not isinstance(original, str):
                raise ValueError("invalid excerpt")
            content.setdefault(field, []).append(restored_excerpt(original, text))
        selected.append(
            {**row, "content": {key: "\n\n".join(value) for key, value in content.items()}}
        )
        seen.add(reference)
    return selected


def scope_problems(question, answer, records):
    prose = CODE.sub("", answer)
    used = set(re.findall(r"debug-issue:[\w-]+/\d+", prose))
    allowed = {
        target
        for row in records
        for target in re.findall(r"debug-issue:[\w-]+/\d+", row["reference"])
    }
    issues = []
    if used - allowed:
        issues.append("回答引用了未选定的记录或版本，请删除越界内容和引用，只回答本题选定范围。")
    if records and re.search(r"原图|图片|记录文字|来源|引用", question) and allowed - used:
        issues.append("用户要求记录或原图，请引用每条实际选定记录的真实reference，不能遗漏。")
    return "".join(issues)


def scoped_fallback(records):
    if not records:
        return (
            "本轮资料尚未完成范围核对，暂不能据此给出可靠结论。"
            "可补充具体记录标题或时间段，继续核对。"
        )
    blocks = ["本轮回答未通过复核，以下为本题已选定的原文片段："]
    for row in records:
        original = "\n\n".join(row["content"].values())
        excerpt = redact(original[:3000])
        if len(original) > 3000:
            excerpt += "\n（原文较长，此处仅为部分摘录）"
        blocks.append("> " + excerpt.replace("\n", "\n> ") + "\n\n" + row["reference"])
    return "\n\n".join(blocks)
