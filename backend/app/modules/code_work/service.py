"""每个对话持有固定来源的可写副本，编辑与验证共享版本和锁。"""

import asyncio
import difflib
import io
import json
import shutil
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path
from threading import Event, RLock

from app.core.identifiers import now_iso
from app.infrastructure.storage.files import digest, safe_path
from app.modules.code_work.environment import CodeEnvironment
from app.modules.code_work.files import (
    PROJECT,
    atomic_bytes,
    code_manifest,
    editable_path,
    encode_text,
    input_manifest,
    read_json,
    save_json,
    snapshot,
)
from app.modules.source_analysis.workspace import Workspace, decode_source

_lock = RLock()
_jobs = {}
ACTIVE = {"queued", "building", "testing"}


@contextmanager
def backup_guard(data):
    """备份包含编辑结果，排除可重建的依赖和输出；复制期间不允许修改。"""
    with _lock:
        tasks, _ = _jobs.get(str(data.resolve()), ({}, {}))
        if tasks:
            raise ValueError("请等待代码验证完成或停止后导出备份")
        yield


class CodeWork:
    def __init__(self, paths, repository):
        self.paths, self.repository = paths, repository
        self.environment = CodeEnvironment(paths.data)
        # 项目切换/目录改绑可装配新 runtime；运行句柄仍以同一数据目录共享。
        with _lock:
            self.tasks, self.stops = _jobs.setdefault(str(paths.data.resolve()), ({}, {}))

    def folder(self, thread_id, *, include_deleted=False):
        self.repository.catalog.get(thread_id, include_deleted=include_deleted)
        parent = self.paths.scratch / "cw"
        parent.mkdir(exist_ok=True)
        folder = safe_path(parent, digest(thread_id.encode())[:12])
        if folder.is_dir():
            state = safe_path(folder, "state.json")
            if state.is_file() and read_json(state).get("thread_id") != thread_id:
                raise ValueError("代码副本标识冲突，请使用新对话")
        return folder

    def _load(self, folder):
        path = safe_path(folder, "state.json")
        state = read_json(path)
        job = state.get("verification")
        if job and job["status"] in ACTIVE and state["thread_id"] not in self.tasks:
            # 重启后不能凭旧 PID 宣称仍在运行，也不能终止可能已复用的进程号。
            job.update(status="interrupted", error="服务重启，验证未完成，请重新验证")
            save_json(path, state)
        return state

    def _state(self, thread_id):
        folder = self.folder(thread_id)
        if not folder.is_dir():
            raise ValueError("请先创建本对话的独立代码副本")
        return folder, self._load(folder)

    def exists(self, thread_id):
        try:
            return (self.folder(thread_id) / "state.json").is_file()
        except FileNotFoundError:
            return False

    def status(self, thread_id):
        with _lock:
            folder = self.folder(thread_id)
            configured = bool(self.environment.load().source_root)
            if not folder.is_dir():
                return {"exists": False, "configured": configured}
            state = self._load(folder)
            files = [
                {"path": path, "kind": item["kind"], "version": item["version"]}
                for path, item in sorted(state["changes"].items())
            ]
            job = state.get("verification")
            current = bool(job and job["revision"] == state["revision"] and self._prepared(folder))
            if current and job["status"] == "passed":
                current = digest(
                    str(sorted(code_manifest(folder / "source").items())).encode()
                ) == job.get("code_version")
            return {
                "exists": True,
                "configured": configured,
                **{key: state[key] for key in ("revision", "created_at", "source_version")},
                "files": files,
                "verification": state.get("verification"),
                "verification_current": current,
                "prepared": self._prepared(folder),
                "scope": (
                    "本机 Simulation 仿真；覆盖示例动作及流程，"
                    "不代表视觉、力控、标定或真实设备验收。"
                ),
            }

    def create(self, thread_id):
        with _lock:
            target = self.folder(thread_id)
            if target.exists():
                if not self._prepared(target):
                    self._hydrate(target)
                return self.status(thread_id)
            config = self.environment.load()
            if not config.source_root:
                raise ValueError("请先由管理员配置仿真源码目录")
            source = Path(config.source_root)
            if source.is_relative_to(self.paths.data) or self.paths.data.is_relative_to(source):
                raise ValueError("仿真源码不能与助手数据目录互相包含")
            if shutil.disk_usage(self.paths.scratch).free < 5_000_000_000:
                raise ValueError("创建代码副本需要至少 5 GB 可用空间")
            staging = target.with_name(target.name + ".creating-" + uuid.uuid4().hex[:8])
            staging.mkdir()
            try:
                work = staging / "source"
                work.mkdir()
                snapshot(source, work)
                manifest = code_manifest(work)
                if manifest != code_manifest(source):
                    raise ValueError("创建期间原源码发生变化，请重试以固定同一版本")
                locked = {}
                for path in [
                    work / PROJECT / "Program.cs",
                    work / PROJECT / f"{PROJECT}.csproj",
                    work / PROJECT / "App.config",
                    *(work / PROJECT / "Infrastructure/Simulation").glob("*.cs"),
                ]:
                    locked[path.relative_to(work).as_posix()] = digest(path.read_bytes())
                state = {
                    "thread_id": thread_id,
                    "revision": 0,
                    "created_at": now_iso(),
                    "source_version": digest(json.dumps(manifest, sort_keys=True).encode()),
                    "baseline": manifest,
                    "locked": locked,
                    "changes": {},
                    "verification": None,
                }
                save_json(staging / "state.json", state)
                save_json(staging / "inputs.json", input_manifest(work))
                atomic_bytes(staging / "ready", b"1")
                staging.rename(target)
            finally:
                if staging.exists():
                    # staging 是本方法创建的目录，递归清理前核对绝对范围。
                    if staging.resolve().parent == target.parent.resolve():
                        shutil.rmtree(staging)
            return self.status(thread_id)

    @staticmethod
    def _prepared(folder):
        return (folder / "ready").is_file()

    def _hydrate(self, folder):
        state = self._load(folder)
        previous = folder / "source.previous"
        if previous.exists():
            if not (folder / "source").exists():
                previous.rename(folder / "source")
            else:
                # 上次替换完成、写就绪标记前中断；确认编辑仍在后才清理旧树。
                for path, item in state["changes"].items():
                    if (
                        digest(editable_path(folder / "source", path).read_bytes())
                        != item["version"]
                    ):
                        raise ValueError("副本恢复尚未完成，请核对保留的 source.previous")
                if previous.resolve().parent == folder.resolve():
                    shutil.rmtree(previous)
        source = Path(self.environment.load().source_root)
        if not self.environment.load().source_root:
            raise ValueError("恢复备份后，请先由管理员重新配置同版本的仿真源码")
        if shutil.disk_usage(folder).free < 5_000_000_000:
            raise ValueError("恢复本机依赖需要至少 5 GB 可用空间")
        staging = folder / ("hydrating-" + uuid.uuid4().hex[:8])
        try:
            staging.mkdir()
            snapshot(source, staging)
            if input_manifest(staging) != read_json(folder / "inputs.json"):
                raise ValueError(
                    "当前仿真源码或依赖与副本来源版本不同，修改已保留；请选择同版本源码"
                )
            for path, item in state["changes"].items():
                data = editable_path(folder / "source", path).read_bytes()
                if digest(data) != item["version"]:
                    raise ValueError("恢复的修改文件指纹不符，不能重建验证副本")
                atomic_bytes(editable_path(staging, path), data)
            # 备份中的 source 只有已保存的 C#；先保留旧树，失败时可以恢复。
            (folder / "source").rename(previous)
            try:
                staging.rename(folder / "source")
            except OSError:
                previous.rename(folder / "source")
                raise
            atomic_bytes(folder / "ready", b"1")
            if previous.resolve().parent == folder.resolve():
                shutil.rmtree(previous)
        finally:
            if staging.exists() and staging.resolve().parent == folder.resolve():
                shutil.rmtree(staging)

    def read(self, thread_id, path, start_line=1, end_line=300):
        with _lock:
            folder, _ = self._state(thread_id)
            file = safe_path(folder / "source", path)
            if file.suffix.lower() != ".cs":
                raise ValueError("工作副本读取工具只读取 C# 文件")
            source = Workspace(folder / "source").read(
                file.relative_to(folder / "source").as_posix()
            )
            if start_line < 1 or end_line < start_line or end_line - start_line >= 500:
                raise ValueError("每次读取 1–500 行，行号从 1 开始")
            source["content"] = "\n".join(
                f"{index}: {line}"
                for index, line in enumerate(source["content"].splitlines(), 1)
                if start_line <= index <= end_line
            )
            return source

    def search(self, thread_id, query):
        with _lock:
            folder, _ = self._state(thread_id)
            return Workspace(folder / "source").search(query, "*.cs", diverse=True)

    def find(self, thread_id, query):
        if not query or len(query) > 300:
            raise ValueError("文件名长度必须在 1 到 300 之间")
        with _lock:
            folder, _ = self._state(thread_id)
            return {"files": Workspace(folder / "source").find_files(query)}

    def write(self, thread_id, path, content, version, *, old_text=None):
        with _lock:
            folder, state = self._state(thread_id)
            if state.get("verification") and state["verification"]["status"] in ACTIVE:
                raise ValueError("正在验证此版本，请等待或停止验证后再修改")
            file = editable_path(folder / "source", path)
            relative = file.relative_to(folder / "source").as_posix()
            data = file.read_bytes() if file.is_file() else b""
            current_version = digest(data) if file.is_file() else ""
            if version != current_version:
                raise ValueError("代码已更新，请重新读取文件版本后修改")
            text = decode_source(data)[0].replace("\r\n", "\n") if data else ""
            if old_text is not None:
                old_text = old_text.replace("\r\n", "\n")
                if not old_text or text.count(old_text) != 1:
                    raise ValueError("待替换原文必须在文件中唯一匹配；请扩大上下文后重试")
                content = text.replace(old_text, content.replace("\r\n", "\n"), 1)
            updated = encode_text(content, data)
            if updated == data and file.is_file():
                return {"path": relative, "version": current_version, "changed": False}
            baseline = safe_path(folder, "baseline/" + relative)
            if relative not in state["changes"] and relative in state["baseline"]:
                if digest(data) != state["baseline"][relative]:
                    raise ValueError("副本被外部修改，不能确定原始差异")
                atomic_bytes(baseline, data)
            existed = file.is_file()
            atomic_bytes(file, updated)
            kind = "modified" if relative in state["baseline"] else "added"
            if baseline.is_file() and baseline.read_bytes() == updated:
                state["changes"].pop(relative, None)
            else:
                state["changes"][relative] = {"kind": kind, "version": digest(updated)}
            state["revision"] += 1
            try:
                save_json(folder / "state.json", state)
            except OSError:
                if existed:
                    atomic_bytes(file, data)
                else:
                    file.unlink(missing_ok=True)
                raise
            return {
                "path": relative,
                "version": digest(updated),
                "changed": True,
                "revision": state["revision"],
            }

    def diff(self, thread_id, path):
        with _lock:
            folder, state = self._state(thread_id)
            file = editable_path(folder / "source", path)
            relative = file.relative_to(folder / "source").as_posix()
            if relative not in state["changes"]:
                raise FileNotFoundError("此文件没有修改")
            original = safe_path(folder, "baseline/" + relative)
            before = decode_source(original.read_bytes())[0] if original.is_file() else ""
            after = decode_source(file.read_bytes())[0]
            lines = difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile="a/" + relative,
                tofile="b/" + relative,
                lineterm="",
            )
            return {
                "path": relative,
                "before": before,
                "after": after,
                "diff": "\n".join(lines),
                "version": digest(file.read_bytes()),
            }

    def revert(self, thread_id, path, version):
        with _lock:
            folder, state = self._state(thread_id)
            if state.get("verification") and state["verification"]["status"] in ACTIVE:
                raise ValueError("请先停止验证")
            file = editable_path(folder / "source", path)
            relative = file.relative_to(folder / "source").as_posix()
            if relative not in state["changes"] or digest(file.read_bytes()) != version:
                raise ValueError("文件版本已变化，请刷新差异后重试")
            baseline = safe_path(folder, "baseline/" + relative)
            previous = file.read_bytes()
            if baseline.is_file():
                atomic_bytes(file, baseline.read_bytes())
            else:
                file.unlink()
            del state["changes"][relative]
            state["revision"] += 1
            try:
                save_json(folder / "state.json", state)
            except OSError:
                atomic_bytes(file, previous)
                raise
            return self.status(thread_id)

    def export(self, thread_id, revision=None):
        with _lock:
            folder, state = self._state(thread_id)
            if revision is not None and state["revision"] != revision:
                raise ValueError("代码已更新，请刷新后下载当前修改")
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                patches = []
                for path in sorted(state["changes"]):
                    data = editable_path(folder / "source", path).read_bytes()
                    if digest(data) != state["changes"][path]["version"]:
                        raise ValueError("副本文件被外部修改，请先核对代码版本")
                    archive.writestr(path, data)
                    patches.append(self.diff(thread_id, path)["diff"])
                archive.writestr("changes.diff", "\n\n".join(patches))
                archive.writestr(
                    "verification.json",
                    json.dumps(self.status(thread_id), ensure_ascii=False, indent=2),
                )
            return buffer.getvalue()

    async def verify(self, thread_id):
        from app.modules.code_work.runner import verify_workspace

        await asyncio.to_thread(self.create, thread_id)
        with _lock:
            folder, state = self._state(thread_id)
            if thread_id in self.tasks:
                raise ValueError("本对话已有验证正在执行")
            self.environment.compiler()
            job = {
                "id": uuid.uuid4().hex,
                "revision": state["revision"],
                "status": "queued",
                "started_at": now_iso(),
                "steps": [],
                "error": "",
            }
            state["verification"] = job
            save_json(folder / "state.json", state)
            stop = Event()
            self.stops[thread_id] = stop

            async def run():
                try:
                    await asyncio.to_thread(verify_workspace, self, thread_id, folder, state, stop)
                finally:
                    self.tasks.pop(thread_id, None)
                    self.stops.pop(thread_id, None)

            self.tasks[thread_id] = asyncio.create_task(run())
            return self.status(thread_id)

    def update_job(self, folder, state):
        with _lock:
            save_json(folder / "state.json", state)

    def cancel(self, thread_id):
        self._state(thread_id)
        if stop := self.stops.get(thread_id):
            stop.set()
        return self.status(thread_id)

    async def shutdown(self):
        for stop in self.stops.values():
            stop.set()
        if self.tasks:
            await asyncio.gather(*list(self.tasks.values()), return_exceptions=True)

    async def purge(self, thread_id):
        folder = self.folder(thread_id, include_deleted=True)
        if task := self.tasks.get(thread_id):
            self.stops[thread_id].set()
            await asyncio.shield(task)
        with _lock:
            if folder.exists() and folder.resolve().parent == (self.paths.scratch / "cw").resolve():
                shutil.rmtree(folder)
