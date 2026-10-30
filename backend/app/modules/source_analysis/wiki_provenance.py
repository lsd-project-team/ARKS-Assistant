"""记录 Wiki 与本地仓库版本，无法取得远端索引版本时明确为未知。"""

import re
import subprocess


def local_revision(workspace):
    def git(*args):
        result = subprocess.run(
            ["git", "-C", str(workspace.root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    try:
        from pathlib import Path

        root = git("rev-parse", "--show-toplevel")
        if not root or Path(root).resolve() != workspace.root:
            return {
                "commit": None,
                "dirty": None,
                "reason": "源码目录没有独立 Git 提交，当前版本以每个文件的 SHA256 为准",
            }
        return {
            "commit": git("rev-parse", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--", ".")),
        }
    except (OSError, subprocess.TimeoutExpired):
        return {"commit": None, "dirty": None}


def wiki_provenance(workspace, repo, result):
    local = local_revision(workspace)
    structured = result.get("structuredContent") or result.get("structured_content") or {}
    remote = None
    if isinstance(structured, dict):
        for name in ("indexed_commit", "commit_sha", "commit"):
            value = structured.get(name)
            if isinstance(value, str) and re.fullmatch(r"[a-fA-F0-9]{40}", value):
                remote = value.lower()
                break
    status = (
        "unknown"
        if not local["commit"] or not remote
        else "match"
        if local["commit"] == remote and not local["dirty"]
        else "different"
    )
    note = {
        "unknown": "Wiki 未提供可核对的索引提交；架构说明需用当前本地源码复核",
        "match": "提交一致；具体结论仍需读取本地源码核对",
        "different": "Wiki 与本地提交或工作区内容不同，以当前本地源码为准",
    }[status]
    return {
        "repo": repo,
        "local": local,
        "remote_indexed_commit": remote,
        "status": status,
        "note": note,
    }
