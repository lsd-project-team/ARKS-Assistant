"""保留异常写回期间的外部修改，按已查看版本确认后重新预览。"""

import re
from pathlib import Path

from app.core.identifiers import now_iso
from app.infrastructure.storage.files import safe_path
from app.modules.code_work import history, transactions
from app.modules.code_work.files import read_json, save_json


def load(folder, recovery_id):
    if not re.fullmatch(r"([a-f0-9]{10}|[a-f0-9]{32})", recovery_id):
        raise ValueError("恢复记录标识无效")
    file = safe_path(folder, f"merges/{recovery_id}/transaction.json")
    journal = read_json(file)
    if journal.get("status") != "pending" or not journal.get("recovery_conflicts"):
        raise ValueError("此记录已恢复，请刷新后重试")
    return file, journal


def diff(folder, recovery_id, path):
    _, journal = load(folder, recovery_id)
    item = next((item for item in journal["recovery_conflicts"] if item["path"] == path), None)
    if item is None:
        raise ValueError("文件不属于当前恢复冲突")
    current = transactions.target_file(Path(journal["target"]), path)
    data = current.read_bytes() if current.is_file() else None
    return history.difference(
        path, history.content(folder, item["before"]), data, version=transactions.version(current)
    )


def resolve(folder, recovery_id, confirm_target, versions, actor):
    file, journal = load(folder, recovery_id)
    if confirm_target != journal["target"]:
        raise ValueError("确认的原工程目录与恢复记录不一致")
    expected = {item["path"]: item["version"] for item in journal["recovery_conflicts"]}
    if versions != expected or any(
        transactions.version(transactions.target_file(Path(journal["target"]), path)) != value
        for path, value in expected.items()
    ):
        raise ValueError("原工程内容已变化，请重新核对恢复差异")
    # 不再写原工程；其余文件和副本已自动恢复。保留人工内容，重新三方预览。
    journal.update(status="recovered_conflicts", resolved_at=now_iso(), resolved_by=actor)
    save_json(file, journal)
    transactions.mark_recovered(file.parent)
    state = read_json(folder / "state.json")
    for key in ("merge_plan_id", "merge_plan_revision", "merge_paths"):
        state.pop(key, None)
    save_json(folder / "state.json", state)
