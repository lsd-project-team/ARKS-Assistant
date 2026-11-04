"""从已保存文件计算差异和行数；摘要与详情使用同一份差异。"""

import difflib

from app.infrastructure.storage.files import digest, safe_path
from app.modules.code_work.files import editable_path
from app.modules.source_analysis.workspace import decode_source


def file_difference(folder, path):
    file = editable_path(folder / "source", path)
    original = safe_path(folder, "baseline/" + path)
    before = decode_source(original.read_bytes())[0] if original.is_file() else ""
    data = file.read_bytes()
    after = decode_source(data)[0]
    lines = list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="a/" + path,
            tofile="b/" + path,
            lineterm="",
        )
    )
    # 前两行是文件头；其后的 +++ 等内容行仍然属于真实新增行。
    return {
        "path": path,
        "before": before,
        "after": after,
        "diff": "\n".join(lines),
        "version": digest(data),
        "additions": sum(line.startswith("+") for line in lines[2:]),
        "deletions": sum(line.startswith("-") for line in lines[2:]),
    }


def change_summary(folder, state):
    files = []
    for path, item in sorted(state["changes"].items()):
        difference = file_difference(folder, path)
        if difference["version"] != item["version"]:
            raise ValueError("副本文件被外部修改，请先打开代码修改面板核对")
        files.append(
            {
                "path": path,
                "kind": item["kind"],
                "version": item["version"],
                "additions": difference["additions"],
                "deletions": difference["deletions"],
            }
        )
    return {
        "exists": True,
        "revision": state["revision"],
        "files": files,
        "additions": sum(file["additions"] for file in files),
        "deletions": sum(file["deletions"] for file in files),
    }
