"""源文件多文件写回事务；先持久化恢复材料，失败或重启恢复原内容。"""

import re
from pathlib import Path

from app.infrastructure.storage.files import digest, is_link, safe_path
from app.modules.code_work.files import atomic_bytes, main_project, read_json, save_json
from app.modules.code_work.history import blob, content


def target_file(root, relative):
    path = safe_path(root, relative)
    project = main_project(root)
    if not relative.startswith(project + "/") or not (
        path.suffix.lower() == ".cs" or relative == f"{project}/{project}.csproj"
    ):
        raise ValueError("合并只能写入已预览的主工程源码及编译项")
    return path


def version(path):
    return digest(path.read_bytes()) if path.is_file() else ""


def restore_files(folder, journal):
    root = Path(journal["target"])
    if not root.is_absolute() or not root.is_dir() or is_link(root):
        raise ValueError("合并恢复目标目录不可用")
    conflicts = []
    for item in reversed(journal["files"]):
        path = target_file(root, item["path"])
        current = version(path)
        if current == item["before"]:
            continue
        if current != item["after"]:
            conflicts.append({**item, "version": current})
            continue
        previous = content(folder, item["before"])
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            atomic_bytes(path, previous)
    return sorted(conflicts, key=lambda item: item["path"])


def begin(folder, directory, root, updates, expected, *, state, inputs):
    entries = []
    for relative, updated in sorted(updates.items()):
        path = target_file(root, relative)
        if version(path) != expected[relative]:
            raise ValueError("原工程已更新，请重新生成合并预览：" + relative)
        previous = path.read_bytes() if path.is_file() else None
        entries.append(
            {"path": relative, "before": blob(folder, previous), "after": blob(folder, updated)}
        )
    touched = set(state["changes"]) | set(updates)
    baseline_before, workspace_before = {}, {}
    for relative in touched:
        base = safe_path(folder, "baseline/" + relative)
        current = safe_path(folder / "source", relative)
        baseline_before[relative] = blob(folder, base.read_bytes() if base.is_file() else None)
        workspace_before[relative] = blob(
            folder, current.read_bytes() if current.is_file() else None
        )
    journal = {
        "status": "pending",
        "target": str(root),
        "files": entries,
        "state_before": state,
        "inputs_before": inputs,
        "baseline_before": baseline_before,
        "workspace_before": workspace_before,
    }
    save_json(directory / "transaction.json", journal)
    return journal


def write(folder, directory, journal):
    root = Path(journal["target"])
    for item in journal["files"]:
        path = target_file(root, item["path"])
        if version(path) != item["before"]:
            raise ValueError("写回期间原工程发生变化：" + item["path"])
        data = content(folder, item["after"])
        if data is None:
            path.unlink(missing_ok=True)
        else:
            atomic_bytes(path, data)


def recover(folder):
    pending = []
    for file in (folder / "merges").glob("*/transaction.json"):
        file = safe_path(folder, file.relative_to(folder).as_posix())
        journal = read_json(file)
        if journal.get("status") != "pending":
            continue
        conflicts = restore_files(folder, journal)
        if not journal.get("workspace_restored"):
            restore_workspace(folder, file, journal)
            journal["workspace_restored"] = True
        journal["recovery_conflicts"] = conflicts
        if conflicts:
            pending.append(
                {"id": file.parent.name, "target": journal["target"], "files": conflicts}
            )
        else:
            journal["status"] = "recovered"
            mark_recovered(file.parent)
        save_json(file, journal)
    return pending


def mark_recovered(directory):
    plan = directory / "plan.json"
    if plan.is_file():
        value = read_json(plan)
        value["status"] = "recovered"
        save_json(plan, value)


def restore_workspace(folder, file, journal):
    previous_name = journal.get("previous_source", "source.previous")
    if previous_name != "source.previous" and not re.fullmatch(
        r"(p-[a-f0-9]{10}|source\.merge-previous-[a-f0-9]{32})", previous_name
    ):
        raise ValueError("合并恢复目录标识无效")
    previous = safe_path(folder, previous_name)
    current = folder / "source"
    if previous.is_dir():
        # 两个目录都已核对在本副本内；保留未完成候选供诊断，不覆盖它。
        failed = file.parent / "failed"
        if current.exists():
            if failed.exists():
                raise ValueError("待恢复合并目录已存在，请核对 failed")
            assert current.resolve().parent == previous.resolve().parent == folder.resolve()
            current.rename(failed)
        previous.rename(current)
    else:
        for relative, digest_value in journal.get("workspace_before", {}).items():
            data = content(folder, digest_value)
            path = safe_path(current, relative)
            if data is None:
                path.unlink(missing_ok=True)
            else:
                atomic_bytes(path, data)
    for relative, digest_value in journal.get("baseline_before", {}).items():
        data = content(folder, digest_value)
        path = safe_path(folder, "baseline/" + relative)
        if data is None:
            path.unlink(missing_ok=True)
        else:
            atomic_bytes(path, data)
    save_json(folder / "inputs.json", journal["inputs_before"])
    save_json(folder / "state.json", journal["state_before"])
