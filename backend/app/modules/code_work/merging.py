"""合并预览、独立候选验证和显式应用；聊天工具不提供写回入口。"""

import asyncio
import copy
import json
import os
import re
import shutil
import uuid
from pathlib import Path
from threading import Event
from types import SimpleNamespace

from app.core.identifiers import now_iso
from app.infrastructure.storage.files import digest, is_link, safe_path
from app.modules.code_work import history, transactions
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
from app.modules.code_work.merge_text import include_files, merge
from app.modules.source_analysis.workspace import decode_source


def origin_signature(root, paths):
    root = root.resolve()
    result = {}
    for relative in paths:
        parts = Path(relative).parts
        if Path(relative).is_absolute() or ".." in parts:
            raise ValueError("来源指纹路径无效")
        file = root / relative
        cursor = root
        for part in parts:
            cursor = cursor / part
            if cursor.exists() and (
                is_link(cursor) or cursor.is_file() and cursor.stat().st_nlink > 1
            ):
                raise ValueError("原工程出现链接，不能合并")
        if not file.resolve().is_relative_to(root):
            raise ValueError("来源指纹超出工程目录")
        result[relative] = digest(file.read_bytes()) if file.is_file() else ""
    return digest(
        json.dumps({"inputs": result, "code": code_manifest(root)}, sort_keys=True).encode()
    )


def baseline_data(folder, state, path):
    if path not in state["baseline"]:
        return None
    baseline = safe_path(folder, "baseline/" + path)
    data = (
        baseline.read_bytes()
        if baseline.is_file()
        else editable_path(folder / "source", path).read_bytes()
    )
    if digest(data) != state["baseline"][path]:
        raise ValueError("修改基线校验失败：" + path)
    return data


def locked_manifest(root):
    return {
        path.relative_to(root).as_posix(): digest(path.read_bytes())
        for path in [
            root / PROJECT / "Program.cs",
            root / PROJECT / f"{PROJECT}.csproj",
            root / PROJECT / "App.config",
            *(root / PROJECT / "Infrastructure/Simulation").glob("*.cs"),
        ]
        if path.is_file()
    }


def cleanup_candidates(folder, keep):
    for directory in (folder / "merges").iterdir():
        if directory.name == keep[:10] or not re.fullmatch(
            r"([a-f0-9]{10}|[a-f0-9]{32})", directory.name
        ):
            continue
        plan_file = directory / "plan.json"
        transaction_file = directory / "transaction.json"
        if transaction_file.exists() and read_json(transaction_file).get("status") == "pending":
            continue
        if plan_file.exists():
            previous = read_json(plan_file)
            if previous["status"] == "preview":
                previous["status"] = "superseded"
                save_json(plan_file, previous)
        for name in ("source", "checks", "test-host"):
            target = directory / name
            if (
                target.exists()
                and target.resolve().is_relative_to((folder / "merges").resolve())
                and target.resolve().parent == directory.resolve()
            ):
                try:
                    absolute = str(target.resolve())
                    shutil.rmtree("\\\\?\\" + absolute if os.name == "nt" else absolute)
                except OSError:
                    pass


