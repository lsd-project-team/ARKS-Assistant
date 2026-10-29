"""六项业务内容投影；旧修订的排查与原因也必须能完整读取。"""

import re


def _normalized(value):
    return re.sub(r"[\s，。；：、,.;:]", "", value).casefold()


def _join(values):
    result = []
    for value in values:
        if value.strip() and not any(_normalized(value) in _normalized(part) for part in result):
            result.append(value)
    return "\n\n".join(result)


def knowledge_sections(payload):
    conditions = payload.get("conditions", "")
    scope = [conditions]
    for key, label in (
        ("device", "设备"),
        ("environment", "环境"),
        ("software_version", "软件版本"),
        ("module", "模块"),
    ):
        value = payload.get(key, "")
        if value and _normalized(value) not in _normalized(conditions):
            scope.append(f"{label}：{value}")
    notes = re.sub(
        r"(?m)^[ \t]*(?:来源编号|原始来源|本(?:次|包)提供文件|导入标识)"
        r"[ \t]*[：:][^\r\n]*(?:\r?\n|$)",
        "",
        payload.get("notes", ""),
    )
    notes = re.sub(r"\bEXP-\d{3}\b[ \t]*", "", notes).strip()
    cause = payload.get("cause", "")
    core = [
        payload.get(key, "")
        for key in ("conditions", "problem", "solution", "verification", "notes")
    ]

    def uncovered(value):
        return bool(value) and not any(_normalized(value) in _normalized(part) for part in core)

    return {
        "适用条件": _join(scope),
        "内容说明": _join(
            [
                payload.get("problem", ""),
                payload.get("investigation", "")
                if uncovered(payload.get("investigation", ""))
                else "",
                f"原因判断：{cause}" if uncovered(cause) else "",
            ]
        ),
        "处理方法": payload.get("solution", ""),
        "结果记录": payload.get("verification", ""),
        "注意事项": notes,
    }
