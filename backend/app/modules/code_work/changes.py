"""从已保存文件计算差异和行数；摘要与详情使用同一份差异。"""

from app.infrastructure.storage.files import safe_path
from app.modules.code_work.files import editable_path
from app.modules.code_work.history import difference
from app.modules.code_work.review import hunks


def file_difference(folder, path, *, include_hunks=True):
    file = editable_path(folder / "source", path)
    original = safe_path(folder, "baseline/" + path)
    before = original.read_bytes() if original.is_file() else b""
    data = file.read_bytes()
    result = difference(path, before, data)
    if include_hunks:
        result["hunks"] = hunks(result["before"], result["after"])
    return result


def change_summary(folder, state):
    files = []
    for path, item in sorted(state["changes"].items()):
        difference = file_difference(folder, path, include_hunks=False)
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
