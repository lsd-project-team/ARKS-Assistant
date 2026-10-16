"""只记录真正放入提示或工具返回值的引用，预算外的候选不能冒充已带入。"""

import re

from app.agents.context.tokens import fit_text, text_tokens
from app.core.config import dump_json


def numbered_prompt_block(row, budget):
    header = dump_json({key: value for key, value in row.items() if key != "content"})
    block = header + "\n" + row["content"]
    if text_tokens(block) <= budget:
        return row, block
    # 为截断标记和元数据变化留空间，再按实际出现的行号缩小引用范围。
    content = fit_text(row["content"], max(0, budget - text_tokens(header) - 40))
    lines = re.findall(r"(?m)^(\d+):", content)
    if not lines or not content.partition(":")[2].strip():
        return None
    candidate = {
        **row,
        "content": content + " [摘录未完整带入]",
        "end_line": int(lines[-1]),
        "partial_excerpt": True,
    }
    candidate["citation"] = re.sub(
        r"#L\d+(?:-L?\d+)?$",
        f"#L{row['start_line']}-L{lines[-1]}",
        row["citation"],
    )
    header = dump_json({key: value for key, value in candidate.items() if key != "content"})
    block = header + "\n" + candidate["content"]
    return (candidate, block) if text_tokens(block) <= budget else None


def references(emit, kind, rows):
    for row in rows:
        emit(
            "knowledge_reference",
            {
                "kind": kind,
                **{key: row[key] for key in ("id", "title", "version", "citation")},
                **({"compatibility": row["compatibility"]} if "compatibility" in row else {}),
                **(
                    {"resolution_status": row["payload"].get("resolution_status")}
                    if "payload" in row
                    else {}
                ),
            },
        )
