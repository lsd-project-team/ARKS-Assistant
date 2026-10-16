"""临时源码、SQLite 与真实 Python 子进程验证隔离修改的高风险边界。"""

import asyncio
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modules.auth.middleware import install_authentication
from app.modules.auth.router import create_router as auth_router
from app.modules.auth.service import AuthService
from app.modules.code_changes import CodeChanges
from app.modules.code_changes.models import CodeChangeRecord, VerificationRecord
from app.modules.code_changes.router import create_router
from app.modules.source_analysis.collection import SourceCollection
from tests.helpers.accounts import sign_in


@pytest.fixture
def changes(services):
    paths, database, workspace, *_ = services
    service = CodeChanges(paths, database, workspace, "project-one")
    yield service
    for task in service._tasks.values():
        task.cancel.set()
    for task in service._tasks.values():
        if task.thread:
            task.thread.join(timeout=12)


def new_change(changes):
    return changes.create("修改入口", "验证隔离修改，不改原件")["id"]


def work_directory(changes, identifier):
    with changes.database.session() as session:
        row = session.scalar(select(CodeChangeRecord).where(CodeChangeRecord.id == identifier))
        return changes._work(row)


def configure(changes, program, timeout=5):
    return changes.save_profile("测试 Python", [sys.executable, "-c", program], timeout)["id"]


async def completed(changes, identifier, profile_id):
    result = changes.verify(identifier, profile_id)
    assert result["latest_verification"]["change_version"] == result["change_version"]
    result = await changes.wait(identifier, timeout_seconds=10)
    assert result["latest_verification"]["status"] != "running"
    return result


def test_copy_edit_conflicts_and_diff_preserve_original(changes):
    original = changes.workspace.root / "Program.cs"
    before_bytes = original.read_bytes()
    identifier = new_change(changes)
    source = changes.read_file(identifier, "Program.cs")
    result = changes.edit_file(identifier, "Program.cs", "Main", "Start", source["version"])
    assert result["status"] == "editing"
    assert result["files_changed"] == 1
    assert original.read_bytes() == before_bytes
    assert "Start" in changes.read_file(identifier, "Program.cs")["content"]
    with pytest.raises(ValueError, match="版本"):
        changes.edit_file(identifier, "Program.cs", "Start", "Wrong", source["version"])
    current = changes.read_file(identifier, "Program.cs")
    with pytest.raises(ValueError, match="上下文"):
        changes.edit_file(identifier, "Program.cs", "missing", "Wrong", current["version"])
    diff = changes.diff(identifier)
    assert diff["source_unchanged"] is True
    assert diff["conflicts"] == []
    assert diff["files"][0]["base_version"] == source["version"]
    assert diff["files"][0]["current_version"] == current["version"]
    assert "- static void Main()" in diff["diff"]
    assert "+ static void Start()" in diff["diff"]


def test_new_file_and_discard_only_remove_own_copy(changes):
    identifier = new_change(changes)
    missing = changes.read_file(identifier, "nested/new.py")
    assert missing["exists"] is False and missing["version"] == ""
    changes.edit_file(identifier, "nested/new.py", "", "print('new')\n", "")
    assert changes.diff(identifier)["files"][0]["status"] == "added"
    work = work_directory(changes, identifier)
    result = changes.discard(identifier)
    assert result["status"] == "discarded"
    assert not work.exists()
    assert not (changes.workspace.root / "nested").exists()
    assert (changes.workspace.root / "Program.cs").exists()
    with pytest.raises(ValueError, match="丢弃"):
        changes.read_file(identifier, "Program.cs")


