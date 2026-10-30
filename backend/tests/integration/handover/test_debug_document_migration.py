"""整批发布必须原子化，不能覆盖并发修改、原图和历史引用。"""

import hashlib
import json
import runpy
from pathlib import Path

import pytest

from app.modules.handover.application.commands import Write
from app.modules.handover.infrastructure.persistence.repository import HandoverStore

SCRIPT = Path(__file__).resolve().parents[4] / "scripts/maintenance/curate_debug_documents.py"


@pytest.fixture
def prepared(services, tmp_path):
    functions = runpy.run_path(str(SCRIPT))
    store = HandoverStore(database=services[1])
    rows = [
        store.create(
            "debug_issue",
            f"经验{number}",
            {
                "problem": f"报警E90{number}",
                "solution": "更换密封圈",
                "recorded_by": "原作者",
                "original_text": "原始描述",
                "images": [{"id": "a" * 64, "name": "原图.png"}],
            },
            "原录入人",
        )
        for number in (1, 2)
    ]
    directory = tmp_path / "curation"
    functions["snapshot"](services[0].data / "app.sqlite3", directory)
    (directory / "drafts").mkdir()
    approved = {}
    for row in rows:
        raw = json.dumps(
            {
                "question": row["payload"]["question"] + "如何处理？",
                "answer": "可参考更换密封圈的处理方法。",
                "keywords": ["真空"],
            },
            ensure_ascii=False,
        )
        (directory / "drafts" / f"{row['id']}.json").write_text(raw, encoding="utf-8")
        approved[row["id"]] = hashlib.sha256(raw.encode()).hexdigest()
    (directory / "reviewed.json").write_text(json.dumps(approved), encoding="utf-8")
    return functions, store, rows, directory, services[0].data / "app.sqlite3"


def test_publish_keeps_metadata_old_versions_and_backup(prepared):
    functions, store, rows, directory, database = prepared
    functions["apply_drafts"](database, directory)
    for before in rows:
        current = store.get(before["id"])
        assert current["version"] == 2
        assert current["payload"]["answer"] == "可参考更换密封圈的处理方法。"
        assert current["payload"]["metadata"] == before["payload"]["metadata"]
        assert store.get(before["id"], 1)["payload"] == before["payload"]
    assert (directory / "before.sqlite3").is_file()
    assert json.loads((directory / "applied.json").read_text(encoding="utf-8"))["updated"] == 2


def test_concurrent_edit_aborts_whole_batch(prepared):
    functions, store, rows, directory, database = prepared
    row = rows[1]
    store.update(
        row["id"],
        Write(
            kind="debug_issue",
            title=row["title"],
            version=1,
            payload={**row["payload"], "answer": "他人更新的答案。"},
            actor="同事",
        ),
    )
    with pytest.raises(ValueError, match="整理期间变化"):
        functions["apply_drafts"](database, directory)
    assert store.get(rows[0]["id"])["version"] == 1
    assert store.get(rows[1]["id"])["payload"]["answer"] == "他人更新的答案。"


def test_changed_unreviewed_draft_cannot_publish(prepared):
    functions, store, rows, directory, database = prepared
    path = directory / "drafts" / f"{rows[1]['id']}.json"
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="草稿在审阅后变化"):
        functions["apply_drafts"](database, directory)
    assert all(store.get(row["id"])["version"] == 1 for row in rows)
