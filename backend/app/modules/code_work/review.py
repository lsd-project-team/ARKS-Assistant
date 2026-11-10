"""统一差异的可撤销修改块；块标识绑定当前两份文本。"""

from difflib import SequenceMatcher

from app.infrastructure.storage.files import digest


def hunks(before, after):
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    result = []
    for group in SequenceMatcher(None, old, new, autojunk=False).get_grouped_opcodes(3):
        a, b, c, d = group[0][1], group[-1][2], group[0][3], group[-1][4]
        identity = digest(repr((a, b, c, d, old[a:b], new[c:d])).encode())
        result.append(
            {
                "id": identity,
                "old_start": a + 1,
                "old_lines": b - a,
                "new_start": c + 1,
                "new_lines": d - c,
                "before": "".join(old[a:b]),
                "after": "".join(new[c:d]),
            }
        )
    return result


def reverse_hunk(before, after, hunk_id):
    block = next((item for item in hunks(before, after) if item["id"] == hunk_id), None)
    if not block:
        raise ValueError("修改块已变化，请刷新差异后重试")
    lines = after.splitlines(keepends=True)
    start = block["new_start"] - 1
    lines[start : start + block["new_lines"]] = block["before"].splitlines(keepends=True)
    return "".join(lines)
