"""只读识别源码对应的仓库；不把应用父目录的 Git 仓库绑定给业务源码。"""

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


def repository_name(value, *, allow_bare=True):
    value = value.strip()
    if allow_bare and re.fullmatch(r"[\w.-]+/[\w.-]+", value, flags=re.ASCII):
        return value if all(part not in {".", ".."} for part in value.split("/")) else None
    if value.lower().startswith("git@github.com:"):
        path = value.split(":", 1)[1]
    else:
        try:
            url = urlsplit(value)
            if url.scheme not in {"https", "http", "ssh", "git"} or url.hostname != "github.com":
                return None
            path = url.path.lstrip("/")
        except ValueError:
            return None
    # 返回仓库名，不把远端 URL 中的凭据带回界面或日志。
    return repository_name(path.rstrip("/").removesuffix(".git"))


def git_repository(root):
    if not (Path(root) / ".git").exists():
        return None
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

    def read(*args):
        result = subprocess.run(
            ["git", "-C", root, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    try:
        top = read("rev-parse", "--show-toplevel")
        if not top or Path(top).resolve() != Path(root).resolve():
            return None
        output = read("config", "--local", "--no-includes", "--get-regexp", r"^remote\..*\.url$")
        remotes = dict(line.split(None, 1) for line in output.splitlines() if " " in line)
        origin = remotes.get("remote.origin.url")
        if origin:
            return repository_name(origin, allow_bare=False)
        candidates = {
            repo for value in remotes.values() if (repo := repository_name(value, allow_bare=False))
        }
        return candidates.pop() if len(candidates) == 1 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def associate_repository(roots, known):
    candidates, bases = set(), set()
    for root in roots:
        repo = git_repository(root)
        if repo:
            candidates.add(repo)
            bases.add("Git 远端")
            continue
        saved = {
            repo
            for item in known
            if item["source_root"] and Path(item["source_root"]).resolve() == Path(root).resolve()
            if (repo := repository_name(item["deepwiki_repo"]))
        }
        candidates.update(saved)
        if saved:
            bases.add("该目录已有的项目关联")
    if len(candidates) == 1:
        return {
            "deepwiki_repo": candidates.pop(),
            "status": "matched",
            "note": "已自动识别：" + "、".join(sorted(bases)),
        }
    if candidates:
        note = "这些目录对应多个仓库，请关闭自动关联后指定本项目的 DeepWiki 仓库。"
    elif roots:
        note = "未识别到对应仓库，可关闭自动关联后手动填写；源码目录仍会正常关联。"
    else:
        note = "选择源码目录后自动识别，也可以先创建空项目。"
    return {"deepwiki_repo": "", "status": "unknown", "note": note}
