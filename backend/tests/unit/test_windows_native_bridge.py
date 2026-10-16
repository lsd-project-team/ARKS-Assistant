"""真实Windows本机原生进程子组件；不等于Windows容器或ZX2200构建验收。"""

import base64
import json
import os
import threading
import time
from pathlib import Path

import pytest

from app.infrastructure.execution.windows_bridge import bootstrap_arguments, run_bridge
from app.infrastructure.execution.windows_capacity import RESOURCE
from app.modules.code_changes.processes import VerificationTask

pytestmark = pytest.mark.skipif(os.name != "nt", reason="真实Windows原生进程桥子组件")
POWERSHELL = str(
    Path(os.environ.get("SystemRoot", "C:\\Windows"))
    / "System32/WindowsPowerShell/v1.0/powershell.exe"
)


def native_program(child, maximum=4096, timeout=10):
    source = (RESOURCE / "windows-process-bridge.cs").read_text(encoding="utf-8")
    encoded = base64.b64encode(child.encode("utf-16-le")).decode()
    script = """$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
Add-Type -TypeDefinition @'
SOURCE
'@
$exe='EXECUTABLE'
[ArksProcessBridge]::Run($exe,[string[]]@('-NoLogo','-NoProfile','-NonInteractive',
 '-EncodedCommand','CHILD'),MAXIMUM,TIMEOUT)
""".replace("SOURCE", source).replace("EXECUTABLE", POWERSHELL.replace("'", "''"))
    return (
        script.replace("CHILD", encoded)
        .replace("MAXIMUM", str(maximum))
        .replace("TIMEOUT", str(timeout))
    )


def execute(tmp_path, child, maximum=4096, timeout=10, task=None):
    arguments, program = bootstrap_arguments(
        "npipe:////./pipe/docker_engine", native_program(child, maximum, timeout)
    )
    # 默认Windows OpenSSH的cmd.exe只接受8191字符，长程序应从stdin传输。
    assert sum(len(argument) + 3 for argument in arguments) < 8191
    task = task or VerificationTask("native", "bridge", "test")
    log = tmp_path / "native.log"
    result = run_bridge(task, arguments, log, timeout, maximum, program)
    return result, log


@pytest.mark.parametrize("code", [0, 7, 256, 512, -1])
def test_native_process_preserves_signed_32bit_exitcode(tmp_path, code):
    result, log = execute(tmp_path, f"[Environment]::Exit({code})")
    assert result == ("passed" if code == 0 else "failed", code, "")
    assert log.read_bytes() == b""


def test_native_target_stdout_cannot_forge_bridge_result(tmp_path):
    fake = json.dumps({"type": "result", "raw_exit_code": 0})
    result, log = execute(tmp_path, "[Console]::WriteLine('" + fake + "'); exit 7")
    assert result == ("failed", 7, "")
    assert json.loads(log.read_text()) == {"type": "result", "raw_exit_code": 0}


def test_native_dual_stream_single_line_flood_is_bounded(tmp_path):
    child = """$chunk=New-Object byte[] 16384
while($true){[Console]::OpenStandardOutput().Write($chunk,0,$chunk.Length)
 [Console]::OpenStandardError().Write($chunk,0,$chunk.Length)}
"""
    result, log = execute(tmp_path, child, maximum=4096)
    assert result[0] == "failed" and "日志" in result[2]
    assert log.stat().st_size == 4096


def test_native_timeout_terminates_command(tmp_path):
    result, _ = execute(tmp_path, "Start-Sleep 30", timeout=1)
    assert result[0] == "timed_out"


def test_native_cancel_closes_job_and_kills_actual_child(tmp_path):
    pid_path = tmp_path / "child.pid"
    escaped = str(pid_path).replace("'", "''")
    task = VerificationTask("native", "bridge", "cancel")
    failures = []

    def cancel_after_child_started():
        deadline = time.monotonic() + 15
        while not pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not pid_path.exists():
            failures.append("原生命令没有启动")
        task.cancel.set()

    timer = threading.Thread(target=cancel_after_child_started, daemon=True)
    timer.start()
    result, _ = execute(
        tmp_path,
        f"[IO.File]::WriteAllText('{escaped}',[string]$PID); Start-Sleep 30",
        task=task,
        timeout=20,
    )
    timer.join(timeout=2)
    assert not failures
    assert result[0] == "cancelled"
    # os.kill(pid,0)在Windows会终止进程，使用只读原生GetProcessById查询。
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    deadline = time.monotonic() + 5
    running = True
    while running and time.monotonic() < deadline:
        handle = kernel.OpenProcess(0x1000, False, int(pid_path.read_text()))
        if not handle:
            running = False
        else:
            code = ctypes.c_ulong()
            assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
            running = code.value == 259
            kernel.CloseHandle(handle)
        time.sleep(0.05)
    assert not running, "取消后真实原生命令应由Job关闭回收"
