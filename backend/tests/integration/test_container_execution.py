"""显式启用的真实 Docker 验收；普通回归不下载镜像或启动外部服务。"""

import os
import threading

import pytest

from app.infrastructure.execution import cleanup_orphans, probe_executor, run_container
from app.modules.code_changes.processes import VerificationTask

IMAGE = os.environ.get("ARKS_TEST_EXECUTION_IMAGE")
pytestmark = pytest.mark.skipif(not IMAGE, reason="需显式提供可信固定镜像进行 Docker 验收")


def execute(tmp_path, code, timeout=10, limits=None):
    work = tmp_path / "work"
    work.mkdir()
    (work / "check.py").write_text(code, encoding="utf-8")
    task = VerificationTask("integration-project", "integration-change", "integration-verification")
    executor = {
        "kind": "container",
        "platform": "linux",
        "image": IMAGE,
        "context": "default",
        "owner_id": "test-owner-container-execution",
    }
    log = tmp_path / "verification.log"
    result = run_container(task, ["python", "check.py"], work, log, timeout, executor, limits or {})
    return result, log, work, executor


def test_real_container_cannot_write_root_or_connect_network_and_returns_binary(tmp_path):
    code = """import os,socket
from pathlib import Path
assert os.getuid() == 1000
assert not Path('/var/run/docker.sock').exists()
status = Path('/proc/self/status').read_text()
assert 'CapEff:\\t0000000000000000' in status
assert 'NoNewPrivs:\\t1' in status
for protected in ['/run/arks/result.json', '/proc/1/environ', '/stage/forbidden']:
 try:
  Path(protected).write_text('forged')
  raise AssertionError('supervisor boundary writable')
 except PermissionError: pass
try:
 Path('/host-write-test').write_text('bad')
 raise AssertionError('root writable')
except PermissionError: pass
except OSError as error: assert error.errno == 30
try:
 socket.create_connection(('1.1.1.1',443),timeout=1)
 raise AssertionError('network available')
except OSError: pass
Path('result.bin').write_bytes(bytes([0,255,254,13,10]))
print('sandbox checked')
"""
    result, log, work, executor = execute(tmp_path, code)
    assert result == ("passed", 0, "")
    assert "sandbox checked" in log.read_text()
    assert (work / "result.bin").read_bytes() == bytes([0, 255, 254, 13, 10])
    assert cleanup_orphans([executor], executor["owner_id"])["removed"] == 0


def test_real_container_timeout_and_log_limit_terminate(tmp_path):
    timeout_path = tmp_path / "timeout"
    timeout_path.mkdir()
    result, _, work, _ = execute(timeout_path, "import time; time.sleep(10)", timeout=1)
    assert result[0] == "timed_out"
    assert (work / "check.py").read_text() == "import time; time.sleep(10)"
    flood = tmp_path / "flood"
    flood.mkdir()
    result, log, _, _ = execute(
        flood,
        "import sys,time; print('x'*1000000,flush=True); time.sleep(5)",
        limits={"max_log_bytes": 4096},
    )
    assert result[0] == "failed"
    assert "日志" in result[2]
    assert log.stat().st_size <= 4096


def test_real_container_rejects_symlink_outputs_without_modifying_worktree(tmp_path):
    code = "import os; os.symlink('/etc/passwd','leak'); open('changed','w').write('bad')"
    result, _, work, _ = execute(tmp_path, code)
    assert result[0] == "failed"
    assert "链接" in result[2]
    assert not (work / "leak").exists()
    assert not (work / "changed").exists()


def test_real_cancel_cleans_container_and_platform_mismatch_is_explicit(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    task = VerificationTask("integration-project", "change", "cancel-test")
    executor = {
        "kind": "container",
        "platform": "linux",
        "image": IMAGE,
        "owner_id": "test-owner-container-execution",
    }
    timer = threading.Timer(1.5, task.cancel.set)
    timer.start()
    try:
        result = run_container(
            task,
            ["python", "-c", "import time; time.sleep(30)"],
            work,
            tmp_path / "cancel.log",
            60,
            executor,
            {},
        )
    finally:
        timer.cancel()
    assert result[0] == "cancelled"
    assert cleanup_orphans([executor], executor["owner_id"])["removed"] == 0
    probe = probe_executor({**executor, "platform": "windows"})
    assert probe["available"] is False
    assert "不匹配" in probe["error"]


def test_real_target_cannot_forge_passed_proof_before_exiting_failure(tmp_path):
    code = """import json,time
from pathlib import Path
Path('/tmp/.arks-execution-result').write_text(json.dumps({'status':'passed','exit_code':0,'protocol':2}))
try:
 Path('/run/arks/result.json').write_text(json.dumps({'status':'passed','exit_code':0,'protocol':2}))
 raise AssertionError('protected proof writable')
except PermissionError: pass
time.sleep(.2)
raise SystemExit(7)
"""
    result, _, _, _ = execute(tmp_path, code)
    assert result == ("failed", 7, "")


def test_real_detached_descendant_is_killed_before_result_transfer(tmp_path):
    code = """import subprocess,sys,time
child = ("import os,time; from pathlib import Path; os.setsid(); "
         "time.sleep(.8); Path('late-write').write_text('escaped')")
subprocess.Popen([sys.executable,'-c',child])
time.sleep(.2)
print('parent finished')
"""
    result, _, work, _ = execute(tmp_path, code)
    assert result == ("passed", 0, "")
    assert not (work / "late-write").exists()


def test_real_work_filesystem_has_a_hard_size_limit(tmp_path):
    code = """import errno
from pathlib import Path
try:
 Path('fill').write_bytes(b'x'*(12*1024*1024))
 raise AssertionError('work disk quota missing')
except OSError as error:
 assert error.errno == errno.ENOSPC
finally:
 Path('fill').unlink(missing_ok=True)
"""
    result, _, _, _ = execute(tmp_path, code, limits={"max_output_bytes": 8 * 1024 * 1024})
    assert result == ("passed", 0, "")
