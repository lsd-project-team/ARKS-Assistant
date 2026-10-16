"""Windows 协议3：Docker exec退出码、停止态文件传输与独立TTL。"""

import hashlib
import json
import subprocess
import tarfile
import tempfile
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from .archives import replace_worktree, write_source
from .cli import ExecutionError, call, command, object_result, options
from .runner import checked_limits, labels_for, positive, start_pipe, stop_pipe
from .windows_bridge import bridge_arguments, run_bridge
from .windows_capacity import admit_capacity, probe_node_capacity, scratch_budget

ENTRYPOINT = [
    "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
    "-NoLogo",
    "-NoProfile",
    "-NonInteractive",
    "-File",
    "C:\\arks\\windows-supervisor.ps1",
]
CAPACITY_LOCK = threading.Lock()


def windows_arguments(executor, task, limits, ttl):
    reserved = scratch_budget(limits)
    bounded = checked_limits(limits)
    arguments = [
        "create",
        "--pull=never",
        "--isolation=hyperv",
        "--network=none",
        "--restart=no",
        "--no-healthcheck",
        "--user=ContainerAdministrator",
        "--cpus",
        str(bounded["cpus"]),
        "--memory",
        f"{bounded['memory_mb']}m",
        "--storage-opt",
        f"size={reserved}",
        "--env",
        f"ARKS_TTL_SECONDS={ttl}",
    ]
    for key, value in labels_for(task, executor).items():
        arguments += ["--label", f"{key}={value}"]
    return [*arguments, executor["image"]]


def ensure_stopped(executor, container):
    state = object_result(executor, "inspect", container)[0].get("State") or {}
    if state.get("Running") is True:
        call(executor, "kill", container)
    state = object_result(executor, "inspect", container)[0].get("State") or {}
    if state.get("Running") is not False:
        raise ExecutionError("无法确认 Windows 容器已停止，拒绝回传与通过")


def remove_container(executor, container):
    try:
        call(executor, "rm", "--force", "--volumes", container)
    except ExecutionError:
        pass


def wait_ready(executor, container, declared, cancel=None):
    started = time.monotonic()
    while time.monotonic() - started < 45:
        if cancel is not None and cancel.is_set():
            raise ExecutionError("Windows 准备已取消")
        raw = call(executor, "logs", "--tail", "1", container, timeout=10)
        if raw.strip():
            try:
                result = json.loads(raw.decode("utf-8-sig"))
            except (ValueError, UnicodeError) as exc:
                raise ExecutionError("Windows 管理员监督入口未返回有效容量证明") from exc
            validate_ready(result, declared)
            return result
        state = object_result(executor, "inspect", container)[0].get("State") or {}
        if state.get("Running") is not True:
            raise ExecutionError("Windows ACL准备或监督入口启动失败")
        time.sleep(0.1)
    raise ExecutionError("Windows ACL与容量准备超时")


def validate_ready(result, declared):
    if (
        not isinstance(result, dict)
        or result.get("protocol") != 3
        or result.get("phase") != "prepared"
        or result.get("supervisor") != "ContainerAdministrator"
    ):
        raise ExecutionError("Windows 监督协议或管理员身份不符合可信模板")
    for field in ["capacity_bytes", "available_bytes"]:
        if isinstance(result.get(field), bool) or not isinstance(result.get(field), int):
            raise ExecutionError("Windows 虚拟盘容量未知，拒绝执行")
    if not 0 < result["available_bytes"] <= result["capacity_bytes"] <= declared:
        raise ExecutionError("Windows 实际虚拟盘容量超过声明预算或数值无效")


def admit_windows_node(executor, info, limits):
    reserved = scratch_budget(limits)
    capacity = probe_node_capacity(executor, info.get("DockerRootDir"))
    admit_capacity(capacity, reserved)
    return capacity, reserved


def create_reserved(executor, task, info, limits, ttl):
    # 单进程内序列化准入和create；把本服务已预留但尚未实际写满的scratch也扣除。
    with CAPACITY_LOCK:
        capacity, reserved = admit_windows_node(executor, info, limits)
        managed = (
            call(
                executor,
                "ps",
                "-aq",
                "--filter",
                "label=io.arks.executor.owner",
            )
            .decode()
            .split()
        )
        outstanding = 0
        for identity in managed:
            data = object_result(executor, "inspect", identity)[0]
            owner = ((data.get("Config") or {}).get("Labels") or {}).get("io.arks.executor.owner")
            if owner != executor["owner_id"]:
                raise ExecutionError("Windows 执行节点已有其他服务预留；当前要求单服务专用节点")
            configuration = data.get("HostConfig") or {}
            value = (configuration.get("StorageOpt") or {}).get("size")
            if not isinstance(value, str) or not value.isdigit():
                raise ExecutionError("Windows 节点存在本服务未明确预留容量的遗留容器")
            outstanding += int(value)
        admit_capacity(capacity, reserved + outstanding)
        identity = call(executor, *windows_arguments(executor, task, limits, ttl)).decode().strip()
        if len(identity) != 64 or any(
            character not in "0123456789abcdef" for character in identity
        ):
            raise ExecutionError("Windows 节点返回无效容器标识")
        return identity, capacity, reserved


