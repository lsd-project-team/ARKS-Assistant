"""项目级编码工作区：文件、快照、命令、审批与设置。"""

import hashlib
import json
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from app.core.config import PROJECT_ROOT
from app.core.identifiers import now_iso
from app.infrastructure.images import MAX_IMAGE_BYTES, inspect
from app.modules.coding import diagnostics, files, ui_checks
from app.modules.coding.executor import Executor
from app.modules.coding.snapshots import Snapshots

DEFAULT_SETTINGS = {
    "approval_mode": "allowlist",
    "permission": "workspace-write",
    "timeout_seconds": 120,
    "build_command": "",
    "test_command": "",
    "enabled": False,
}
MODES = {"allowlist", "confirm", "full"}
PERMISSIONS = {"read-only", "workspace-write", "full-access"}
POLICY_BY_PERMISSION = {
    "read-only": "read-only",
    "workspace-write": "allowlist",
    "full-access": "full",
}
APPROVAL_MODE_BY_PERMISSION = {
    "read-only": "allowlist",
    "workspace-write": "allowlist",
    "full-access": "full",
}
PERMISSION_BY_APPROVAL_MODE = {
    "allowlist": "workspace-write",
    "confirm": "workspace-write",
    "full": "full-access",
}
READONLY_ROOT = (PROJECT_ROOT / "trunk").resolve()
APPROVAL_TIMEOUT = 300
SESSION_ALLOW_TTL = 4 * 60 * 60
SESSION_ALLOW_MAX = 50
LOCK_TIMEOUT = 960
OUTPUT_EVENT_CHARS = 1_500
OUTPUT_EVENT_INTERVAL = 0.4