@pytest.mark.parametrize(
    "encoding,prefix",
    [
        ("utf-8", b""),
        ("utf-8", b"\xef\xbb\xbf"),
        ("utf-16-le", b"\xff\xfe"),
        ("utf-16-be", b"\xfe\xff"),
        ("gb18030", b""),
    ],
)
def test_edit_preserves_encoding_bom_and_crlf(changes, encoding, prefix):
    original = changes.workspace.root / "编码.cs"
    before = prefix + "名称 old\r\n尾行\r\n".encode(encoding)
    original.write_bytes(before)
    identifier = new_change(changes)
    source = changes.read_file(identifier, "编码.cs")
    changes.edit_file(
        identifier, "编码.cs", source["content"], "名称 new\n尾行\n", source["version"]
    )
    assert (work_directory(changes, identifier) / "编码.cs").read_bytes() == (
        prefix + "名称 new\r\n尾行\r\n".encode(encoding)
    )
    assert original.read_bytes() == before


@pytest.mark.parametrize(
    "encoding,prefix", [("utf-8", b""), ("gb18030", b""), ("utf-16-be", b"\xfe\xff")]
)
def test_downloaded_patch_really_applies_without_trailing_newline(
    changes, tmp_path, encoding, prefix
):
    git = shutil.which("git")
    if not git:
        pytest.skip("此可应用性验证需要本机 Git")
    relative = "带 空格.cs"
    original = changes.workspace.root / relative
    original.write_bytes(prefix + "名称 old".encode(encoding))
    (changes.workspace.root / "remove.txt").write_text("delete me", encoding="utf-8")
    identifier = new_change(changes)
    source = changes.read_file(identifier, relative)
    changes.edit_file(identifier, relative, "old", "new", source["version"])
    changes.edit_file(identifier, "new-empty.txt", "", "", "")
    changes.edit_file(identifier, "new-text.txt", "", "added", "")
    (work_directory(changes, identifier) / "remove.txt").unlink()
    patch = changes.export(identifier).encode("utf-8")
    apply_to = tmp_path / "apply-to"
    shutil.copytree(changes.workspace.root, apply_to)
    result = subprocess.run(
        [git, "apply", "--check", "-"], input=patch, cwd=apply_to, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    result = subprocess.run(
        [git, "apply", "-"], input=patch, cwd=apply_to, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert (apply_to / relative).read_bytes() == prefix + "名称 new".encode(encoding)
    assert (apply_to / "new-empty.txt").read_bytes() == b""
    assert (apply_to / "new-text.txt").read_bytes() == b"added"
    assert not (apply_to / "remove.txt").exists()
    assert original.read_bytes() == prefix + "名称 old".encode(encoding)


def test_unsupported_copy_location_does_not_break_service_construction(changes):
    service = CodeChanges(
        changes.paths, changes.database, SimpleNamespace(root=changes.paths.data), "overlap"
    )
    assert service.list() == []
    with pytest.raises(ValueError, match="源码目录之外"):
        service.create("拒绝递归复制", "源码目录含数据目录时只拒绝创建副本")


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "/outside.txt",
        "C:/outside.txt",
        "a/../../x",
        "file:stream",
        ".git/config",
        "CON.txt",
        "a. /x",
    ],
)
def test_paths_cannot_escape_or_use_system_aliases(changes, path):
    identifier = new_change(changes)
    with pytest.raises(ValueError):
        changes.edit_file(identifier, path, "", "unsafe", "")
    assert changes.diff(identifier)["files"] == []


def test_original_drift_is_reported_and_edit_rejected(changes):
    identifier = new_change(changes)
    source = changes.read_file(identifier, "Program.cs")
    (changes.workspace.root / "Program.cs").write_text("external change", encoding="utf-8")
    diff = changes.diff(identifier)
    assert diff["source_unchanged"] is False
    assert diff["conflicts"] == ["Program.cs"]
    with pytest.raises(ValueError, match="基线冲突"):
        changes.edit_file(identifier, "Program.cs", source["content"], "new", source["version"])


def test_hard_link_in_copy_cannot_modify_original_or_be_discarded(changes):
    identifier = new_change(changes)
    work = work_directory(changes, identifier)
    target = work / "linked.cs"
    original = changes.workspace.root / "Program.cs"
    expected = original.read_bytes()
    os.link(original, target)
    with pytest.raises(ValueError, match="硬链接"):
        changes.read_file(identifier, "linked.cs")
    with pytest.raises(ValueError, match="硬链接"):
        changes.discard(identifier)
    assert original.read_bytes() == expected
    target.unlink()


