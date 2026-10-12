"""供应商结构适配只移动已知业务字段，不改变事实、引文或字段值。"""

import json

from app.handover.schemas import PAYLOADS


def candidate_data(content):
    value = json.loads(content)
    if not isinstance(value, dict) or not isinstance(value.get("candidates"), list):
        return value
    for item in value["candidates"]:
        if not isinstance(item, dict) or not isinstance(item.get("payload"), dict):
            continue
        payload = item["payload"]
        kind = payload.get("target_kind")
        if not isinstance(kind, str) or kind not in PAYLOADS:
            continue
        proposed = payload.get("proposed", {})
        if not isinstance(proposed, dict):
            continue
        business_fields = set(PAYLOADS[kind].model_fields) - {"origin", "evidence", "notes"}
        for field in set(payload) & business_fields:
            if field in proposed and proposed[field] != payload[field]:
                # 同一个字段有两份不同内容时不能替模型选择，留给严格验证与修正。
                continue
            proposed[field] = payload.pop(field)
        payload["proposed"] = proposed
    return value
