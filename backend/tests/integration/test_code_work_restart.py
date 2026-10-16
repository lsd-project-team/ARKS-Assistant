"""独立端口和临时数据验证真实应用崩溃恢复，以及验证期间的原件漂移。"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from app.modules.code_changes import CodeChanges
from app.modules.code_changes.models import VerificationRecord

pytestmark = pytest.mark.authentication
BACKEND = Path(__file__).resolve().parents[2]

# 只替换阅读供应商边界；FastAPI、认证、迁移、SQLite、进程和启动恢复均真实运行。
SERVER_PROGRAM = r"""
import asyncio
import json
import sys
from pathlib import Path

import uvicorn

from app.agents.runtime import engine
from app.core.config import Paths
from app.bootstrap import create_app

data, source, port, phase, call_log = sys.argv[1:]

class TestReadingAnalyzer:
    def __init__(self, _settings):
        pass

    def validate(self):
        pass

    async def __call__(self, text, metadata):
        with Path(call_log).open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'phase': phase, 'path': metadata['path'],
                                     'chunk_index': metadata['chunk_index']}) + '\n')
        if phase == 'blocked' and metadata['chunk_index'] == 1:
            await asyncio.sleep(3600)
        return {'summary': 'Saved source chunk ' + metadata['path'],
                'unknowns': ['No external supplier is used in this test'],
                'references': [{key: metadata[key] for key in
                                ('path', 'source_version', 'start_line', 'end_line')}]}