def test_source_symlink_is_rejected_without_copying_target(changes, tmp_path):
    outside = tmp_path / "private"
    outside.mkdir()
    (outside / "secret.txt").write_text("private", encoding="utf-8")
    link = changes.workspace.root / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if os.name != "nt":
            pytest.skip(f"环境未提供符号链接权限：{error}")
        import _winapi

        _winapi.CreateJunction(str(outside), str(link))
    with pytest.raises(ValueError, match="链接"):
        new_change(changes)
    assert changes.list() == []
    assert (outside / "secret.txt").read_text(encoding="utf-8") == "private"


def test_project_scope_isolates_copies_profiles_and_logs(changes):
    identifier = new_change(changes)
    configure(changes, "print('one')")
    other = CodeChanges(changes.paths, changes.database, changes.workspace, "project-two")
    assert other.list() == [] and other.profiles() == []
    for operation in [other.get, other.diff, other.discard, other.log_path]:
        with pytest.raises(FileNotFoundError):
            operation(identifier)
    assert other.create("第二项目", "同源码目录使用不同项目空间")["id"] != identifier
    assert len(changes.list()) == 1


def test_multi_root_creation_refuses_to_silently_omit_sources(changes, tmp_path):
    attached = tmp_path / "attached"
    attached.mkdir()
    workspace = SourceCollection(
        changes.workspace.root, [{"source_id": "extra", "label": "附加", "root": str(attached)}]
    )
    service = CodeChanges(changes.paths, changes.database, workspace, "multi")
    with pytest.raises(ValueError, match="附加源码目录"):
        service.create("跨目录", "不应静默漏掉附加目录")


async def test_real_verification_uses_copy_and_invalidates_previous_pass(changes):
    identifier = new_change(changes)
    profile = configure(
        changes,
        "from pathlib import Path; assert Path('Program.cs').is_file(); "
        "print('verified-copy', flush=True)",
    )
    result = await completed(changes, identifier, profile)
    assert result["status"] == "passed"
    assert result["latest_verification"]["exit_code"] == 0
    assert "verified-copy" in result["latest_verification"]["output"]
    source = changes.read_file(identifier, "Program.cs")
    edited = changes.edit_file(identifier, "Program.cs", "Main", "Changed", source["version"])
    assert edited["status"] == "editing"
    assert edited["latest_verification"]["stale"] is True
    assert edited["latest_verification"]["change_version"] != edited["change_version"]
    assert "Main" in (changes.workspace.root / "Program.cs").read_text(encoding="utf-8")


async def test_list_invalidates_previous_pass_after_external_copy_edit(changes):
    identifier = new_change(changes)
    result = await completed(changes, identifier, configure(changes, "print('passed')"))
    previous_version = result["change_version"]
    (work_directory(changes, identifier) / "Program.cs").write_text(
        "external copy edit", encoding="utf-8"
    )
    listed = changes.list()[0]
    assert listed["status"] == "editing"
    assert listed["change_version"] != previous_version
    assert listed["latest_verification"]["stale"] is True
    assert changes.get(identifier)["status"] == "editing"
    assert changes.diff(identifier)["source_unchanged"] is True


@pytest.mark.parametrize(
    "program,seconds,status,exit_code",
    [
        ("import sys; print('assert failed', file=sys.stderr); sys.exit(7)", 5, "failed", 7),
        ("import time; print('started', flush=True); time.sleep(20)", 1, "timed_out", None),
    ],
)
async def test_real_failure_and_timeout_have_terminal_record(
    changes, program, seconds, status, exit_code
):
    identifier = new_change(changes)
    result = await completed(changes, identifier, configure(changes, program, seconds))
    verification = result["latest_verification"]
    assert result["status"] == "failed"
    assert verification["status"] == status
    assert verification["ended_at"] is not None
    if exit_code is not None:
        assert verification["exit_code"] == exit_code
        assert "assert failed" in verification["output"]
    else:
        assert verification["exit_code"] != 0
        assert "started" in verification["output"]
        assert "时间限制" in verification["error"]


