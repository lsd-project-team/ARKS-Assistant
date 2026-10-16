"""在Windows节点保留32位Engine状态，再以受信帧返回Linux控制端。"""

import base64
import hashlib
import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field

from .cli import ExecutionError, object_result, options
from .windows_capacity import RESOURCE, powershell_arguments


def bridge_arguments(executor, container, argv, maximum, timeout, daemon_id):
    endpoint = object_result(
        executor,
        "context",
        "inspect",
        executor.get("context", "default"),
        "--format",
        "{{json .Endpoints.docker}}",
    )
    host = endpoint.get("Host", "")
    pipe = (
        "dockerDesktopWindowsEngine"
        if host.endswith("/dockerDesktopWindowsEngine")
        else "docker_engine"
    )
    payload = {
        "container": container,
        "argv": argv,
        "maximum": maximum,
        "timeout": timeout,
        "daemon_id": daemon_id,
        "pipe": pipe,
    }
    script = (RESOURCE / "windows-exec-bridge.ps1").read_text(encoding="utf-8")
    script = script.replace(
        "CSHARP_SOURCE", (RESOURCE / "windows-process-bridge.cs").read_text(encoding="utf-8")
    )
    script = script.replace(
        "PAYLOAD_BASE64", base64.b64encode(json.dumps(payload).encode()).decode()
    )
    return bootstrap_arguments(host, script)


def bootstrap_arguments(host, script):
    # OpenSSH默认cmd命令行仅8191字符；源码通过有界stdin传输，命令行只含固定引导器。
    program = script.encode("utf-8")
    encoded = base64.b64encode(program)
    if len(encoded) > 1024 * 1024:
        raise ExecutionError("Windows 受信桥接程序与参数超过传输限制")
    digest = hashlib.sha256(program).hexdigest()
    bootstrap = """$ErrorActionPreference='Stop';
$buffer=New-Object char[] 4096;$text=New-Object Text.StringBuilder;
while(($n=[Console]::In.Read($buffer,0,$buffer.Length)) -gt 0){
 if($text.Length+$n -gt 1048576){throw 'Bridge input exceeded'};
 [void]$text.Append($buffer,0,$n)};
$bytes=[Convert]::FromBase64String($text.ToString());
$sha=[Security.Cryptography.SHA256]::Create();
$actual=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant();
if($actual -ne 'DIGEST'){throw 'Bridge input changed'};
& ([ScriptBlock]::Create([Text.Encoding]::UTF8.GetString($bytes)))
""".replace("DIGEST", digest)
    arguments = powershell_arguments(host, base64.b64encode(bootstrap.encode("utf-16-le")).decode())
    return arguments, encoded


@dataclass
class BridgeState:
    raw_exit_code: int | None = None
    terminal: str = ""
    error: str = ""
    ready: threading.Event = field(default_factory=threading.Event)


def decode_frame(line, output, state, used, maximum):
    frame = json.loads(line)
    if not isinstance(frame, dict) or state.terminal:
        raise ExecutionError("Windows 节点桥接帧顺序不正确")
    if set(frame) == {"type", "data"} and frame["type"] == "output":
        data = base64.b64decode(frame["data"], validate=True)
        if used + len(data) > maximum:
            raise ExecutionError("Windows 节点输出超过日志额度")
        output.write(data)
        output.flush()
        return used + len(data)
    if set(frame) == {"type", "raw_exit_code"} and frame["type"] == "result":
        raw = frame["raw_exit_code"]
        if isinstance(raw, bool) or not isinstance(raw, int) or not -(2**31) <= raw < 2**31:
            raise ExecutionError("Windows Engine未返回有效32位原始退出码")
        state.raw_exit_code = raw
        state.terminal = "result"
    elif frame in [{"type": "overflow"}, {"type": "timed_out"}]:
        state.terminal = frame["type"]
    else:
        raise ExecutionError("Windows 节点返回未知桥接帧")
    state.ready.set()
    return used


def read_frames(stream, destination, maximum, state):
    used = 0
    pending = bytearray()
    try:
        with destination.open("wb") as output:
            while block := os.read(stream.fileno(), 4096):
                pending.extend(block)
                while b"\n" in pending:
                    line, _, rest = pending.partition(b"\n")
                    pending = bytearray(rest)
                    if len(line) > 32768:
                        raise ExecutionError("Windows 桥接元数据超限")
                    used = decode_frame(line.rstrip(b"\r"), output, state, used, maximum)
                if len(pending) > 32768:
                    raise ExecutionError("Windows 桥接元数据超限")
            if pending or not state.terminal:
                raise ExecutionError("Windows 桥接连接中断或缺少原始退出码")
    except (ExecutionError, OSError, ValueError, TypeError) as exc:
        state.error = str(exc) if isinstance(exc, ExecutionError) else "Windows 桥接数据无效"
        state.ready.set()


def send_program(stream, data, state):
    try:
        if data:
            stream.write(data)
            stream.flush()
    except (OSError, ValueError):
        state.error = "Windows 受信桥接程序传输中断"
    finally:
        try:
            stream.close()
        except OSError:
            pass


def run_bridge(task, arguments, log_path, timeout, maximum, input_data=b""):
    if task.cancel.is_set():
        return "cancelled", None, ""
    state = BridgeState()
    process = subprocess.Popen(
        arguments,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=False,
        **options(),
    )
    reader = threading.Thread(
        target=read_frames, args=(process.stdout, log_path, maximum, state), daemon=True
    )
    reader.start()
    writer = threading.Thread(
        target=send_program, args=(process.stdin, input_data, state), daemon=True
    )
    writer.start()
    started = time.monotonic()
    try:
        while process.poll() is None:
            if task.cancel.is_set():
                return "cancelled", None, ""
            if state.error or state.terminal == "overflow":
                return "failed", None, state.error or "Windows 验证日志超过项目额度"
            if state.terminal == "timed_out" or time.monotonic() - started >= timeout + 10:
                return "timed_out", None, "Windows 验证命令超过时间限制"
            task.cancel.wait(0.05)
        reader.join(timeout=5)
        if state.error or reader.is_alive() or process.returncode:
            return "failed", None, state.error or "Windows 受信节点桥接失败"
        if state.terminal == "overflow":
            return "failed", None, "Windows 验证日志超过项目额度"
        if state.terminal == "timed_out":
            return "timed_out", None, "Windows 验证命令超过时间限制"
        if state.terminal != "result" or state.raw_exit_code is None:
            return "failed", None, "Windows 缺少Engine原始退出码"
        return "passed" if state.raw_exit_code == 0 else "failed", state.raw_exit_code, ""
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        reader.join(timeout=10)
        writer.join(timeout=5)
        process.stdout.close()
