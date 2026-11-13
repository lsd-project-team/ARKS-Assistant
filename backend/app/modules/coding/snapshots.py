"""项目快照：仓库放在 data 下，用 --git-dir/--work-tree 指向项目，项目里不出现 .git。"""

import os
import re
import shutil
import subprocess
from pathlib import Path

EXCLUDES = (
    "bin/",
    "obj/",
    "packages/",
    ".vs/",
    ".idea/",
    ".venv/",
    "venv/",
    "node_modules/",
    "dist/",
    "build/",
    "out/",
    "target/",
    "coverage/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".tox/",
    ".gradle/",
    ".next/",
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
        self.disabled = False
        self.reason = ""

    def available(self):
        return not self.disabled

    def _disable(self, reason):
        self.disabled = True
        self.reason = reason

    def _git(self, *arguments, timeout=GIT_TIMEOUT):
        if self.disabled:
            raise ValueError(self.reason or "快照仓库不可用")
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
        if self.disabled:
            return
        if self._ready and (self.repo / "HEAD").exists():
            return
        if shutil.which("git") is None:
            self._disable("未检测到 git，已禁用快照；文件读写仍可用")
            return
        try:
            if not (self.repo / "HEAD").exists():
                self.repo.mkdir(parents=True, exist_ok=True)
                result = _run(["git", "init", "--bare", "--quiet", str(self.repo)])
                if result.returncode != 0:
                    self._disable("初始化快照仓库失败，已禁用快照")
                    return
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
        except (OSError, ValueError) as error:
            self._disable(f"快照不可用：{error}")

    def _head(self):
        if self.disabled:
            return ""
        result = _run(
            ["git", f"--git-dir={self.repo}", "rev-parse", "--verify", "HEAD"],
            timeout=30,
        )
        return result.stdout.decode().strip() if result.returncode == 0 else ""

    def exists(self):
        return (self.repo / "HEAD").exists()

    def head(self):
        return self._head()

    def show(self, commit):
        """返回某个检查点自身引入的改动，而不是它到当前工作区的累计差异。"""
        _check_commit(commit)
        self.ensure()
        if self.disabled:
            return ""
        parent = _run(
            ["git", f"--git-dir={self.repo}", "rev-parse", "--verify", f"{commit}^"],
            timeout=30,
        )
        if parent.returncode == 0 and parent.stdout.strip():
            return self._git("diff", "--unified=3", f"{commit}^", commit)
        return self._git("show", "--unified=3", "--format=", commit)

    def path_in(self, commit, path):
        if self.disabled:
            return False
        result = _run(
            ["git", f"--git-dir={self.repo}", "cat-file", "-e", f"{commit}:{path}"],
            timeout=30,
        )
        return result.returncode == 0

    def checkout_paths(self, commit, paths):
        normalized = [path.replace("\\", "/") for path in paths]
        self._git("checkout", commit, "--", *normalized)
        return normalized

    def has_changes(self):
        if self.disabled:
            return False
        if not (self.repo / "HEAD").exists():
            return True
        return bool(self._git("status", "--porcelain").strip())

    def checkpoint(self, label):
        self.ensure()
        if self.disabled:
            return ""
        if not self.has_changes():
            return self._head()
        self._git("add", "-A")
        self._git("commit", "--quiet", "-m", label or "checkpoint")
        return self._head()

    def log(self, limit=20):
        self.ensure()
        if self.disabled:
            return []
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
        if self.disabled:
            return []
        rows = []
        for line in self._git("status", "--porcelain").splitlines():
            code, path = line[:2], line[3:]
            rows.append({"code": code.strip(), "path": path})
        return rows

    def diff(self, base="", head="", paths=None):
        self.ensure()
        if self.disabled:
            return ""
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
        if self.disabled:
            raise ValueError("当前环境没有可用的快照仓库，无法回滚")
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

    def name_status(self, base, head=""):
        self.ensure()
        if self.disabled:
            return []
        _check_commit(base)
        arguments = ["diff", "--name-status", "-M", base]
        if head:
            _check_commit(head)
            arguments.append(head)
        rows = []
        for line in self._git(*arguments).splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0].startswith("R"):
                rows.append({"status": "R", "path": parts[2], "previous": parts[1]})
            elif len(parts) >= 2:
                rows.append({"status": parts[0][:1], "path": parts[-1]})
        return rows

    def numstat(self, base, head=""):
        self.ensure()
        if self.disabled:
            return {}
        _check_commit(base)
        arguments = ["diff", "--numstat", "-M", base]
        if head:
            _check_commit(head)
            arguments.append(head)
        rows = {}
        for line in self._git(*arguments).splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            added, deleted, path = parts[0], parts[1], parts[-1]
            rows[path] = {
                "additions": None if added == "-" else int(added),
                "deletions": None if deleted == "-" else int(deleted),
                "binary": added == "-",
            }
        return rows

    def changed_paths(self, base, head=""):
        if self.disabled:
            return []
        arguments = ["diff", "--name-only", base]
        if head:
            arguments.append(head)
        return [line for line in self._git(*arguments).splitlines() if line]


def _check_commit(commit):
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit or ""):
        raise ValueError("检查点标识无效")
