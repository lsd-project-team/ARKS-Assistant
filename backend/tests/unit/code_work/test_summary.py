"""摘要从原始基线计算，与展示差异一致，不累计重复编辑次数。"""

import pytest

from app.modules.code_work.service import CodeWork
from tests.helpers.code_work import FILE, make_work


def test_summary_counts_baseline_diff_and_survives_reload_and_revert(services, tmp_path):
    work, thread, original = make_work(services, tmp_path)
    before = (original / "Main/Example.cs").read_bytes()
    assert work.summary(thread)["files"] == []
    first = work.write(
        thread,
        FILE,
        "int Value = 2;",
        work.read(thread, FILE)["version"],
        old_text="int Value = 1;",
    )
    work.write(thread, FILE, "int Value = 3;", first["version"], old_text="int Value = 2;")
    added = "AKRS.ZX2200/Main/Added.cs"
    work.write(thread, added, "// added\n\n+++content\n", "")
    summary = work.summary(thread)
    assert summary["revision"] == 3
    assert (summary["additions"], summary["deletions"]) == (4, 1)
    assert [(item["path"], item["additions"], item["deletions"]) for item in summary["files"]] == [
        (added, 3, 0),
        (FILE, 1, 1),
    ]
    assert "before" not in summary["files"][0] and "diff" not in summary["files"][0]
    assert work.diff(thread, FILE)["additions"] == 1
    assert CodeWork(work.paths, work.repository).summary(thread) == summary
    for file in summary["files"]:
        work.revert(thread, file["path"], file["version"])
    final = work.summary(thread)
    assert final["files"] == [] and final["additions"] == final["deletions"] == 0
    assert (original / "Main/Example.cs").read_bytes() == before


def test_empty_thread_summary_does_not_create_a_source_copy(services, tmp_path):
    work, _, _ = make_work(services, tmp_path)
    thread = work.repository.create_thread("尚无代码修改")["id"]
    assert work.summary(thread) == {
        "exists": False,
        "revision": 0,
        "files": [],
        "additions": 0,
        "deletions": 0,
    }
    assert not work.folder(thread).exists()
    with pytest.raises(FileNotFoundError):
        work.summary("missing")


def test_summary_rejects_unrecorded_file_changes(services, tmp_path):
    work, thread, _ = make_work(services, tmp_path)
    work.write(thread, FILE, "class Changed {}", work.read(thread, FILE)["version"])
    (work.folder(thread) / "source" / FILE).write_text("class External {}", encoding="utf-8")
    with pytest.raises(ValueError, match="外部修改"):
        work.summary(thread)
