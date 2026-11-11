"""统一差异与行数统计；展示和摘要共用同一份计算。"""

import difflib

from app.infrastructure.storage.files import digest
from app.modules.workspace_work.paths import text_of


def difference(path, before, after, *, version=""):
    old = text_of(before) if before else ""
    new = text_of(after) if after else ""
    lines = list(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(), "a/" + path, "b/" + path, lineterm=""
        )
    )
    return {
        "path": path,
        "before": old,
        "after": new,
        "diff": "\n".join(lines),
        "version": version or (digest(after) if after else ""),
        "additions": sum(line.startswith("+") for line in lines[2:]),
        "deletions": sum(line.startswith("-") for line in lines[2:]),
    }
