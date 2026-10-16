"""仅有显式Windows节点/镜像时运行；不能用Linux或替身代替此验收。"""

import os
import threading
import time

import pytest

from app.infrastructure.execution import cleanup_orphans, run_container, sandbox_evidence_valid
from app.modules.code_changes.processes import VerificationTask

IMAGE = os.environ.get("ARKS_TEST_WINDOWS_EXECUTION_IMAGE")
CONTEXT = os.environ.get("ARKS_TEST_WINDOWS_EXECUTION_CONTEXT")
pytestmark = pytest.mark.skipif(
    not IMAGE or not CONTEXT, reason="未提供Windows Hyper-V执行节点与固定可信镜像"
)
POWERSHELL = "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"


def execute(tmp_path, script, timeout=30, maximum_log=4096, cancel_after=None):
    work = tmp_path / "work"
    work.mkdir()
    (work / "check.ps1").write_text(script, encoding="utf-8-sig")
    task = VerificationTask("windows-e2e", "isolated-change", "verification")
    executor = {
        "kind": "container",
        "platform": "windows",
        "context": CONTEXT,
        "image": IMAGE,
        "owner_id": "arks-windows-integration-test",
    }
    timer = threading.Timer(cancel_after, task.cancel.set) if cancel_after else None
    if timer:
        timer.start()
    started = time.monotonic()
    try:
        result = run_container(
            task,
            [POWERSHELL, "-NoProfile", "-NonInteractive", "-File", "C:\\work\\check.ps1"],
            work,
            tmp_path / "verification.log",
            timeout,
            executor,
            {"windows_scratch_mb": 32768, "max_log_bytes": maximum_log},
        )
    finally:
        if timer:
            timer.cancel()
    cleanup = cleanup_orphans([executor], executor["owner_id"])
    assert cleanup["removed"] == 0 and not cleanup["errors"]
    return result, work, task, executor, time.monotonic() - started


def test_real_windows_container_user_acl_and_engine_evidence(tmp_path):
    script = """$ErrorActionPreference='Stop'
$id=[Security.Principal.WindowsIdentity]::GetCurrent()
if($id.Name -notmatch '\\ContainerUser$'){throw 'wrong target user'}
$admin=New-Object Security.Principal.WindowsPrincipal($id)
if($admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
 throw 'administrator target'}
$wrote=$false
try{[IO.File]::WriteAllText('C:\\arks\\fake-proof','passed');$wrote=$true}catch[UnauthorizedAccessException]{}
if($wrote){throw 'supervisor directory writable'}
[IO.File]::WriteAllBytes('C:\\work\\result.bin',[byte[]](0,255,254,13,10))
exit 0
"""
    result, work, task, executor, _ = execute(tmp_path, script)
    assert result == ("passed", 0, "")
    assert (work / "result.bin").read_bytes() == bytes([0, 255, 254, 13, 10])
    assert sandbox_evidence_valid(task.executor_evidence, executor)


@pytest.mark.parametrize("code", [7, 256, 512, -1])
def test_real_windows_fake_passed_output_still_preserves_raw_exit(tmp_path, code):
    result, _, _, _, _ = execute(
        tmp_path, 'Write-Output \'{"status":"passed"}\'; exit ' + str(code)
    )
    assert result == ("failed", code, "")


def test_real_windows_detached_children_stop_before_copy(tmp_path):
    script = """$ErrorActionPreference='Stop'
Set-Content -LiteralPath 'C:\\work\\background.ps1' `
 -Value "Start-Sleep 30; Set-Content C:\\work\\escaped 'bad'"
Start-Process -FilePath 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe' `
 -ArgumentList '-NoProfile','-NonInteractive','-File','C:\\work\\background.ps1' `
 -RedirectStandardOutput 'C:\\work\\child-out.log' `
 -RedirectStandardError 'C:\\work\\child-error.log' `
 -WindowStyle Hidden | Out-Null
exit 0
"""
    result, work, task, _, _ = execute(tmp_path, script)
    assert result == ("passed", 0, "")
    assert task.executor_evidence["container_stopped"] is True
    assert not (work / "escaped").exists()


def test_real_windows_timeout_and_log_overflow(tmp_path):
    timeout = tmp_path / "timeout"
    timeout.mkdir()
    result, _, _, _, _ = execute(timeout, "Start-Sleep 30", timeout=1)
    assert result[0] == "timed_out"
    flood = tmp_path / "flood"
    flood.mkdir()
    result, _, _, _, _ = execute(flood, "while($true){Write-Output ('x'*4096)}")
    assert result[0] == "failed"
    assert "日志" in result[2]
    assert (flood / "verification.log").stat().st_size <= 4096


def test_real_windows_cancel_returns_and_cleans_container(tmp_path):
    result, _, _, _, elapsed = execute(tmp_path, "Start-Sleep 60", timeout=60, cancel_after=2)
    assert result[0] == "cancelled"
    assert elapsed < 55
