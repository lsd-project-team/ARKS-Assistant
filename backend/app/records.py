"""存储记录转换；原始 JSON 与接口字段有明确边界。"""

import json


def record_dict(record) -> dict:
    result = {column.name: getattr(record, column.name) for column in record.__table__.columns}
    for field in (
        "selections_json",
        "payload_json",
        "model_snapshot_json",
        "source_options_json",
        "project_snapshot_json",
        "source_folders_json",
    ):
        if field in result:
            result[field.removesuffix("_json")] = json.loads(result.pop(field))
    return result
