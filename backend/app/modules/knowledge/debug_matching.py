"""明确条件用于筛选，不从相似症状推断设备、版本或已验证的解决方案。"""

import re

from app.modules.knowledge.search import alarm_codes

_STAGE = re.compile(r"(?<![a-z0-9])s[12](?![a-z0-9])", re.IGNORECASE)


def compact(value):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", str(value).casefold())


def explicit_filters(query, device="", software_version="", module="", conditions=""):
    version = re.search(
        r"(?i)(?:(?<![a-z0-9])v\s*|版本\s*[:：]?\s*)(\d+(?:\.\d+){1,3})(?!\d)", query
    )
    machine = re.search(
        r"(?i)(?<![a-z0-9])(?:zx\s*\d{3,5}(?:\s*(?:hs|ls))?|adv[\s-]*\d+(?![a-z0-9]))",
        query,
    )
    stage = _STAGE.search(query)
    return {
        "device": device or (machine[0] if machine else ""),
        "software_version": software_version or (version[1] if version else ""),
        "module": module or (stage[0] if stage else ""),
        "conditions": conditions or query,
        "alarm_codes": alarm_codes(query),
    }


def heating(text):
    cold = r"未加热|不加热|没加热|无加热|常温|冷态"
    negative = bool(re.search(cold, text))
    positive = bool(re.search(r"加热|热态|高温", re.sub(cold, "", text)))
    return "" if negative and positive else "cold" if negative else "heated" if positive else ""


def compatibility(row, filters):
    from app.modules.handover.domain.debug_knowledge import debug_metadata

    payload = {**row["payload"], **debug_metadata(row["payload"])}
    requested_codes = filters.get("alarm_codes", set())
    record_text = row["title"] + " " + " ".join(map(str, payload.values()))
    if requested_codes and not requested_codes.intersection(alarm_codes(record_text)):
        return {"status": "mismatch", "reason": "报警码与原问题不一致", "missing": []}
    missing, matched = [], []
    for field in ("device", "software_version", "module"):
        requested = compact(filters.get(field, ""))
        known = payload.get(field, "")
        if field == "device" and not known:
            match = re.search(
                r"(?i)(?<![a-z0-9])zx\s*\d{3,5}(?:\s*(?:hs|ls))?", payload.get("environment", "")
            )
            known = match[0] if match else ""
        actual = compact(known)
        if field == "module" and requested in {"s1", "s2"}:
            # “中转台取片”等功能名没有说明所属S区，属于缺少信息，不能当作明确冲突。
            actual = "".join(_STAGE.findall(str(known))).casefold()
        differs = requested not in actual and actual not in requested
        if field == "device" and requested.startswith("adv") and actual.startswith("adv"):
            differs = requested != actual
        if field == "software_version" and requested and actual:
            versions = set(re.findall(r"\d+(?:\.\d+){1,3}", str(known)))
            differs = (
                filters[field].lstrip("vV") not in versions if versions else requested != actual
            )
        if requested and actual and differs:
            return {"status": "mismatch", "reason": f"{field} 与问题明确条件不一致", "missing": []}
        if not requested or not actual:
            missing.append(field)
        else:
            matched.append(field)
    requested_heat = heating(filters.get("conditions", ""))
    recorded_heat = heating(payload.get("conditions", ""))
    if requested_heat and recorded_heat and requested_heat != recorded_heat:
        return {"status": "mismatch", "reason": "加热工况不同", "missing": []}
    if not requested_heat or not recorded_heat:
        missing.append("conditions")
    return {
        "status": "needs_confirmation" if missing else "matched",
        "matched": matched,
        "missing": missing,
        "reason": "需核对设备、版本、模块及工况，历史相似记录不代表当前已验证"
        if missing
        else "明确字段匹配，仍需现场验证",
    }
