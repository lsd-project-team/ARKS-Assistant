import io
import tarfile

import pytest

from app.infrastructure.execution.archives import replace_worktree, unpack_result, write_source
from app.infrastructure.execution.cli import ExecutionError
from app.infrastructure.execution.runner import checked_limits, create_arguments
from app.modules.code_changes.processes import VerificationTask


def archive(*members):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode="w") as output:
        for name, content, kind in members:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(content) if kind == tarfile.REGTYPE else 0
            if kind in {tarfile.SYMTYPE, tarfile.LNKTYPE}:
                info.linkname = "../outside.txt"
            output.addfile(info, io.BytesIO(content) if info.isfile() else None)
    result.seek(0)
    return result


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "C:/escape",
        "a\\escape",
        "NUL.txt",
        "file. ",
        "bad\nname",
        "bad\x1fname",
        "<bad>",
        'bad"name',
        "bad|name",
        "bad?name",
        "bad*name",
    ],
)
def test_result_paths_cannot_escape_or_use_windows_special_names(tmp_path, name):
    work = tmp_path / "work"
    work.mkdir()
    original = work / "original.txt"
    original.write_bytes(b"original")
    with pytest.raises(ExecutionError):
        replace_worktree(archive((name, b"bad", tarfile.REGTYPE)), work, 100)
    assert original.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [work]


@pytest.mark.parametrize(
    "kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE]
)
def test_result_special_members_are_rejected_before_replacing_work(tmp_path, kind):
    work = tmp_path / "work"
    work.mkdir()
    (work / "a").write_text("untouched")
    with pytest.raises(ExecutionError):
        replace_worktree(archive(("unsafe", b"", kind)), work, 100)
    assert (work / "a").read_text() == "untouched"


def test_atomic_result_replaces_changed_files_preserves_bytes_and_deletions(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "deleted").write_text("old")
    data = b"\xff\xfe\x00\r\n"
    replace_worktree(archive(("sub/result.bin", data, tarfile.REGTYPE)), work, len(data))
    assert (work / "sub/result.bin").read_bytes() == data
    assert not (work / "deleted").exists()
    assert list(tmp_path.iterdir()) == [work]


def test_result_size_boundary_and_duplicate_case_are_enforced(tmp_path):
    destination = tmp_path / "stage"
    destination.mkdir()
    with pytest.raises(ExecutionError, match="空间限制"):
        unpack_result(archive(("a", b"12345", tarfile.REGTYPE)), destination, 4)
    assert not (destination / "a").exists()
    with pytest.raises(ExecutionError, match="大小写冲突"):
        unpack_result(
            archive(("A", b"1", tarfile.REGTYPE), ("a", b"2", tarfile.REGTYPE)), destination, 4
        )


def test_source_transfers_binary_and_rejects_reserved_control_file(tmp_path):
    source = tmp_path / "work"
    source.mkdir()
    (source / "data").write_bytes(b"\x00\xff")
    target = tmp_path / "source.tar"
    assert write_source(source, target, 2) == 2
    with tarfile.open(target) as content:
        assert content.extractfile("data").read() == b"\x00\xff"
        assert content.getmember("data").uid == 0
    (source / ".arks-execution-result").write_text("fake")
    with pytest.raises(ExecutionError, match="保留路径"):
        write_source(source, target, 100)


def test_source_size_above_exact_limit_is_rejected(tmp_path):
    (tmp_path / "source").mkdir()
    (tmp_path / "source/a").write_bytes(b"12")
    with pytest.raises(ExecutionError, match="空间限制"):
        write_source(tmp_path / "source", tmp_path / "source.tar", 1)


@pytest.mark.parametrize("value", [0, -1, True, None, "2", float("nan")])
def test_invalid_resource_limits_rejected(value):
    with pytest.raises(ExecutionError):
        checked_limits({"cpus": value})


def test_linux_sandbox_arguments_have_no_host_mount_or_network():
    task = VerificationTask("project", "change", "verification")
    executor = {
        "kind": "container",
        "platform": "linux",
        "image": "sha256:" + "a" * 64,
        "owner_id": "b" * 64,
    }
    args = create_arguments(executor, task, ["python", "check.py"], 10, checked_limits({}))
    for expected in [
        "--pull=never",
        "--network=none",
        "--read-only",
        "--user=0:0",
        "--cap-drop=ALL",
        "--cap-add=SETUID",
        "--cap-add=SETGID",
        "--cap-add=KILL",
        "no-new-privileges=true",
        "--pids-limit",
    ]:
        assert expected in args
    assert not {"--mount", "--volume", "--privileged", "--env-file"}.intersection(args)
    assert args[-1] == executor["image"]
    executor["platform"] = "windows"
    args = create_arguments(executor, task, ["python", "check.py"], 10, checked_limits({}))
    assert "--isolation=hyperv" in args
    assert "--user=ContainerUser" in args