engine.ModelReadingAnalyzer = TestReadingAnalyzer
app = create_app(Paths(Path(data), Path(source)))
uvicorn.run(app, host='127.0.0.1', port=int(port), log_level='warning', access_log=False)
"""


def wait_until(read, ready, *, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = read()
        if ready(result):
            return result
        time.sleep(0.025)
    raise AssertionError("临时应用未在期限内达到预期状态")


def api(client, method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    assert response.status_code in {200, 201}, (response.status_code, response.text)
    return response.json()


def login(client, data):
    accounts = json.loads((data / "auth.initial-accounts.json").read_text(encoding="utf-8"))
    admin = next(row for row in accounts if row["username"] == "admin")
    result = api(
        client,
        "POST",
        "/api/auth/login",
        json={
            "username": "admin",
            "password": admin["password"],
        },
    )
    client.headers["X-Arks-CSRF"] = result["csrf_token"]


class TemporaryApp:
    def __init__(self, temporary, phase):
        self.temporary, self.phase = temporary, phase
        self.process, self.output = None, None
        with socket.socket() as available:
            available.bind(("127.0.0.1", 0))
            self.port = available.getsockname()[1]
        assert self.port != 8765
        self.url = f"http://127.0.0.1:{self.port}"
        self.log = temporary / f"server-{phase}.log"

    def start(self):
        self.output = self.log.open("wb")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                SERVER_PROGRAM,
                str(self.temporary / "data"),
                str(self.temporary / "source"),
                str(self.port),
                self.phase,
                str(self.temporary / "reading-calls.jsonl"),
            ],
            cwd=BACKEND,
            stdin=subprocess.DEVNULL,
            stdout=self.output,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            with httpx.Client(base_url=self.url, timeout=1, trust_env=False) as client:

                def healthy():
                    if self.process.poll() is not None:
                        raise AssertionError(self.log.read_text(encoding="utf-8", errors="replace"))
                    try:
                        return client.get("/api/health").status_code == 200
                    except httpx.RequestError:
                        return False

                wait_until(healthy, bool, seconds=35)
            return self
        except BaseException:
            self.kill()
            raise

    def kill(self):
        # 只使用本测试创建并持有的 Popen 句柄，不扫描进程或按端口杀服务。
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=10)
        if self.output:
            self.output.close()
            self.output = None


@pytest.mark.skipif(os.name != "nt", reason="异常退出后代清理由 Windows Job Object 提供")
def test_killed_app_recovers_verification_logs_and_resumes_saved_reading_via_api(tmp_path):
    import _winapi

    source, data = tmp_path / "source", tmp_path / "data"
    source.mkdir()
    (source / "Long.cs").write_text("// persisted chunk\n" * 3000, encoding="utf-8")
    (source / "value.py").write_text("answer = 1\n", encoding="utf-8")
    originals = {path.name: path.read_bytes() for path in source.iterdir()}
    executions = tmp_path / "verification-starts.txt"
    verifier = (
        "import os,time; from pathlib import Path; "
        f"counter=Path({str(executions)!r}); "
        "counter.write_text(str(int(counter.read_text())+1) if counter.exists() else '1'); "
        "print('RESTART-LOG',flush=True); print('PID:'+str(os.getpid()),flush=True); "
        "time.sleep(120)"
    )
    initial, restarted, verifier_handle = TemporaryApp(tmp_path, "blocked"), None, None
    try:
        initial.start()
        with httpx.Client(base_url=initial.url, timeout=5, trust_env=False) as client:
            login(client, data)
            project = api(
                client,
                "POST",
                "/api/projects",
                json={
                    "name": "Real restart test",
                    "source_root": str(source),
                    "auto_associate": False,
                },
            )
            prefix = f"/api/p/{project['id']}"
            change = api(
                client,
                "POST",
                prefix + "/code-changes",
                json={
                    "title": "Persisted verification",
                    "goal": "Recover without automatic execution",
                },
            )
            profile = api(
                client,
                "POST",
                prefix + "/code-changes/profiles",
                json={
                    "name": "Known temporary Python",
                    "argv": [sys.executable, "-c", verifier],
                    "timeout_seconds": 120,
                },
            )
            change_url = prefix + "/code-changes/" + change["id"]
            api(client, "POST", change_url + "/verify", json={"profile_id": profile["id"]})
            running = wait_until(
                lambda: api(client, "GET", change_url),
                lambda row: "PID:" in (row["latest_verification"] or {}).get("output", ""),
            )
            verification = running["latest_verification"]
            assert running["status"] == "verifying"
            pid = int(verification["output"].split("PID:")[1].splitlines()[0])
            verifier_handle = _winapi.OpenProcess(0x00100000 | 0x1000 | 0x0001, False, pid)
            log_url = change_url + f"/verifications/{verification['id']}/log"
            saved_log = client.get(log_url)
            assert saved_log.status_code == 200 and b"RESTART-LOG" in saved_log.content
            job = api(client, "POST", prefix + "/project-reading", json={"title": "Checkpoint"})
            job_url = prefix + "/project-reading/" + job["id"]
            api(client, "POST", job_url + "/start")
            documents = wait_until(
                lambda: api(client, "GET", job_url + "/documents")["documents"],
                lambda rows: len(rows) == 1,
            )
            files = api(client, "GET", job_url + "/files")["files"]
            assert next(row for row in files if row["path"] == "Long.cs")["next_chunk"] == 1
            assert api(client, "GET", job_url)["status"] == "running"
            assert executions.read_text() == "1"
            initial.kill()
            assert _winapi.WaitForSingleObject(verifier_handle, 5000) == 0

        restarted = TemporaryApp(tmp_path, "resumed").start()
        with httpx.Client(base_url=restarted.url, timeout=5, trust_env=False) as client:
            assert client.get(change_url).status_code == 401
            login(client, data)
            recovered = api(client, "GET", change_url)
            assert recovered["status"] == "interrupted"
            assert recovered["latest_verification"]["status"] == "interrupted"
            assert recovered["latest_verification"]["id"] == verification["id"]
            assert (
                recovered["latest_verification"]["change_version"] == verification["change_version"]
            )
            assert recovered["latest_verification"]["exit_code"] is None
            assert client.get(log_url).content == saved_log.content
            assert api(client, "GET", job_url)["status"] == "interrupted"
            assert api(client, "GET", job_url + "/documents")["documents"] == documents
            api(client, "POST", job_url + "/start", json={"max_chunks": 256})
            completed = wait_until(
                lambda: api(client, "GET", job_url), lambda row: row["status"] != "running"
            )
            assert completed["status"] == "completed"
            resumed = api(client, "GET", job_url + "/documents")["documents"]
            assert any(row["id"] == documents[0]["id"] for row in resumed)
            calls = [
                json.loads(line)
                for line in (tmp_path / "reading-calls.jsonl").read_text().splitlines()
            ]
            resumed_chunks = [
                row["chunk_index"]
                for row in calls
                if row["phase"] == "resumed" and row["path"] == "Long.cs"
            ]
            assert resumed_chunks and min(resumed_chunks) == 1 and 0 not in resumed_chunks
            assert executions.read_text() == "1"
            assert api(client, "GET", change_url)["status"] == "interrupted"
            assert {path.name: path.read_bytes() for path in source.iterdir()} == originals
    finally:
        initial.kill()
        if restarted:
            restarted.kill()
        if verifier_handle is not None:
            if _winapi.WaitForSingleObject(verifier_handle, 0) != 0:
                _winapi.TerminateProcess(verifier_handle, 1)
                _winapi.WaitForSingleObject(verifier_handle, 5000)
            _winapi.CloseHandle(verifier_handle)


@pytest.fixture
def isolated_changes(services):
    paths, database, workspace, *_ = services
    changes = CodeChanges(paths, database, workspace, "drift-project")
    yield changes
    for task in changes._tasks.values():
        task.cancel.set()
    for task in changes._tasks.values():
        if task.thread:
            task.thread.join(timeout=12)


def test_verify_rejects_original_drift_before_launch_without_starting_command(
    isolated_changes, tmp_path
):
    changes = isolated_changes
    change = changes.create("Before launch", "Reject changed source baseline")
    marker = tmp_path / "must-not-run.txt"
    profile = changes.save_profile(
        "Do not execute",
        [
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
        ],
    )
    original = changes.workspace.root / "Program.cs"
    original.write_bytes(b"externally updated source")
    with pytest.raises(ValueError, match="基线冲突"):
        changes.verify(change["id"], profile["id"])
    assert not marker.exists()
    assert changes.get(change["id"])["latest_verification"] is None
    with changes.database.session() as session:
        assert session.query(VerificationRecord).count() == 0
    assert original.read_bytes() == b"externally updated source"


async def test_original_drift_during_successful_real_command_invalidates_verification(
    isolated_changes,
):
    changes = isolated_changes
    change = changes.create(
        "During verification", "Successful exit cannot approve changed original"
    )
    profile = changes.save_profile(
        "Gate real Python",
        [
            sys.executable,
            "-c",
            "from pathlib import Path; import time; print('WAITING',flush=True); "
            "gate=Path('.pytest_cache/release'); deadline=time.monotonic()+10\n"
            "while not gate.exists() and time.monotonic()<deadline: time.sleep(.01)\n"
            "assert gate.exists(); print('EXIT-ZERO',flush=True)",
        ],
        15,
    )
    changes.verify(change["id"], profile["id"])
    await asyncio.to_thread(
        wait_until,
        lambda: changes.get(change["id"]),
        lambda row: "WAITING" in row["latest_verification"]["output"],
    )
    original = changes.workspace.root / "Program.cs"
    original.write_bytes(b"source changed while command was running")
    with changes.database.session() as session:
        record = changes._row(session, change["id"])
        release = changes._work(record) / "release"
    # 闸门位于排除目录，放行命令不改变受验证的源码树版本。
    release = release.with_name(".pytest_cache") / "release"
    release.parent.mkdir()
    release.write_bytes(b"go")
    result = await changes.wait(change["id"], timeout_seconds=15)
    assert result["status"] == "failed"
    assert result["latest_verification"]["status"] == "failed"
    assert result["latest_verification"]["exit_code"] == 0
    assert "原件在验证期间改变" in result["error"]
    assert "EXIT-ZERO" in result["latest_verification"]["output"]
    assert original.read_bytes() == b"source changed while command was running"
