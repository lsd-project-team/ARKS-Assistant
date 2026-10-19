"""只从本轮用户命令和受控的续接问题恢复实施意图，不读取模型或资料授权。"""

import re

from app.agents.analysis.policy import CONTINUE_QUESTION

ACTION = (
    r"(?:修改|改一下|修复|实现|编写|写代码|生成补丁|尝试开发|继续开发"
    r"|新增|添加|删除|移除|去掉|重命名|重构|调整|改成|改为|更新|完善|补充)"
)
EDIT_REQUEST = re.compile(
    r"^(?:(?:请(?:你)?|帮我|给我|尝试|开始|继续|直接|现在|需要|我要|我想)\s*)*"
    r"(?:(?:在|对|针对).{1,30}?)?"
    r"(?:" + ACTION + r"|(?:按照|按|把|将).{1,30}" + ACTION + r")"
)
DISCUSSION_ONLY = re.compile(
    r"先讨论|先回答|先(?:给|提供|看).{0,20}方案|只(?:要|做|需|是)?.{0,8}(?:分析|解释|方案)"
)
# 否定必须作用于同一分句；“原件不变；仅修改副本”不能跨分号合成禁止修改。
NEGATIVE = r"(?:不(?:要|需要|用|能|允许)?|暂不|先不|别|禁止)[^，,。！!？?；;\n]{0,10}"
EDIT_NEGATIVE = re.compile(
    NEGATIVE + r"(?:修改|实现|编写|写代码|修复|新增|添加|删除|重构|动代码|动手|实施|开发)"
)
READ_NEGATIVE = re.compile(NEGATIVE + r"(?:通读|阅读|开始|执行)")
INQUIRY = re.compile(
    r"如何|怎样|怎么|为什么|为何|哪些|哪种|多少|多久|何时|什么|是否|能否|可否|有没有|是不是|吗|么|[?？]"
)
TEMPORARY_DISCUSSION = re.compile(
    r"先讨论|先回答(?:我)?|先(?:给|提供|看).{0,20}?方案"
    r"|先(?:不|不要|不用)(?:开始|修改|动代码|实现|编写)"
)
CLAUSE_BOUNDARY = r"[，,。！!？?；;\n]"
REQUIREMENT_FIELDS = {
    "title": r"标题|修改名称",
    "goal": r"目标|需求描述",
    "acceptance_criteria": r"验收标准|验收条件|验收要求",
    "constraints": r"约束|限制条件",
    "allowed_paths": r"修改范围|文件范围|允许路径|允许修改路径",
}
REQUIREMENT_ITEM = (
    r"(?:本次|当前|这个|这次|已有|的)*"
    r"(?:需求约定|需求契约|" + "|".join(REQUIREMENT_FIELDS.values()) + r")"
    r"(?!函数|方法|检查|校验|变量|类)"
)
REQUIREMENT_TARGET = REQUIREMENT_ITEM + r"(?:\s*(?:、|和|及|与)\s*" + REQUIREMENT_ITEM + r")*"
REQUIREMENT_REQUEST = re.compile(
    r"^(?:(?:请(?:你)?|帮我|给我|直接|现在|需要|我要|我想)\s*)*"
    r"(?:(?:为|给)(?:本次修改|这个副本|本副本)\s*)?"
    r"(?:(?:把|将)(?P<before>"
    + REQUIREMENT_TARGET
    + r")\s*"
    + ACTION
    + r"|"
    + ACTION
    + r"\s*(?P<after>"
    + REQUIREMENT_TARGET
    + r"))"
)


def command_text(request_text):
    """授权判断忽略粘贴源码和引用；原始正文另行留存，不用清洗结果冒充原文。"""
    text = effective_request(request_text)
    text = re.sub(r"(?ms)^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?(?:^[ \t]*\1[ \t]*$|\Z)", "", text)
    text = re.sub(r"(?s)<code_selection\b[^>]*>.*?(?:</code_selection>|\Z)", "", text)
    return re.sub(r"(?m)^[ \t]*>.*$", "", text)