def probe_windows(executor, info, limits=None):
    limits = limits or {}
    probe_executor = {**executor, "owner_id": executor.get("owner_id", "arks-windows-probe")}
    task = SimpleNamespace(
        project_id="environment", change_id="probe", verification_id=uuid.uuid4().hex
    )
    container = None
    try:
        container, capacity, reserved = create_reserved(probe_executor, task, info, limits, 90)
        call(executor, "start", container)
        ready = wait_ready(executor, container, reserved)
        ensure_stopped(executor, container)
        return {
            "node_capacity": capacity,
            "scratch_reserved_bytes": reserved,
            "observed_capacity_bytes": ready["capacity_bytes"],
            "protocol": 3,
        }
    finally:
        if container:
            try:
                ensure_stopped(executor, container)
            except ExecutionError:
                pass
            remove_container(executor, container)


def wait_exec(task, executor, container, argv, log_path, timeout, maximum, daemon_id):
    arguments, program = bridge_arguments(executor, container, argv, maximum, timeout, daemon_id)
    return run_bridge(task, arguments, log_path, timeout, maximum, program)


def copy_out(task, executor, container, work, temporary, maximum):
    archive = temporary / "windows-result.tar"
    process, worker, overflow = start_pipe(
        executor, ["cp", f"{container}:C:\\work\\.", "-"], archive, maximum + 32 * 1024 * 1024
    )
    started = time.monotonic()
    try:
        while process.poll() is None:
            if task.cancel.is_set() or overflow.is_set() or time.monotonic() - started >= 90:
                raise ExecutionError("Windows 回传已取消或超过流量/时间限制")
            task.cancel.wait(0.05)
        worker.join(timeout=5)
        if process.returncode or overflow.is_set() or worker.is_alive():
            raise ExecutionError("Windows 停止态回传失败或超限")
        with archive.open("rb") as source:
            replace_worktree(source, work, maximum)
    finally:
        stop_pipe(process, worker)


def run_windows(task, argv, cwd, log_path, timeout_seconds, executor, limits):
    from .cli import probe_executor

    container = None
    try:
        if task.cancel.is_set():
            return "cancelled", None, ""
        if not argv or not all(isinstance(arg, str) and "\x00" not in arg for arg in argv):
            raise ExecutionError("Windows 验证argv不合法")
        positive(timeout_seconds, "时限", 86400)
        bounded = checked_limits(limits)
        labels_for(task, executor)
        probe = probe_executor(executor, limits=limits, check_runtime=False)
        if not probe["available"]:
            raise ExecutionError(probe["error"])
        configured_image = executor["image"]
        executor = {**executor, "image": probe["image_id"]}
        info = object_result(executor, "info", "--format", "{{json .}}")
        with tempfile.TemporaryDirectory(prefix="arks-windows-", dir=Path(cwd).parent) as temp:
            temporary = Path(temp)
            source = temporary / "source.tar"
            write_source(Path(cwd), source, bounded["max_output_bytes"])
            if task.cancel.is_set():
                return "cancelled", None, ""
            container, capacity, reserved = create_reserved(
                executor, task, info, limits, timeout_seconds + 60
            )
            admitted_at = int(time.time())
            daemon_id = info.get("ID")
            if not isinstance(daemon_id, str) or not daemon_id:
                raise ExecutionError("Windows 节点身份未知，拒绝执行")
            with source.open("rb") as stream:
                transfer = subprocess.run(
                    command(executor, "cp", "-", f"{container}:C:\\work"),
                    stdin=stream,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                    shell=False,
                    **options(),
                )
            if transfer.returncode:
                raise ExecutionError("Windows 停止态源码传入失败")
            if task.cancel.is_set():
                return "cancelled", None, ""
            call(executor, "start", container)
            ready = wait_ready(executor, container, reserved, task.cancel)
            if ready["available_bytes"] < bounded["max_output_bytes"] + 64 * 1024 * 1024:
                raise ExecutionError("Windows 虚拟盘没有足够工作余量")
            if task.cancel.is_set():
                return "cancelled", None, ""
            result = wait_exec(
                task,
                executor,
                container,
                argv,
                Path(log_path),
                timeout_seconds,
                bounded["max_log_bytes"],
                daemon_id,
            )
            ensure_stopped(executor, container)
            task.executor_evidence = {
                "image_id": probe["image_id"],
                "platform": "windows",
                "protocol": 3,
                "isolated": True,
                "isolation": "hyperv",
                "proof_kind": "engine_exec_exit",
                "container_stopped": True,
                "node_capacity": capacity,
                "scratch_reserved_bytes": reserved,
                "observed_capacity_bytes": ready["capacity_bytes"],
                "guest_available_bytes": ready["available_bytes"],
                "admitted_at": admitted_at,
                "node_id": hashlib.sha256(daemon_id.encode()).hexdigest(),
                "configured_image": configured_image,
                "configured_context": executor.get("context", "default"),
                "raw_exit_code": result[1],
            }
            if result[0] in {"passed", "failed"}:
                copy_out(
                    task, executor, container, Path(cwd), temporary, bounded["max_output_bytes"]
                )
            return result
    except (
        ExecutionError,
        OSError,
        ValueError,
        subprocess.TimeoutExpired,
        tarfile.TarError,
        IndexError,
        KeyError,
        TypeError,
    ) as exc:
        error = str(exc) if isinstance(exc, ExecutionError) else "Windows 隔离执行或回传失败"
        return "cancelled" if task.cancel.is_set() else "failed", None, error
    finally:
        if container:
            try:
                ensure_stopped(executor, container)
            except (ExecutionError, IndexError, KeyError, TypeError):
                pass
            remove_container(executor, container)
