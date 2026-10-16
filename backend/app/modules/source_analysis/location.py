"""仅在工作区内有唯一匹配时补齐遗漏的父目录，不猜测同名文件。"""


def resolve_source_path(workspace, path):
    normalized = path.removeprefix("/workspace/").replace("\\", "/")
    try:
        return workspace.read(normalized)["path"]
    except FileNotFoundError:
        pass
    # 越界、绝对路径和盘符继续交给原有权限校验，不能通过模糊匹配绕过。
    if normalized.startswith("/") or ":" in normalized or ".." in normalized.split("/"):
        return normalized
    candidates = workspace.find_files(normalized)
    matching = [
        row["path"]
        for row in candidates
        if row["path"].casefold().endswith("/" + normalized.casefold())
    ]
    return matching[0] if len(matching) == 1 and len(candidates) < 100 else normalized