async def test_cancel_stops_real_process_and_prevents_edit_while_running(changes):
    identifier = new_change(changes)
    profile = configure(changes, "import time; print('ready', flush=True); time.sleep(30)")
    changes.verify(identifier, profile)
    with pytest.raises(ValueError, match="验证中不能导出"):
        changes.export(identifier)
    with pytest.raises(ValueError, match="验证中"):
        changes.edit_file(identifier, "new.txt", "", "blocked", "")
    with pytest.raises(ValueError, match="验证中"):
        changes.verify(identifier, profile)
    ready = threading.Event()

    def wait_for_output():
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if "ready" in changes.get(identifier)["latest_verification"]["output"]:
                ready.set()
                return
            ready.wait(0.02)

    await asyncio.to_thread(wait_for_output)
    assert ready.is_set()
    changes.cancel(identifier)
    result = await changes.wait(identifier, timeout_seconds=10)
    assert result["latest_verification"]["status"] == "cancelled"
    assert result["latest_verification"]["exit_code"] != 0
    task = changes._tasks[result["latest_verification"]["id"]]
    assert task.process.poll() is not None


async def test_full_logs_survive_output_truncation_and_discard(changes):
    identifier = new_change(changes)
    result = await completed(
        changes, identifier, configure(changes, "print('HEAD-' + 'x' * 80000 + '-TAIL')")
    )
    verification = result["latest_verification"]
    assert verification["truncated"] is True
    assert len(verification["output"]) <= 64000
    assert "-TAIL" in verification["output"]
    full = changes.log_path(identifier, verification["id"])
    assert full.read_text().startswith("HEAD-") and full.stat().st_size > 80000
    changes.discard(identifier)
    assert changes.log_path(identifier, verification["id"]).is_file()


async def test_verifier_mutating_copy_cannot_claim_pass_for_old_version(changes):
    identifier = new_change(changes)
    result = await completed(
        changes,
        identifier,
        configure(
            changes,
            "from pathlib import Path; Path('Program.cs').write_text('modified by verifier')",
        ),
    )
    assert result["status"] == "failed"
    assert result["latest_verification"]["stale"] is True
    assert "副本发生改变" in result["error"]
    assert changes.diff(identifier)["source_unchanged"] is True


async def test_missing_configured_executable_records_environment_failure(changes, tmp_path):
    identifier = new_change(changes)
    executable = tmp_path / "removed-executable.exe"
    executable.write_bytes(b"configured but removed before execution")
    executable.chmod(0o700)
    profile = changes.save_profile("环境故障", [str(executable)], 2)["id"]
    executable.unlink()
    result = await completed(changes, identifier, profile)
    assert result["status"] == "failed"
    assert result["latest_verification"]["exit_code"] is None
    assert "验证进程执行失败" in result["error"]
    assert result["latest_verification"]["ended_at"] is not None


async def test_shutdown_cancels_verification_and_rejects_new_processes(changes):
    identifier = new_change(changes)
    profile = configure(changes, "import time; time.sleep(30)")
    changes.verify(identifier, profile)
    await changes.shutdown()
    result = changes.get(identifier)
    assert result["latest_verification"]["status"] == "cancelled"
    task = changes._tasks[result["latest_verification"]["id"]]
    assert task.finished.is_set()
    assert task.process is None or task.process.poll() is not None
    with pytest.raises(ValueError, match="关闭"):
        changes.verify(identifier, profile)


