"""真实文件的轮次快照、历史不可变和修改块撤销。"""

import pytest

from app.modules.code_work.review import hunks, reverse_hunk
from tests.helpers.code_work import FILE, make_work


def test_turns_keep_their_own_before_and_after_after_later_edits(services, tmp_path):
    work, thread, original = make_work(services, tmp_path)
    initial = work.read(thread, FILE)["version"]
    first = work.write(thread, FILE, "class Example { int Value = 2; }", initial, run_id="first")
    snapshot = work.summary(thread, "first")
    work.write(thread, FILE, "class Example { int Value = 3; }", first["version"], run_id="second")
    assert work.summary(thread, "first") == snapshot
    assert "Value = 2" in work.diff(thread, FILE, "first")["after"]
    second = work.diff(thread, FILE, "second")
    assert "Value = 2" in second["before"] and "Value = 3" in second["after"]
    assert "Value = 3" in work.diff(thread, FILE)["after"]
    assert [item["run_id"] for item in work.status(thread)["history"]] == ["second", "first"]
    work.revert(thread, FILE, second["version"])
    assert work.summary(thread)["files"] == []
    assert work.summary(thread, "first") == snapshot
    assert "Value = 1" in (original / "Main/Example.cs").read_text(encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        work.diff(thread, "AKRS.ZX2200/Other.cs", "first")


def test_hunks_revert_only_selected_change_and_reject_stale_identifier():
    before = "".join(f"line {i}\n" for i in range(30))
    after = before.replace("line 2\n", "first change\n").replace("line 24\n", "second change\n")
    blocks = hunks(before, after)
    assert len(blocks) == 2
    restored = reverse_hunk(before, after, blocks[0]["id"])
    assert "line 2\n" in restored and "second change\n" in restored
    assert reverse_hunk(before, restored, hunks(before, restored)[0]["id"]) == before
    with pytest.raises(ValueError, match="修改块"):
        reverse_hunk(before, restored, blocks[0]["id"])


def test_revert_added_file_hunk_removes_file_and_old_turn_remains(services, tmp_path):
    work, thread, _ = make_work(services, tmp_path)
    path = "AKRS.ZX2200/Main/New.cs"
    created = work.write(thread, path, "class New {}\n", "", run_id="add")
    block = work.diff(thread, path)["hunks"][0]
    assert work.revert_hunk(thread, path, created["version"], block["id"])["files"] == []
    assert not (work.folder(thread) / "source" / path).exists()
    assert work.diff(thread, path, "add")["after"] == "class New {}\n"
