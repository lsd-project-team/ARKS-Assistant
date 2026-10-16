"""真实临时文件验证默认文件工具无法读取其他会话和修改副本。"""

import pytest
from deepagents.backends import FilesystemBackend

from app.agents.runtime.artifacts import thread_artifacts


def test_thread_artifacts_deny_other_thread_and_code_changes_preserving_legacy(services):
    scratch = services[0].scratch
    legacy = scratch / "threads" / "thread-a"
    legacy.mkdir(parents=True)
    (legacy / "summary.md").write_text("old summary", encoding="utf-8")
    secret = scratch / "code-changes" / "project-a" / "copy"
    secret.mkdir(parents=True)
    (secret / "private.txt").write_text("private-source-test", encoding="utf-8")
    root_a = thread_artifacts(scratch, "thread-a")
    root_b = thread_artifacts(scratch, "thread-b")
    first, second = FilesystemBackend(root_a), FilesystemBackend(root_b)
    result = first.read("/threads/thread-a/summary.md")
    assert result.error is None and result.file_data["content"] == "old summary"
    assert second.read("/threads/thread-a/summary.md").error
    assert first.read("/code-changes/project-a/copy/private.txt").error
    with pytest.raises(ValueError, match="traversal"):
        second.read("/../code-changes/project-a/copy/private.txt")
    assert (legacy / "summary.md").read_text(encoding="utf-8") == "old summary"
    assert thread_artifacts(scratch, "thread-a") == root_a
