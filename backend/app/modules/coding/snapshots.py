"""项目快照：仓库放在 data 下，用 --git-dir/--work-tree 指向项目，项目里不出现 .git。"""

import os
import re
import subprocess
from pathlib import Path

EXCLUDES = (
    "bin/",
    "obj/",
    "packages/",
    ".vs/",
    "node_modules/",
    "dist/",
    "publish/",
    "*.user",
    "*.suo",
    "*.log",
    ".git/",
    ".svn/",
)
GIT_TIMEOUT = 120


def _run(arguments, cwd=None, timeout=GIT_TIMEOUT):
    result = subprocess.run(
        arguments,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    return result


class Snapshots:
    def __init__(self, data, project_id, root):
        self.repo = Path(data) / "coding" / "snapshots" / project_id / "repo"
        self.root = Path(root).resolve()
        self._ready = False

    def _git(self, *arguments, timeout=GIT_TIMEOUT):
        result = _run(
            [
                "git",
                f"--git-dir={self.repo}",
                f"--work-tree={self.root}",
                *arguments,
            ],
            timeout=timeout,
        )
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", "replace").strip()
            raise ValueError(f"快照命令失败：{message or arguments[0]}")
        return result.stdout.decode("utf-8", "replace")

    def ensure(self):
        if self._ready and (self.repo / "HEAD").exists():
            return
        if not (self.repo / "HEAD").exists():
            self.repo.mkdir(parents=True, exist_ok=True)
            result = _run(["git", "init", "--bare", "--quiet", str(self.repo)])
            if result.returncode != 0:
                raise ValueError("初始化快照仓库失败，请确认已安装 git")
            (self.repo / "info").mkdir(parents=True, exist_ok=True)
            (self.repo / "info" / "exclude").write_text(
                "\n".join(EXCLUDES) + "\n", encoding="utf-8"
            )
            self._git("config", "user.name", "coding-agent")
            self._git("config", "user.email", "coding-agent@localhost")
            self._git("config", "core.autocrlf", "false")
        self._ready = True
        if not self._head():
            self._git("add", "-A")
            self._git("commit", "--quiet", "--allow-empty", "-m", "baseline")

    def _head(self):
        result = _run(
            ["git", f"--git-dir={self.repo}", "rev-parse", "--verify", "HEAD"],
            timeout=30,
        )
        return result.stdout.decode().strip() if result.returncode == 0 else ""

    def has_changes(self):
        if not (self.repo / "HEAD").exists():
            return True
        return bool(self._git("status", "--porcelain").strip())

    def checkpoint(self, label):
        self.ensure()
        if not self.has_changes():
            return self._head()
        self._git("add", "-A")
        self._git("commit", "--quiet", "-m", label or "checkpoint")
        return self._head()

    def log(self, limit=20):
        self.ensure()
        output = self._git(
            "log",
            f"--max-count={max(1, min(limit, 200))}",
            "--pretty=format:%H%x09%ad%x09%s",
            "--date=iso",
        )
        rows = []
        for line in output.splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                rows.append({"commit": parts[0], "date": parts[1], "label": parts[2]})
        return rows

    def status(self):
        self.ensure()
        rows = []
        for line in self._git("status", "--porcelain").splitlines():
            code, path = line[:2], line[3:]
            rows.append({"code": code.strip(), "path": path})
        return rows

    def diff(self, base="", head="", paths=None):
        self.ensure()
        arguments = ["diff", "--unified=3"]
        if base:
            _check_commit(base)
            arguments.append(base)
        if head:
            _check_commit(head)
            arguments.append(head)
        if paths:
            arguments.append("--")
            arguments.extend(paths)
        return self._git(*arguments)

    def restore(self, commit, paths=None):
        _check_commit(commit)
        self.ensure()
        self.checkpoint(f"before-restore-{commit[:8]}")
        if paths:
            normalized = [path.replace("\\", "/") for path in paths]
            self._git("checkout", commit, "--", *normalized)
            self.checkpoint(f"restore-{commit[:8]}")
            return {"commit": commit, "paths": normalized}
        for line in self._git("diff", "--name-status", commit, "HEAD").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].startswith("A"):
                target = self.root / parts[1]
                if target.is_file():
                    target.unlink()
                elif target.is_dir():
                    import shutil

                    shutil.rmtree(target, ignore_errors=True)
        self._git("checkout", commit, "--", ".")
        self.checkpoint(f"restore-{commit[:8]}")
        return {"commit": commit, "paths": []}

    def changed_paths(self, base, head=""):
        arguments = ["diff", "--name-only", base]
        if head:
            arguments.append(head)
        return [line for line in self._git(*arguments).splitlines() if line]


def _check_commit(commit):
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit or ""):
        raise ValueError("检查点标识无效")
