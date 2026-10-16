"""固定只读节点容量探针；不提供可携带目标命令的远程 shell 接口。"""

import base64
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

from .cli import ExecutionError, object_result, options

RESOURCE = Path(__file__).resolve().parents[4] / "resources" / "execution"
LOCAL_ROOT = re.compile(r"[A-Za-z]:\\(?:[A-Za-z0-9_. -]+\\?)*\Z")
SSH_HOST = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?\Z")
SSH_USER = re.compile(r"[A-Za-z0-9_.-]{1,64}\Z")


def encoded_probe(root):
    if (
        not isinstance(root, str)
        or not LOCAL_ROOT.fullmatch(root)
        or any(part in {".", ".."} for part in root.split("\\"))
    ):
        raise ExecutionError("Windows Docker 数据路径不是受支持的本地盘绝对路径")
    script = (RESOURCE / "probe-node.ps1").read_text(encoding="utf-8")
    script = script.replace("ROOT_BASE64", base64.b64encode(root.encode()).decode())
    return base64.b64encode(script.encode("utf-16-le")).decode()


def probe_arguments(endpoint, root):
    return powershell_arguments(endpoint, encoded_probe(root))


def powershell_arguments(endpoint, encoded):
    powershell = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
        encoded,
    ]
    if endpoint.startswith("npipe://"):
        if os.name != "nt" or endpoint not in {
            "npipe:////./pipe/docker_engine",
            "npipe:////./pipe/dockerDesktopWindowsEngine",
        }:
            raise ExecutionError("Windows 容量探针只支持本机受信管道或已配置 SSH context")
        executable = (
            Path(os.environ.get("SystemRoot", "C:\\Windows"))
            / "System32/WindowsPowerShell/v1.0/powershell.exe"
        )
        return [str(executable), *powershell[1:]]
    try:
        target = urlsplit(endpoint)
        host = target.hostname or ""
        user = target.username
        port = target.port or 22
        if (
            target.scheme != "ssh"
            or not SSH_HOST.fullmatch(host)
            or (user is not None and not SSH_USER.fullmatch(user))
            or target.password
            or target.path not in {"", "/"}
            or target.query
            or target.fragment
            or not 1 <= port <= 65535
        ):
            raise ValueError("invalid SSH endpoint")
    except (TypeError, ValueError) as exc:
        raise ExecutionError("Windows 远端容量核对需要已配置的受信 SSH context") from exc
    executable = shutil.which("ssh")
    if not executable:
        raise ExecutionError("没有 SSH 客户端，无法核对 Windows 节点真实剩余空间")
    return [
        executable,
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ConnectTimeout=10",
        "-p",
        str(port),
        f"{user}@{host}" if user else host,
        *powershell,
    ]


def validate_capacity(value, now=None):
    now = time.time() if now is None else now
    if not isinstance(value, dict) or value.get("probe_version") != 1:
        raise ExecutionError("节点容量证明格式不正确")
    for field in ["free_bytes", "total_bytes", "measured_at"]:
        if isinstance(value.get(field), bool) or not isinstance(value.get(field), int):
            raise ExecutionError("节点容量证明缺少有效数值")
    if (
        not 0 < value["free_bytes"] <= value["total_bytes"]
        or not now - 120 <= value["measured_at"] <= now + 30
    ):
        raise ExecutionError("节点容量证明已过期或数值不可信")
    return {
        key: value[key] for key in ["probe_version", "free_bytes", "total_bytes", "measured_at"]
    }


def probe_node_capacity(executor, root):
    endpoint = object_result(
        executor,
        "context",
        "inspect",
        executor.get("context", "default"),
        "--format",
        "{{json .Endpoints.docker}}",
    )
    if not isinstance(endpoint, dict):
        raise ExecutionError("Docker context 没有有效的节点端点")
    arguments = probe_arguments(endpoint.get("Host", ""), root)
    try:
        result = subprocess.run(
            arguments, capture_output=True, timeout=25, shell=False, **options()
        )
        if result.returncode or len(result.stdout) > 8192:
            raise ExecutionError("受信 Windows 节点容量核对失败")
        return validate_capacity(json.loads(result.stdout.decode("utf-8-sig")))
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise ExecutionError("无法取得受信 Windows 节点容量证明") from exc


def scratch_budget(limits):
    value = (limits or {}).get("windows_scratch_mb", 32768)
    if isinstance(value, bool) or not isinstance(value, int) or not 20480 <= value <= 1048576:
        raise ExecutionError("Windows scratch 预算必须明确为 20480 至 1048576 MB")
    return value * 1024 * 1024


def admit_capacity(capacity, reserved):
    # 最少留出1GiB宿主余量，不能把虚拟C盘的free冒充节点物理盘的free。
    if capacity["free_bytes"] < reserved + 1073741824:
        raise ExecutionError("Windows 节点剩余空间不足以预留 scratch 与宿主余量")