async def test_cancel_terminates_child_process_tree(changes):
    if os.name != "nt" and not hasattr(os, "pidfd_open"):
        pytest.skip("此环境没有可等待的子进程身份句柄")
    identifier = new_change(changes)
    profile = configure(
        changes,
        "import subprocess,sys,time; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        "print('child:'+str(child.pid),flush=True); time.sleep(30)",
    )
    changes.verify(identifier, profile)

    def child_pid():
        deadline = time.monotonic() + 5
        wait = threading.Event()
        while time.monotonic() < deadline:
            output = changes.get(identifier)["latest_verification"]["output"]
            if "child:" in output:
                return int(output.split("child:")[1].splitlines()[0])
            wait.wait(0.02)
        raise AssertionError("验证父进程未输出子进程身份")

    pid = await asyncio.to_thread(child_pid)
    if os.name == "nt":
        import _winapi

        handle = _winapi.OpenProcess(0x00100000 | 0x1000, False, pid)
    else:
        handle = os.pidfd_open(pid)
    try:
        changes.cancel(identifier)
        result = await changes.wait(identifier, timeout_seconds=10)
        assert result["latest_verification"]["status"] == "cancelled"
        if os.name == "nt":
            assert _winapi.WaitForSingleObject(handle, 3000) == 0
        else:
            import select

            assert select.select([handle], [], [], 3)[0] == [handle]
    finally:
        if os.name == "nt":
            _winapi.CloseHandle(handle)
        else:
            os.close(handle)


def assert_process_stopped(pid):
    if os.name == "nt":
        import _winapi

        try:
            handle = _winapi.OpenProcess(0x00100000 | 0x1000 | 0x0001, False, pid)
        except OSError as error:
            assert error.winerror == 87  # 已退出且进程对象已释放。
            return
        try:
            stopped = _winapi.WaitForSingleObject(handle, 3000) == 0
            if not stopped:
                _winapi.TerminateProcess(handle, 1)
                _winapi.WaitForSingleObject(handle, 3000)
            assert stopped, "验证已结束但后台子进程仍在运行"
        finally:
            _winapi.CloseHandle(handle)
    else:
        import select
        import signal

        try:
            handle = os.pidfd_open(pid)
        except ProcessLookupError:
            return
        try:
            stopped = bool(select.select([handle], [], [], 3)[0])
            if not stopped:
                os.kill(pid, signal.SIGKILL)
            assert stopped, "验证已结束但后台子进程仍在运行"
        finally:
            os.close(handle)


async def test_normal_parent_exit_cleans_background_descendant_before_pass(changes):
    if os.name != "nt" and not hasattr(os, "pidfd_open"):
        pytest.skip("此环境没有可等待的子进程身份句柄")
    identifier = new_change(changes)
    profile = configure(
        changes,
        "import subprocess,sys; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        "print('child:'+str(child.pid),flush=True)",
    )
    result = await completed(changes, identifier, profile)
    assert result["status"] == "passed"
    output = result["latest_verification"]["output"]
    pid = int(output.split("child:")[1].splitlines()[0])
    assert_process_stopped(pid)


@pytest.mark.skipif(os.name != "nt", reason="Windows JobObject 绑定失败保护")
async def test_job_assignment_failure_never_resumes_uncontained_process(changes, monkeypatch):
    def refused(_self, _pid):
        raise OSError("test-assignment-failed")

    monkeypatch.setattr(
        "app.modules.code_changes.processes.WindowsJob.assign_and_resume",
        refused,
    )
    identifier = new_change(changes)
    profile = configure(
        changes,
        "from pathlib import Path; Path('uncontained.txt').write_text('unsafe')",
    )
    result = await completed(changes, identifier, profile)
    assert result["status"] == "failed"
    assert result["latest_verification"]["exit_code"] is None
    assert "test-assignment-failed" in result["error"]
    assert not (work_directory(changes, identifier) / "uncontained.txt").exists()
    task = changes._tasks[result["latest_verification"]["id"]]
    assert task.process.poll() is not None


@pytest.mark.skipif(os.name != "nt", reason="Windows JobObject KILL_ON_JOB_CLOSE 崩溃保护")
def test_abrupt_job_owner_exit_terminates_its_verifier(tmp_path):
    program = (
        "import os,subprocess,sys; "
        "from app.modules.code_changes.windows_job import WindowsJob,CREATE_SUSPENDED; "
        "job=WindowsJob(); "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'], "
        "creationflags=CREATE_SUSPENDED|subprocess.CREATE_NO_WINDOW); "
        "job.assign_and_resume(child.pid); print(child.pid,flush=True); os._exit(0)"
    )
    owner = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    assert owner.returncode == 0, owner.stderr.decode(errors="replace")
    assert_process_stopped(int(owner.stdout.strip()))