def requested_requirement_fields(request_text):
    text = command_text(request_text)
    # 允许“只补验收，不修改代码”；讨论和全局否定仍不能授权约定变更。
    text = re.sub(
        r"(?:不要|不|别|禁止)修改(?:任何)?代码\s*(?=" + CLAUSE_BOUNDARY + r"|$)", "", text
    )
    if DISCUSSION_ONLY.search(text) or READ_NEGATIVE.search(text):
        return set()
    clauses = [clause.strip() for clause in re.split(CLAUSE_BOUNDARY, text)]
    fields = set()
    prohibited = set()
    for clause in clauses:
        if EDIT_NEGATIVE.search(clause):
            specific = {
                key for key, pattern in REQUIREMENT_FIELDS.items() if re.search(pattern, clause)
            }
            if not specific or re.search(r"需求约定|需求契约", clause):
                return set()
            prohibited.update(specific)
            continue
        match = REQUIREMENT_REQUEST.match(clause)
        if not match or INQUIRY.search(clause) or EDIT_NEGATIVE.search(clause):
            continue
        target = match.group("before") or match.group("after")
        if re.search(r"需求约定|需求契约", target):
            fields.update(REQUIREMENT_FIELDS)
        else:
            fields.update(
                key for key, pattern in REQUIREMENT_FIELDS.items() if re.search(pattern, target)
            )
    return fields - prohibited


def _without_protected_objects(text):
    # 只移除完整的局部保护约束，不能把“原件和副本”裁成只有原件。
    objects = (
        r"测试(?:代码|文件|用例)?|点值替身|工程文件|配置(?:文件)?|调用片段|其他文件"
        r"|[A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+"
        r"|需求约定|需求契约|" + "|".join(REQUIREMENT_FIELDS.values())
    )
    if re.search(r"副本|隔离", text):
        objects += r"|原件|原文件|原始文件"
    item = r"(?:" + objects + r")"
    constraint = re.compile(
        r"(?:不要|不需要|不用|不|别|禁止)(?:再)?(?:修改|改动|改)"
        r"(?P<objects>" + item + r"(?:\s*(?:、|或|和|以及|及|与)\s*" + item + r")*)"
        r"\s*(?=" + CLAUSE_BOUNDARY + r"|$)"
    )
    requests = [
        clause
        for clause in re.split(CLAUSE_BOUNDARY, text)
        if EDIT_REQUEST.match(clause.strip())
        and not INQUIRY.search(clause)
        and not EDIT_NEGATIVE.search(clause)
    ]

    def remove(match):
        protected = re.findall(item, match.group("objects"))
        # 同一对象既要求修改又禁止修改时保留否定，不能把冲突当成授权。
        if any(name in clause for name in protected for clause in requests):
            return match.group()
        return ""

    return constraint.sub(remove, text)


def effective_request(request_text):
    inherited = re.fullmatch(r"([^\n]+)\n此前已授权的请求：(.+)", request_text.strip(), re.S)
    if not inherited or not CONTINUE_QUESTION.fullmatch(inherited.group(1)):
        return request_text
    command, previous = inherited.groups()
    # “开始吧”解除前轮的临时讨论阶段；“继续”仍可能只是继续讨论，不能自动升级权限。
    if re.search(r"开始|动手", command):
        return TEMPORARY_DISCUSSION.sub("", previous)
    return previous


def is_discussion(request_text, *, reading=False):
    text = _without_protected_objects(command_text(request_text))
    return bool(
        DISCUSSION_ONLY.search(text)
        or READ_NEGATIVE.search(text)
        or (not reading and EDIT_NEGATIVE.search(text))
    )


def explicit_edit_request(request_text):
    text = command_text(request_text)
    if is_discussion(request_text):
        return False
    if re.search(r"[，,]\s*(?:需要|要|有)(?:哪些|什么|多少|多久|何时)", text):
        return False
    return any(
        EDIT_REQUEST.match(clause.strip())
        and not INQUIRY.search(clause)
        and not REQUIREMENT_REQUEST.match(clause.strip())
        for clause in re.split(r"[，,。！!\n；;]", text)
    )