class CodingWorkspace:
    def __init__(self, paths, repository):
        self.root = Path(paths.workspace)
        self.data = Path(paths.data)
        self.project_id = getattr(repository, "project_id", None) or repository.workspace_id
        self.settings_path = self.data / "coding" / "settings" / f"{self.project_id}.json"
        self.audit_path = self.data / "coding" / "audit" / f"{self.project_id}.jsonl"
        self.lock = threading.RLock()
        self.approvals = {}
        self.cancels = {}
        # 本会话放行：thread_id -> {完整命令: 到期 monotonic 时间}，只存内存，切换权限即清空。
        self.session_allow = {}
        self.snapshots = Snapshots(self.data, self.project_id, self.root)
        settings = self.load_settings()
        self.executor = Executor(
            self.root,
            self.data / "coding" / "logs" / self.project_id,
            settings["approval_mode"],
            POLICY_BY_PERMISSION[settings["permission"]],
        )

    # ---------- 锁 ----------
    @contextmanager
    def _locked(self):
        if not self.lock.acquire(timeout=LOCK_TIMEOUT):
            raise ValueError("另一个会话正在执行项目命令，请稍后重试")
        try:
            yield
        finally:
            self.lock.release()

    # ---------- 设置 ----------
    def load_settings(self):
        raw = {}
        if self.settings_path.exists():
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        value = {**DEFAULT_SETTINGS, **raw}
        value["permission"] = self._derive_permission(raw, value)
        return value

    def _derive_permission(self, raw, value):
        """旧配置没有 permission 时，从 approval_mode + 目录可写状态推导，避免破坏已有项目。"""
        permission = raw.get("permission")
        if permission in PERMISSIONS:
            return permission
        if value.get("approval_mode") == "full":
            return "full-access"
        if self._can_write_root(value):
            return "workspace-write"
        return "read-only"

    def _can_write_root(self, value):
        root = self.root.resolve()
        return not root.is_relative_to(READONLY_ROOT) or bool(value.get("enabled"))

    def permission(self):
        return self.load_settings()["permission"]

    def settings(self):
        value = self.load_settings()
        root = self.root.resolve()
        return {
            **value,
            "root": str(root),
            "writable": self.writable(),
            "readonly": root.is_relative_to(READONLY_ROOT),
            "environment": self.environment(),
        }

    def environment(self):
        settings = self.load_settings()
        try:
            detected = files.detect_project(self.root)
        except (OSError, ValueError):
            detected = {}
        return {
            "language": detected.get("language", ""),
            "build_command": settings["build_command"] or detected.get("build", ""),
            "test_command": settings["test_command"] or detected.get("test", ""),
            "detected": detected,
        }

    def save_settings(self, changes):
        value = self.load_settings()
        previous_permission = value["permission"]
        if "permission" in changes:
            if changes["permission"] not in PERMISSIONS:
                raise ValueError("权限必须是 read-only / workspace-write / full-access")
            value["permission"] = changes["permission"]
            value["approval_mode"] = APPROVAL_MODE_BY_PERMISSION[value["permission"]]
        if "approval_mode" in changes:
            if changes["approval_mode"] not in MODES:
                raise ValueError("审批档位必须是 allowlist / confirm / full")
            value["approval_mode"] = changes["approval_mode"]
            value["permission"] = PERMISSION_BY_APPROVAL_MODE[value["approval_mode"]]
        if "timeout_seconds" in changes:
            timeout = int(changes["timeout_seconds"])
            if not 10 <= timeout <= 900:
                raise ValueError("超时必须在 10~900 秒")
            value["timeout_seconds"] = timeout
        for key in ("build_command", "test_command"):
            if key in changes:
                value[key] = str(changes[key])[:500]
        if "enabled" in changes:
            value["enabled"] = bool(changes["enabled"])
        explicit_permission = "permission" in changes or "approval_mode" in changes
        if (
            "enabled" in changes
            and value["enabled"]
            and value["permission"] == "read-only"
            and not explicit_permission
        ):
            # 老流程是「勾选启用即可写」：只打开 enabled 时把推导出的只读档一并提升。
            value["permission"] = "workspace-write"
            value["approval_mode"] = "allowlist"
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.executor.mode = value["approval_mode"]
        self.executor.policy = POLICY_BY_PERMISSION[value["permission"]]
        if value["permission"] != previous_permission:
            self._cancel_pending_approvals()
            self.session_allow.clear()
            self._audit(
                "permission",
                f"{previous_permission} -> {value['permission']}",
                None,
            )
        return self.settings()

    def writable(self):
        """默认分析目录（trunk）及其子目录保持只读；权限为仅可查看时也不可写。"""
        settings = self.load_settings()
        if settings["permission"] == "read-only":
            return False
        return self._can_write_root(settings)

    def _require_writable(self):
        if not self.writable():
            if self.permission() == "read-only":
                raise ValueError(
                    "当前权限为『仅可查看』（只读），不能修改文件；需要写入请在聊天头部切换权限"
                )
            raise ValueError("当前是只读分析项目，请选择其他目录建项目，或显式启用该项目的编码")

    # ---------- 文件 ----------
    def list_files(self, path=".", depth=2):
        return files.list_tree(self.root, path, depth)

    def read_file(self, path, start_line=1, end_line=400):
        return files.read_text(self.root, path, start_line, end_line)

    def read_image(self, path):
        """读取项目内图片用于模型直接查看；只读操作，不要求项目可写。"""
        relative_path, data = files.read_binary(self.root, path, MAX_IMAGE_BYTES)
        image_format, width, height, frames = inspect(data)
        return {
            "path": relative_path,
            "data": data,
            "format": image_format,
            "width": width,
            "height": height,
            "frames": frames,
        }

    def is_empty(self):
        """判断项目里是否还没有源码/工程文件，用于识别“从零生成”任务。"""
        ignored = {".git", ".vs", "bin", "obj", "publish", "node_modules", "shots"}
        try:
            for path in self.root.rglob("*"):
                if not path.is_file() or any(part in ignored for part in path.parts):
                    continue
                if path.suffix.lower() in {".cs", ".csproj", ".sln", ".xaml", ".fs", ".vb"}:
                    return False
        except OSError:
            return False
        return True

    def verify(self, kind="build", timeout=None):
        """执行构建或测试并把诊断结构化；需要审批的命令不阻塞等待。"""
        if kind not in {"build", "test"}:
            raise ValueError("verify 只支持 build 或 test")
        settings, detected = self.load_settings(), self.environment()
        if kind == "build":
            command = (
                settings.get("build_command") or detected.get("build_command") or "dotnet build"
            )
            timeout = timeout or 300
        else:
            command = (
                settings.get("test_command")
                or self._test_command()
                or detected.get("test_command")
                or "dotnet test"
            )
            timeout = timeout or 600
        result = self.run_command(command, timeout=timeout, approved=False, wait=False)
        if result.get("approval_required"):
            return {
                "ok": False,
                "kind": kind,
                "command": command,
                "error": (
                    "该验证命令不在自动放行范围，未执行；"
                    "请先确认审批或改用白名单内的构建/测试命令"
                ),
                "approval": result.get("approval"),
            }
        output = result.get("output") or ""
        parsed = diagnostics.parse_diagnostics(output, result.get("exit_code") or 0)
        tests = (
            diagnostics.parse_tests(output, result.get("exit_code") or 0)
            if kind == "test"
            else None
        )
        ok = parsed["ok"] and (tests is None or tests["ok"])
        return {
            "ok": ok,
            "kind": kind,
            "command": command,
            "exit_code": result.get("exit_code"),
            "duration_ms": result.get("duration_ms"),
            "errors": parsed["errors"][:50],
            "warnings": parsed["warnings"][:50],
            "error_count": parsed["error_count"],
            "warning_count": parsed["warning_count"],
            "summary": parsed["summary"],
            "tests": tests,
            "log_tail": diagnostics.tail(output),
        }

    def check_ui(self, tabs=2, timeout=150):
        """运行 --screenshot，解析控件树并校验截图，供 Agent 自检界面。"""
        project = self._project_file()
        if project is None:
            raise ValueError("项目内找不到 .csproj，请先创建工程或使用 scaffold_winforms")
        shots, outputs, output, missing = [], [], "", []
        for index in range(max(1, min(int(tabs), 4))):
            relative = f"shots/ui_tab{index}.png"
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            result = self.run_command(
                f'dotnet run --project "{project.name}" -- --screenshot "{relative}" {index}',
                timeout=timeout,
                approved=False,
                wait=False,
            )
            if result.get("approval_required"):
                return {
                    "ok": False,
                    "error": "截图命令需要审批，未执行；且无法确认界面，请不要宣称界面已验证",
                    "approval": result.get("approval"),
                }
            console = result.get("output") or ""
            layout_file = self.root / f"{relative}.layout.txt"
            # 优先用应用写下的控件树；控制台输出也会打印同一份，不能重复计算。
            if layout_file.is_file():
                tab_output = layout_file.read_text(encoding="utf-8", errors="replace") + "\n"
            else:
                tab_output = console + "\n"
            outputs.append(tab_output)
            output += tab_output
            if target.is_file():
                shots.append(relative)
            else:
                missing.append(relative)
                output += f"[截图缺失] {relative}\n"
                # 第一张就没有截图说明 --screenshot 入口可能未实现，再试第二张只是浪费一轮超时。
                break
        report = ui_checks.evaluate_layout(
            ui_checks.parse_layout(output),
            [ui_checks.analyze_screenshot(self.root / shot) for shot in shots],
        )
        issues = list(report["issues"])
        for index, tab_output in enumerate(outputs):
            page_count = sum(
                1 for row in ui_checks.parse_layout(tab_output) if row["type"] == "TabPage"
            )
            if page_count != 2:
                issues.append(
                    f"第 {index + 1} 个标签页的页签数量应为 2，实际 {page_count}"
                    "（不要重复创建 TabPage，骨架已有参数设置/设备功能两页）"
                )
        if missing:
            issues.append(
                f"未生成截图：{', '.join(missing)}；"
                "应用需支持 --screenshot <png> <tab> 并打印控件 bounds"
            )
            crash = _runtime_error(output)
            if crash:
                issues.append(f"截图模式启动失败：{crash}")
        ok = not issues
        checkpoint = self._remember_ui_pass() if ok else ""
        return {
            "ok": ok,
            "project": project.name,
            "shots": shots,
            "issues": issues,
            "notes": report["notes"],
            "counts": report["counts"],
            "checkpoint": checkpoint,
            "last_pass": self._last_ui_pass(),
            "log_tail": diagnostics.tail(output),
        }

    def _ui_pass_file(self):
        return self.data / "coding" / "ui-pass" / f"{self.project_id}.json"

    def _last_ui_pass(self):
        path = self._ui_pass_file()
        if not path.is_file():
            return ""
        try:
            return str(json.loads(path.read_text(encoding="utf-8")).get("commit") or "")
        except (ValueError, OSError):
            return ""

    def _remember_ui_pass(self):
        """界面自检通过时保存一个检查点，供布局被改坏时回退。"""
        if not self.writable() or not self.snapshots.available():
            return ""
        try:
            commit = self.snapshots.checkpoint("ui-pass")
        except (OSError, ValueError):
            return ""
        if not commit:
            return ""
        path = self._ui_pass_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"commit": commit, "at": now_iso()}, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(commit)

    def recover_ui(self):
        """回到最近一次界面自检通过的状态并重新自检；没有存档时明确失败。"""
        commit = self._last_ui_pass()
        if not commit:
            return {"ok": False, "error": "没有可回退的界面通过状态"}
        if not self.snapshots.exists():
            return {"ok": False, "error": "项目还没有检查点，无法回退"}
        with self._locked():
            self._require_writable()
            self.snapshots.restore(commit)
        result = self.check_ui()
        return {
            **result,
            "recovered_from": commit,
            "ok": bool(result.get("ok")),
            "issues": [] if result.get("ok") else result.get("issues", []),
        }

    def _project_file(self):
        candidates = sorted(path for path in self.root.glob("*.csproj") if path.is_file())
        return candidates[0] if candidates else None

    def _test_command(self):
        """没配置测试命令时，优先运行 tests/ 下的控制台自测工程，其次回退到框架检测。"""
        candidates = (
            sorted((self.root / "tests").glob("**/*.csproj"))
            if (self.root / "tests").is_dir()
            else []
        )
        if candidates:
            relative = candidates[0].relative_to(self.root).as_posix()
            return f'dotnet run --project "{relative}"'
        return ""

    def scaffold(self, template="winforms", values=None, path="."):
        """把经验证的界面骨架写入空目录；已有源码的目录拒绝覆盖。"""
        with self._locked():
            self._require_writable()
            target = files.resolve(self.root, path)
            if not target.is_dir():
                raise ValueError("目标不是目录")
            template_dir = Path(__file__).resolve().parent / "templates" / template
            if not template_dir.is_dir():
                raise ValueError(f"未知模板：{template}")
            existing = [item.name for item in target.iterdir() if item.is_file()]
            if any(
                name.endswith((".cs", ".csproj", ".sln", ".xaml")) for name in existing
            ):
                raise ValueError("目录已有源码或工程文件，不能 scaffold；请直接修改现有工程")
            replacements = {
                "__NAMESPACE__": "Sp900App",
                "__ASSEMBLY__": "Sp900App",
                "__PRODUCT__": "SP900 点胶机上位机",
                "__VERSION__": "1.0.0",
                **(values or {}),
            }
            written = []
            for source in sorted(template_dir.iterdir()):
                if not source.is_file():
                    continue
                name = source.name[:-5] if source.name.endswith(".tmpl") else source.name
                destination = target / name
                if destination.exists():
                    raise ValueError(f"目标文件已存在：{name}")
                text = source.read_text(encoding="utf-8")
                for key, value in replacements.items():
                    text = text.replace(key, str(value))
                destination.write_text(text, encoding="utf-8", newline="\n")
                written.append(files.relative(self.root, destination))
            return {
                "ok": True,
                "template": template,
                "path": files.relative(self.root, target),
                "files": sorted(written),
            }

    def search_files(self, query, path=".", glob=""):
        return files.search_text(self.root, query, path, glob)

    def find_files(self, pattern, path=".", limit=100):
        return files.find_files(self.root, pattern, path, limit)

    def write_file(self, path, content, expected_hash=""):
        with self._locked():
            self._require_writable()
            self.snapshots.ensure()
            result = files.write_text(self.root, path, content, expected_hash)
            self._touch()
            return result

    def edit_file(self, path, edits, expected_hash=""):
        with self._locked():
            self._require_writable()
            self.snapshots.ensure()
            result = files.edit_text(self.root, path, edits, expected_hash)
            self._touch()
            return result

    def write_binary(self, path, content_base64, expected_hash=""):
        with self._locked():
            self._require_writable()
            self.snapshots.ensure()
            result = files.write_binary(self.root, path, content_base64, expected_hash)
            self._touch()
            return result

    def create_directory(self, path):
        with self._locked():
            self._require_writable()
            self.snapshots.ensure()
            result = files.create_directory(self.root, path)
            self._touch()
            return result

    def move_path(self, path, destination):
        with self._locked():
            self._require_writable()
            self.snapshots.checkpoint("before-move")
            result = files.move(self.root, path, destination)
            self._touch()
            return result

    def delete_path(self, path, recursive=False):
        with self._locked():
            self._require_writable()
            self.snapshots.checkpoint("before-delete")
            result = files.delete(self.root, path, recursive)
            self._touch()
            return result

    # ---------- 快照 ----------
    def begin_run(self, run_id):
        if not self.writable():
            return None
        with self._locked():
            return self.snapshots.checkpoint(f"run-start-{run_id[:8]}")

    def run_changes(self, base, *, limit=400_000):
        with self._locked():
            head = self.snapshots.checkpoint("run-end")
            files_changed = []
            stats = self.snapshots.numstat(base, head)
            for row in self.snapshots.name_status(base, head):
                path = row["path"]
                item = {
                    "path": path,
                    "status": {"A": "added", "D": "deleted", "R": "renamed"}.get(
                        row["status"], "modified"
                    ),
                    **stats.get(path, {"additions": None, "deletions": None, "binary": False}),
                }
                if row.get("previous"):
                    item["previous"] = row["previous"]
                files_changed.append(item)
            diff, truncated = "", False
            for item in files_changed:
                if item["binary"]:
                    continue
                chunk = self.snapshots.diff(base, head, [item["path"]])
                item["patch"] = chunk[:100_000]
                if len(chunk) > 100_000:
                    item["patch"] += "\n…（该文件 diff 过长，已截断）"
                if len(diff) + len(chunk) > limit:
                    diff += "\n…（diff 过长，已截断，请在编码面板查看完整内容）"
                    truncated = True
                    break
                diff += chunk
            return {
                "base": base,
                "head": head,
                "files": files_changed,
                "diff": diff,
                "truncated": truncated,
            }

    def checkpoint(self, label=""):
        with self._locked():
            self._require_writable()
            return {"commit": self.snapshots.checkpoint(label or f"run-{_stamp()}")}

    def checkpoints(self, limit=20):
        if not self.writable():
            return {"checkpoints": [], "changes": [], "readonly": True}
        if not self.snapshots.exists():
            return {
                "checkpoints": [],
                "changes": [],
                "readonly": False,
                "snapshot_unavailable": not self.snapshots.available(),
            }
        return {
            "checkpoints": self.snapshots.log(limit),
            "changes": self.snapshots.status(),
            "readonly": False,
        }

    def diff(self, base="", head="", paths=None, commit=""):
        if not self.snapshots.exists():
            return {"diff": ""}
        if commit:
            return {"diff": self.snapshots.show(commit)}
        return {"diff": self.snapshots.diff(base, head, paths)}

    def restore(self, commit, paths=None):
        with self._locked():
            self._require_writable()
            return self.snapshots.restore(commit, paths)

    def restore_run(self, base, files_changed, commit):
        """撤销某一轮：仅当该轮之后没有新的检查点时允许。"""
        with self._locked():
            self._require_writable()
            if self.snapshots.head() != commit:
                raise ValueError("该轮之后已有新的修改，请先在编码面板中手动回滚")
            self.snapshots.checkpoint("before-undo-run")
            restored = []
            for row in files_changed:
                path = row["path"]
                previous = row.get("previous")
                if previous and self.snapshots.path_in(base, previous):
                    self.snapshots.checkout_paths(base, [previous])
                    target = self.root / path
                    if target.is_file():
                        target.unlink()
                    restored.append(previous)
                    continue
                if self.snapshots.path_in(base, path):
                    self.snapshots.checkout_paths(base, [path])
                    restored.append(path)
                    continue
                target = self.root / path
                if target.is_file():
                    target.unlink()
                    restored.append(path)
                elif target.is_dir():
                    import shutil

                    shutil.rmtree(target, ignore_errors=True)
                    restored.append(path)
            self.snapshots.checkpoint("undo-run")
            return {"commit": base, "paths": restored}

    # ---------- 命令 ----------
    def run_command(
        self,
        command,
        cwd=".",
        timeout=None,
        approved=False,
        *,
        wait=True,
        emit=None,
        run_id="",
        thread_id="",
    ):
        command = (command or "").strip()
        if not command:
            raise ValueError("命令不能为空")
        # 破坏性命令与项目外路径写入在任何权限档位都直接拒绝，不进入审批。
        if self.executor.classify(command) == "dangerous":
            raise ValueError("该命令被识别为危险命令或试图访问项目外路径，任何权限下都不会执行")
        if self.permission() == "read-only":
            if not self.executor.readonly_allowed(command):
                raise ValueError(
                    "当前权限为『仅可查看』，不能执行会改动文件或系统状态的命令；"
                    "需要执行请在聊天头部切换权限"
                )
        else:
            self._require_writable()
        settings = self.load_settings()
        timeout = max(5, min(int(timeout or settings["timeout_seconds"]), 900))
        approval = None
        if (
            not approved
            and not self.executor.allowed(command)
            and not self._session_allowed(command, thread_id)
        ):
            approval = self.request_approval(
                command,
                cwd,
                timeout,
                kind="command",
                emit=emit,
                run_id=run_id,
                thread_id=thread_id,
                waiting=wait,
            )
            if not wait:
                return {"approval_required": True, "approval": _public(approval)}
            status = self._wait_for_approval(approval, run_id)
            if status != "approved":
                result = {
                    "ok": False,
                    "approved": False,
                    "approval_status": status,
                    "command": command,
                    "message": _approval_message(status),
                }
                self._finish_approval(approval, result, status)
                self.cancels.pop(run_id, None)
                return {**result, "approval": self.approval(approval["id"])}
        try:
            result = self._execute_command(command, cwd, timeout, run_id, thread_id, emit)
        except Exception as error:
            if approval is not None:
                self._finish_approval(approval, {"ok": False, "error": str(error)}, "failed")
            raise
        if approval is not None:
            self._finish_approval(approval, result, "approved")
            return {**result, "approval": self.approval(approval["id"])}
        return result

    def _execute_command(self, command, cwd, timeout, run_id, thread_id, emit):
        with self._locked():
            if self.writable():
                self.snapshots.ensure()
                # 命令可能通过 shell 删除或覆盖文件，执行前先把已有改动存档。
                if self.snapshots.has_changes():
                    self.snapshots.checkpoint("before-command")
            stream = self._output_stream(emit, command, run_id)
            cancel = self.cancels.setdefault(run_id, threading.Event()) if run_id else None
            try:
                result = self.executor.run(
                    command,
                    cwd,
                    timeout,
                    approved=True,
                    on_output=stream,
                    cancel=cancel,
                    run_id=run_id,
                )
            finally:
                if stream is not None:
                    stream.flush()
                if run_id:
                    self.cancels.pop(run_id, None)
            self._audit(
                "run",
                command,
                result.get("exit_code"),
                thread_id=thread_id,
                run_id=run_id,
                duration_ms=result.get("duration_ms"),
                output=result.get("output", ""),
            )
            return result

    def start_process(
        self,
        command,
        cwd=".",
        approved=False,
        *,
        wait=True,
        emit=None,
        run_id="",
        thread_id="",
    ):
        command = (command or "").strip()
        if not command:
            raise ValueError("命令不能为空")
        if self.executor.classify(command) == "dangerous":
            raise ValueError("该命令被识别为危险命令或试图访问项目外路径，任何权限下都不会执行")
        if self.permission() == "read-only":
            raise ValueError(
                "当前权限为『仅可查看』，不能启动后台进程；需要执行请在聊天头部切换权限"
            )
        self._require_writable()
        approval = None
        if (
            not approved
            and not self.executor.allowed(command)
            and not self._session_allowed(command, thread_id)
        ):
            approval = self.request_approval(
                command,
                cwd,
                120,
                kind="process",
                emit=emit,
                run_id=run_id,
                thread_id=thread_id,
                waiting=wait,
            )
            if not wait:
                return {"approval_required": True, "approval": _public(approval)}
            status = self._wait_for_approval(approval, run_id)
            if status != "approved":
                result = {
                    "ok": False,
                    "approved": False,
                    "approval_status": status,
                    "command": command,
                    "message": _approval_message(status),
                }
                self._finish_approval(approval, result, status)
                self.cancels.pop(run_id, None)
                return {**result, "approval": self.approval(approval["id"])}
        try:
            with self._locked():
                self.snapshots.ensure()
                if self.snapshots.has_changes():
                    self.snapshots.checkpoint("before-process")
                result = self.executor.start(
                    command, cwd, approved=True, run_id=run_id, thread_id=thread_id
                )
                self._audit("start", command, None, thread_id=thread_id, run_id=run_id)
        except Exception as error:
            if approval is not None:
                self._finish_approval(approval, {"ok": False, "error": str(error)}, "failed")
            raise
        if approval is not None:
            self._finish_approval(approval, result, "approved")
            return {**result, "approval": self.approval(approval["id"])}
        return result

    def read_process(self, job_id, lines=80):
        return self.executor.read(job_id, lines)

    def list_jobs(self, limit=30):
        return {"jobs": self.executor.list_jobs(limit)}

    def stop_process(self, job_id):
        return self.executor.stop(job_id)

    def cancel_run(self, run_id):
        event = self.cancels.get(run_id)
        if event is not None:
            event.set()
        self.executor.cancel(run_id)
        with self.lock:
            pending = [
                row
                for row in self.approvals.values()
                if row.get("run_id") == run_id and row["status"] == "pending"
            ]
            for row in pending:
                row["status"] = "cancelled"
        for row in pending:
            self._emit_approval(row)

    def cancel_all(self):
        for run_id in list(self.cancels):
            self.cancel_run(run_id)
        self.executor.stop_all()

    # ---------- 审批 ----------
    def request_approval(
        self,
        command,
        cwd=".",
        timeout=120,
        *,
        kind="command",
        emit=None,
        run_id="",
        thread_id="",
        waiting=False,
    ):
        approval_id = uuid.uuid4().hex[:12]
        row = {
            "id": approval_id,
            "kind": kind,
            "command": command,
            "cwd": cwd,
            "timeout": timeout,
            "status": "pending",
            "created_at": now_iso(),
            "finished_at": None,
            "result": None,
            "scope": None,
            "run_id": run_id,
            "thread_id": thread_id,
            "_event": threading.Event(),
            "_emit": emit,
            "_waiting": waiting,
        }
        with self.lock:
            self.approvals[approval_id] = row
            if len(self.approvals) > 200:
                finished = sorted(
                    (item for item in self.approvals.values() if item["status"] != "pending"),
                    key=lambda item: item["created_at"],
                )
                for item in finished[: len(self.approvals) - 200]:
                    self.approvals.pop(item["id"], None)
        self._emit_approval(row)
        return row

    def approval(self, approval_id):
        with self.lock:
            row = self.approvals.get(approval_id)
            if not row:
                raise FileNotFoundError("审批请求不存在或已过期")
            return _public(row)

    def list_approvals(self):
        with self.lock:
            return [_public(row) for row in self.approvals.values() if row["status"] == "pending"]

    def recent_approvals(self, limit=20):
        with self.lock:
            rows = sorted(
                self.approvals.values(), key=lambda item: item["created_at"], reverse=True
            )[: max(1, min(limit, 100))]
            return [_public(row) for row in rows]

    def decide_approval(self, approval_id, approved, scope="once"):
        if scope not in {"once", "session"}:
            raise ValueError("审批范围必须是 once 或 session")
        with self.lock:
            row = self.approvals.get(approval_id)
            if not row:
                raise FileNotFoundError("审批请求不存在或已过期")
            if row["status"] != "pending":
                raise ValueError("该请求已经处理")
            row["status"] = "approved" if approved else "rejected"
            # 没有对话线程时无法按会话放行，退回一次性授权。
            row["scope"] = (scope if row.get("thread_id") else "once") if approved else None
            waiting = bool(row.get("_waiting"))
            row["_event"].set()
        if approved and row.get("scope") == "session":
            self._remember_session(row["command"], row.get("thread_id", ""))
        if approved:
            self._audit(
                "approve",
                row["command"],
                None,
                thread_id=row.get("thread_id", ""),
                run_id=row.get("run_id", ""),
                scope=row.get("scope") or "once",
            )
        if waiting:
            # 等待中的工具线程会在收到结果后执行并回填。
            return self.approval(approval_id)
        if not approved:
            self._finish_approval(
                row,
                {"ok": False, "approved": False, "message": "用户拒绝了这条命令"},
                "rejected",
            )
            return self.approval(approval_id)
        result = self._approved_result(row)
        self._finish_approval(row, result, "approved")
        return self.approval(approval_id)

    def _cancel_pending_approvals(self):
        """切换权限后，已经无法按原权限执行的待确认请求要作废，避免批准了却执行不了。"""
        with self.lock:
            rows = [row for row in self.approvals.values() if row["status"] == "pending"]
            for row in rows:
                row["status"] = "cancelled"
                row["finished_at"] = now_iso()
        for row in rows:
            self._emit_approval(row)

    def _session_allowed(self, command, thread_id):
        if not thread_id:
            return False
        rows = self.session_allow.get(thread_id)
        if not rows:
            return False
        expiry = rows.get(command)
        if expiry is None:
            return False
        if expiry <= time.monotonic():
            rows.pop(command, None)
            return False
        return True

    def _remember_session(self, command, thread_id):
        if not thread_id:
            return
        rows = self.session_allow.setdefault(thread_id, {})
        if command not in rows and len(rows) >= SESSION_ALLOW_MAX:
            rows.pop(min(rows, key=rows.get), None)
        rows[command] = time.monotonic() + SESSION_ALLOW_TTL

    def _approved_result(self, row):
        try:
            if row["kind"] == "process":
                return self.start_process(
                    row["command"],
                    row["cwd"],
                    approved=True,
                    wait=False,
                    emit=row.get("_emit"),
                    run_id=row.get("run_id", ""),
                    thread_id=row.get("thread_id", ""),
                )
            return self.run_command(
                row["command"],
                row["cwd"],
                row["timeout"],
                approved=True,
                wait=False,
                emit=row.get("_emit"),
                run_id=row.get("run_id", ""),
                thread_id=row.get("thread_id", ""),
            )
        except Exception as error:  # 审批执行失败要回到界面，而不是静默丢失
            return {"ok": False, "error": str(error)}

    def _wait_for_approval(self, approval, run_id):
        deadline = time.monotonic() + APPROVAL_TIMEOUT
        cancel = self.cancels.setdefault(run_id, threading.Event()) if run_id else None
        while True:
            with self.lock:
                row = self.approvals.get(approval["id"], {})
                if row.get("status") != "pending":
                    return row.get("status", "expired")
            if cancel is not None and cancel.is_set():
                with self.lock:
                    row = self.approvals.get(approval["id"])
                    if row and row["status"] == "pending":
                        row["status"] = "cancelled"
                return "cancelled"
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                with self.lock:
                    row = self.approvals.get(approval["id"])
                    if row and row["status"] == "pending":
                        row["status"] = "expired"
                return "expired"
            with self.lock:
                row = self.approvals.get(approval["id"])
                event = row["_event"] if row else None
            if event is not None:
                event.wait(min(0.5, remaining))
            else:
                return "expired"

    def _finish_approval(self, row, result, status):
        with self.lock:
            row["result"] = result
            row["status"] = status
            row["finished_at"] = now_iso()
        self._emit_approval(row)

    def _emit_approval(self, row):
        emit = row.get("_emit")
        if emit is None:
            return
        try:
            emit("coding_approval", _public(row))
        except Exception:
            pass

    def _output_stream(self, emit, command, run_id):
        if emit is None:
            return None
        state = {"buffer": [], "last": 0.0}

        def flush(force=False):
            text = "".join(state["buffer"])
            if not text:
                return
            now = time.monotonic()
            pending = len(text) < OUTPUT_EVENT_CHARS
            if not force and pending and now - state["last"] < OUTPUT_EVENT_INTERVAL:
                return
            state["buffer"] = []
            state["last"] = now
            try:
                emit(
                    "coding_output",
                    {
                        "command": command,
                        "chunk": text[-8_000:],
                        "run_id": run_id,
                        "truncated": len(text) > 8_000,
                    },
                )
            except Exception:
                pass

        def receive(text):
            state["buffer"].append(text)
            flush()

        receive.flush = lambda: flush(True)
        return receive

    # ---------- 审计 ----------
    def list_audit(self, limit=50):
        if not self.audit_path.exists():
            return []
        rows = []
        for line in self.audit_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        return rows[::-1][: max(1, min(limit, 500))]

    # ---------- 辅助 ----------
    def _touch(self):
        stamps = self.data / "coding" / "activity"
        stamps.mkdir(parents=True, exist_ok=True)
        (stamps / f"{self.project_id}.json").write_text(
            json.dumps({"updated_at": now_iso(), "root": str(self.root)}), encoding="utf-8"
        )

    def _audit(
        self,
        action,
        command,
        exit_code,
        *,
        thread_id="",
        run_id="",
        duration_ms=None,
        output="",
        scope="",
    ):
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "at": now_iso(),
            "project": self.project_id,
            "action": action,
            "command": command,
            "exit_code": exit_code,
            "mode": self.load_settings()["approval_mode"],
            "permission": self.permission(),
            "thread_id": thread_id,
            "run_id": run_id,
            "scope": scope,
            "duration_ms": duration_ms,
            "output_digest": hashlib.sha256(output.encode("utf-8")).hexdigest() if output else "",
        }
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def _public(row):
    return {key: value for key, value in row.items() if not key.startswith("_")}


def _approval_message(status):
    if status == "rejected":
        return "用户拒绝了这条命令，不要重试；需要时先说明原因再询问。"
    if status == "cancelled":
        return "本轮已被用户停止，命令没有执行。"
    return "等待用户确认超时，命令没有执行；请说明需要确认的命令，不要反复重试。"


def _stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _runtime_error(output):
    """从截图运行的输出里提取未处理异常，供 check_ui 直接告诉模型。"""
    for line in reversed((output or "").splitlines()):
        text = line.strip()
        if "Unhandled exception" in text or ("Exception" in text and "System." in text):
            return text[:300]
    return ""