def test_recover_marks_only_orphans_in_selected_project(changes):
    identifier = new_change(changes)
    with changes.database.session.begin() as session:
        change = session.get(CodeChangeRecord, identifier)
        verification = VerificationRecord(
            project_id=changes.project_id,
            change_id=identifier,
            profile_id="old",
            argv_json='["not-executed"]',
            timeout_seconds=1,
            change_version=change.change_version,
        )
        session.add(verification)
        session.flush()
        change.status, change.latest_verification_id = "verifying", verification.id
    other = CodeChanges(changes.paths, changes.database, changes.workspace, "another-project")
    assert other.recover() == 0
    assert changes.get(identifier)["status"] == "verifying"
    assert changes.recover() == 1
    result = changes.get(identifier)
    assert result["status"] == "interrupted"
    assert result["latest_verification"]["status"] == "interrupted"
    assert changes.recover() == 0


@pytest.mark.authentication
def test_http_requires_login_and_admin_profile_configuration(changes, services):
    paths, database, *_ = services
    auth = AuthService(database, paths)
    auth.initialize()
    app = FastAPI()
    app.state.auth = auth
    install_authentication(app, auth)
    app.include_router(auth_router(auth))
    repository = services[3]
    app.include_router(
        create_router(
            SimpleNamespace(
                runtime=SimpleNamespace(code_changes=changes),
                repository=repository,
                runs=SimpleNamespace(edit_lock=asyncio.Lock()),
            )
        )
    )

    @app.exception_handler(ValueError)
    async def invalid(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    with TestClient(app) as client:
        assert client.get("/api/code-changes").status_code == 401
        sign_in(client, "user")
        body = {
            "name": "Python",
            "argv": [sys.executable, "-c", "print('hello')"],
            "executor": {"kind": "trusted_host"},
            "baseline_required": False,
        }
        assert client.post("/api/code-changes/profiles", json=body).status_code == 403
        created = client.post("/api/code-changes", json={"title": "用户修改", "goal": "隔离测试"})
        assert created.status_code == 200
        assert created.json()["status"] == "ready"
        identifier = created.json()["id"]
        source = client.get(f"/api/code-changes/{identifier}/file", params={"path": "Program.cs"})
        assert source.status_code == 200
        assert isinstance(source.json()["version"], str)
        sign_in(client, "admin")
        configured = client.post("/api/code-changes/profiles", json=body)
        assert configured.status_code == 200
        assert configured.json()["argv"][0] == str(Path(sys.executable).resolve())
        assert client.get("/api/code-changes/profiles").json()["profiles"][0]["name"] == "Python"
        invalid = client.post(
            "/api/code-changes/profiles", json={**body, "argv": "python -c unsafe"}
        )
        assert invalid.status_code == 422

        slow = client.post(
            "/api/code-changes/profiles",
            json={
                "name": "可取消命令",
                "argv": [sys.executable, "-c", "import time;time.sleep(30)"],
                "executor": {"kind": "trusted_host"},
            },
        ).json()
        verifying = client.post(
            f"/api/code-changes/{identifier}/verify", json={"profile_id": slow["id"]}
        )
        assert verifying.status_code == 200

        def archived():
            raise ValueError("归档项目不能修改")

        repository.creation_guard = archived
        denied = client.post("/api/code-changes", json={"title": "拒绝", "goal": "归档只读"})
        assert denied.status_code == 409
        assert "归档" in denied.json()["detail"]
        assert client.post("/api/code-changes/profiles", json=body).status_code == 409
        assert client.post(f"/api/code-changes/{identifier}/discard").status_code == 409
        assert client.post(f"/api/code-changes/{identifier}/cancel").status_code == 200
        assert (
            client.get(
                f"/api/code-changes/{identifier}/file", params={"path": "Program.cs"}
            ).status_code
            == 200
        )
    result = asyncio.run(changes.wait(identifier, timeout_seconds=10))
    assert result["latest_verification"]["status"] == "cancelled"