class MergeWork:
    def __init__(self, work):
        self.work = work

    def load(self, thread_id, plan_id):
        folder, state = self.work._state(thread_id)
        if not re.fullmatch(r"[a-f0-9]{32}", plan_id):
            raise ValueError("合并标识无效")
        directory = safe_path(folder, "merges/" + plan_id[:10])
        if not directory.exists():
            directory = safe_path(folder, "merges/" + plan_id)
        plan = read_json(directory / "plan.json")
        if plan.get("id") != plan_id:
            raise ValueError("合并标识冲突，请重新生成预览")
        return folder, state, directory, plan

    def public(self, thread_id, plan_id):
        _, _, directory, plan = self.load(thread_id, plan_id)
        job = (
            read_json(directory / "state.json").get("verification")
            if (directory / "state.json").is_file()
            else None
        )
        return {
            key: plan[key]
            for key in (
                "id",
                "revision",
                "target",
                "created_at",
                "files",
                "conflicts",
                "rebase_conflicts",
                "source_changed",
                "status",
            )
        } | {
            "resolutions": plan.get("resolutions", {}),
            "verification": job,
            "can_apply": plan["status"] == "preview"
            and not plan["conflicts"]
            and not plan["rebase_conflicts"]
            and bool(job and job["status"] == "passed"),
        }

    def preview(self, thread_id, selected=None, resolutions=None):
        folder, state = self.work._state(thread_id)
        self.work._ensure_idle(thread_id, state)
        if thread_id in self.work.tasks or "merge:" + thread_id in self.work.tasks:
            raise ValueError("请等待或停止当前验证后生成合并预览")
        paths = sorted(state["changes"] if selected is None else set(selected))
        if not paths or len(paths) > 1000 or any(path not in state["changes"] for path in paths):
            raise ValueError("请选择当前待合入的文件，最多1000个")
        resolutions = resolutions or {}
        if any(path not in paths for path in resolutions):
            raise ValueError("冲突处理只能针对已选择文件")
        source_path = state.get("source_path") or self.work.environment.load().source_root
        root = Path(source_path)
        if not root.is_absolute() or not root.is_dir() or is_link(root):
            raise ValueError("原工程目录不可用，请核对固定来源")
        root = root.resolve()
        if root.is_relative_to(
            self.work.paths.data.resolve()
        ) or self.work.paths.data.resolve().is_relative_to(root):
            raise ValueError("原工程不能与助手数据目录互相包含")
        if shutil.disk_usage(folder).free < 5_000_000_000:
            raise ValueError("合并候选需要至少5 GB可用空间")
        plan_id = uuid.uuid4().hex
        directory = folder / "merges" / plan_id[:10]
        directory.mkdir(parents=True)
        candidate = directory / "source"
        snapshot(root, candidate)
        original_inputs = input_manifest(candidate)
        signature = origin_signature(root, original_inputs)
        # 快照过程中发生的修改必须使本次预览失败，不能混用不同版本。
        original_code = code_manifest(candidate)
        if original_code != code_manifest(root):
            raise ValueError("创建候选期间原工程发生变化，请重新预览")
        candidate_state = {
            "revision": state["revision"],
            "baseline": original_code,
            "changes": {},
            "requirements": copy.deepcopy(state.get("requirements", [])),
            "desktop_flow": state.get("desktop_flow", False),
            "verification": None,
        }
        rows, rebased, conflicts, rebase_conflicts = [], {}, [], []
        for path, item in sorted(state["changes"].items()):
            work_file = editable_path(folder / "source", path)
            ours = work_file.read_bytes()
            if digest(ours) != item["version"]:
                raise ValueError("副本被外部修改，请核对：" + path)
            base = baseline_data(folder, state, path)
            current_file = editable_path(candidate, path)
            theirs = current_file.read_bytes() if current_file.is_file() else None
            resolution = resolutions.get(path)
            status = "ready"
            try:
                if resolution:
                    choice = resolution["choice"]
                    merged = (
                        theirs
                        if choice == "source"
                        else ours
                        if choice == "workspace"
                        else encode_text(resolution["content"], theirs or ours)
                    )
                    status = "resolved"
                else:
                    merged = merge(base, theirs, ours)
            except ValueError:
                merged, status = None, "conflict"
            if path not in paths:
                if status == "conflict":
                    rebase_conflicts.append(path)
                else:
                    rebased[path] = history.blob(folder, merged)
                continue
            if status == "conflict":
                conflicts.append(path)
            result = history.difference(path, theirs, merged if status != "conflict" else ours)
            row = {
                "path": path,
                "kind": item["kind"],
                "status": status,
                "additions": result["additions"],
                "deletions": result["deletions"],
                "base": history.blob(folder, base),
                "source": history.blob(folder, theirs),
                "workspace": history.blob(folder, ours),
                "result": history.blob(folder, merged),
            }
            rows.append(row)
            if status != "conflict":
                if merged is None:
                    current_file.unlink(missing_ok=True)
                else:
                    atomic_bytes(current_file, merged)
                if merged != theirs:
                    candidate_state["changes"][path] = {
                        "kind": "modified" if theirs is not None else "added",
                        "version": history.blob(folder, merged),
                    }
        project_path = f"{PROJECT}/{PROJECT}.csproj"
        project_file = safe_path(candidate, project_path)
        project_before = project_file.read_bytes()
        additions = [
            row["path"]
            for row in rows
            if not row["source"] and row["status"] != "conflict" and row["result"]
        ]
        project_after = include_files(project_before, additions)
        if project_before != project_after:
            atomic_bytes(project_file, project_after)
            result = history.difference(project_path, project_before, project_after)
            rows.append(
                {
                    "path": project_path,
                    "kind": "project",
                    "status": "ready",
                    "additions": result["additions"],
                    "deletions": result["deletions"],
                    "base": history.blob(folder, project_before),
                    "source": history.blob(folder, project_before),
                    "workspace": history.blob(folder, project_after),
                    "result": history.blob(folder, project_after),
                }
            )
        candidate_state["locked"] = locked_manifest(candidate)
        plan = {
            "id": plan_id,
            "revision": state["revision"],
            "target": str(root),
            "created_at": now_iso(),
            "files": rows,
            "conflicts": conflicts,
            "rebase_conflicts": rebase_conflicts,
            "rebased": rebased,
            "original_inputs": list(original_inputs),
            "origin_signature": signature,
            "source_changed": original_code != state["baseline"],
            "status": "preview",
            "resolutions": resolutions,
        }
        save_json(directory / "state.json", candidate_state)
        save_json(directory / "plan.json", plan)
        atomic_bytes(directory / "ready", b"1")
        if origin_signature(root, original_inputs) != signature:
            raise ValueError("原工程在预览期间发生变化，请重新生成")
        cleanup_candidates(folder, plan_id)
        state["merge_plan_id"] = plan_id
        state["merge_plan_revision"] = state["revision"]
        state["merge_paths"] = paths
        save_json(folder / "state.json", state)
        return self.public(thread_id, plan_id)

    def diff(self, thread_id, plan_id, path):
        folder, _, _, plan = self.load(thread_id, plan_id)
        row = next((item for item in plan["files"] if item["path"] == path), None)
        if not row:
            raise FileNotFoundError("合并预览不包含此文件")
        result = history.difference(
            path,
            history.content(folder, row["source"]),
            history.content(
                folder, row["result"] if row["status"] != "conflict" else row["workspace"]
            ),
        )
        return {
            **result,
            "base": decode_source(history.content(folder, row["base"]) or b"")[0],
            "source": decode_source(history.content(folder, row["source"]) or b"")[0],
            "workspace": decode_source(history.content(folder, row["workspace"]) or b"")[0],
            "status": row["status"],
        }

    async def verify(self, thread_id, plan_id):
        from app.modules.code_work.runner import verify_workspace

        folder, state, directory, plan = self.load(thread_id, plan_id)
        self.check_current(folder, state, plan)
        if plan["conflicts"] or plan["rebase_conflicts"]:
            raise ValueError("请先处理冲突；未选择文件存在冲突时请将其纳入本次合并")
        key = "merge:" + thread_id
        if thread_id in self.work.tasks or key in self.work.tasks:
            raise ValueError("此对话已有验证正在执行")
        candidate = read_json(directory / "state.json")
        candidate["verification"] = {
            "id": uuid.uuid4().hex,
            "revision": plan["revision"],
            "status": "queued",
            "started_at": now_iso(),
            "steps": [],
            "error": "",
        }
        save_json(directory / "state.json", candidate)
        stop = Event()
        adapter = SimpleNamespace(
            environment=self.work.environment,
            build_root=folder,
            update_job=self.work.update_job,
        )

        async def run():
            try:
                await asyncio.to_thread(
                    verify_workspace, adapter, thread_id, directory, candidate, stop
                )
            finally:
                self.work.tasks.pop(key, None)
                self.work.stops.pop(key, None)

        self.work.stops[key] = stop
        self.work.tasks[key] = asyncio.create_task(run())
        return self.public(thread_id, plan_id)

    def check_current(self, folder, state, plan):
        if state.get("_recovery"):
            raise ValueError("请先处理合并恢复冲突")
        if plan["status"] != "preview" or state["revision"] != plan["revision"]:
            raise ValueError("副本或合并状态已变化，请重新生成预览")
        if (
            origin_signature(Path(plan["target"]), plan["original_inputs"])
            != plan["origin_signature"]
        ):
            raise ValueError("原工程已变化，请重新生成合并预览并验证")
        expected = {
            **state["baseline"],
            **{path: item["version"] for path, item in state["changes"].items()},
        }
        if code_manifest(folder / "source") != expected:
            raise ValueError("副本存在未记录的外部修改")

    def apply(self, thread_id, plan_id, actor):
        from app.modules.code_work.checks import validation_version

        folder, state, directory, plan = self.load(thread_id, plan_id)
        self.check_current(folder, state, plan)
        if thread_id in self.work.tasks or "merge:" + thread_id in self.work.tasks:
            raise ValueError("请等待验证完成")
        candidate_state = read_json(directory / "state.json")
        job = candidate_state.get("verification") or {}
        if job.get("validation_version") and job["validation_version"] != validation_version(
            candidate_state
        ):
            raise ValueError("合并需求或界面用例已变化，请重新验证")
        candidate = directory / "source"
        manifest = code_manifest(candidate)
        if (
            plan["conflicts"]
            or plan["rebase_conflicts"]
            or job.get("status") != "passed"
            or job.get("code_version") != digest(str(sorted(manifest.items())).encode())
        ):
            raise ValueError("合并结果尚未通过当前版本验证")
        for path, version in candidate_state["locked"].items():
            if digest(safe_path(candidate, path).read_bytes()) != version:
                raise ValueError("候选工程配置已变化，请重新验证")
        updates = {
            item["path"]: history.content(folder, item["result"])
            for item in plan["files"]
            if item["result"] != item["source"]
        }
        expected = {item["path"]: item["source"] for item in plan["files"]}
        inputs_before = read_json(folder / "inputs.json")
        journal = transactions.begin(
            folder,
            directory,
            Path(plan["target"]),
            updates,
            expected,
            state=state,
            inputs=inputs_before,
        )
        previous = folder / ("p-" + plan_id[:10])
        journal["previous_source"] = previous.name
        save_json(directory / "transaction.json", journal)
        if previous.exists():
            raise ValueError("上次工程切换尚未清理，请先恢复副本")
        try:
            transactions.write(folder, directory, journal)
            new_state = copy.deepcopy(state)
            new_state.update(
                baseline=manifest,
                locked=candidate_state["locked"],
                source_path=plan["target"],
                source_version=digest(json.dumps(manifest, sort_keys=True).encode()),
                changes={},
                verification=None,
                revision=state["revision"] + 1,
            )
            # 先记录实际合并基线，再恢复未选择的副本编辑；后者需要重新验证。
            next_inputs = input_manifest(candidate)
            for path, version in plan["rebased"].items():
                file = editable_path(candidate, path)
                baseline = file.read_bytes() if file.is_file() else None
                data = history.content(folder, version)
                if data == baseline:
                    continue
                if baseline is not None:
                    atomic_bytes(folder / "baseline" / path, baseline)
                if data is not None:
                    atomic_bytes(file, data)
                    new_state["changes"][path] = {
                        "kind": "modified" if baseline is not None else "added",
                        "version": version,
                    }
            record = {
                "id": plan_id,
                "status": "applied",
                "created_at": now_iso(),
                "actor": actor,
                "files": list(updates),
                "target": plan["target"],
                "verification": copy.deepcopy(job),
            }
            new_state.setdefault("applied", []).append(record)
            assert candidate.resolve().is_relative_to((folder / "merges").resolve())
            assert (
                previous.resolve().parent
                == (folder / "source").resolve().parent
                == folder.resolve()
            )
            (folder / "source").rename(previous)
            candidate.rename(folder / "source")
            save_json(folder / "inputs.json", next_inputs)
            save_json(folder / "state.json", new_state)
            plan["status"] = "applied"
            save_json(directory / "plan.json", plan)
            journal["status"] = "committed"
            save_json(directory / "transaction.json", journal)
        except Exception:
            transactions.recover(folder)
            raise
        if previous.resolve().parent == folder.resolve():
            try:
                shutil.rmtree(previous)
            except OSError:
                pass  # 已提交；保留的旧树由副本恢复逻辑核对后清理。
        return self.work.status(thread_id)

    def rollback(self, thread_id, plan_id, actor):
        folder, state, directory, plan = self.load(thread_id, plan_id)
        self.work._ensure_idle(thread_id, state)
        active = [item for item in state.get("applied", []) if item["status"] == "applied"]
        if not active or active[-1]["id"] != plan_id:
            raise ValueError("只能回退最近一次尚未回退的合并")
        if thread_id in self.work.tasks or "merge:" + thread_id in self.work.tasks:
            raise ValueError("请等待或停止验证后回退")
        journal = read_json(directory / "transaction.json")
        root = Path(plan["target"])
        for item in journal["files"]:
            if transactions.version(transactions.target_file(root, item["path"])) != item["after"]:
                raise ValueError("原工程已有后续修改，不能覆盖回退：" + item["path"])
        rollback_id = uuid.uuid4().hex
        rollback_dir = folder / "merges" / rollback_id[:10]
        rollback_dir.mkdir()
        updates = {
            item["path"]: history.content(folder, item["before"]) for item in journal["files"]
        }
        expected = {item["path"]: item["after"] for item in journal["files"]}
        undo = transactions.begin(
            folder,
            rollback_dir,
            root,
            updates,
            expected,
            state=state,
            inputs=read_json(folder / "inputs.json"),
        )
        try:
            transactions.write(folder, rollback_dir, undo)
            next_state = copy.deepcopy(state)
            next_inputs = read_json(folder / "inputs.json")
            for item in journal["files"]:
                path = item["path"]
                before = history.content(folder, item["before"])
                if path.endswith(".csproj"):
                    atomic_bytes(safe_path(folder / "source", path), before)
                    next_state["locked"][path] = item["before"]
                else:
                    current = editable_path(folder / "source", path)
                    if before is None:
                        next_state["baseline"].pop(path, None)
                    else:
                        next_state["baseline"][path] = item["before"]
                        atomic_bytes(folder / "baseline" / path, before)
                    if current.is_file() and transactions.version(current) != item["before"]:
                        next_state["changes"][path] = {
                            "kind": "modified" if before is not None else "added",
                            "version": transactions.version(current),
                        }
                    else:
                        next_state["changes"].pop(path, None)
                if before is None:
                    next_inputs.pop(path, None)
                else:
                    next_inputs[path] = item["before"]
            next_state["revision"] += 1
            next_state["verification"] = None
            next_state["source_version"] = digest(
                json.dumps(next_state["baseline"], sort_keys=True).encode()
            )
            record = next(item for item in next_state["applied"] if item["id"] == plan_id)
            record.update(status="rolled_back", rolled_back_at=now_iso(), rolled_back_by=actor)
            save_json(folder / "inputs.json", next_inputs)
            save_json(folder / "state.json", next_state)
            plan["status"] = "rolled_back"
            save_json(directory / "plan.json", plan)
            undo["status"] = "committed"
            save_json(rollback_dir / "transaction.json", undo)
        except Exception:
            transactions.recover(folder)
            raise
        return self.work.status(thread_id)
