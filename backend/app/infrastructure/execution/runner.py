"""固定镜像、无网络和无宿主挂载的容器执行。"""

import base64
import json
import subprocess
import tarfile
import tempfile
import threading
import time
import uuid
from pathlib import Path

from .archives import replace_worktree, write_source
from .cli import (
    IDENTITY,
    LABEL,
    ExecutionError,
    call,
    command,
    object_result,
    options,
    probe_executor,
)


def positive(value, name, maximum, *, integer=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, int if integer else (int, float))
        or not 0 < value <= maximum
    ):
        raise ExecutionError(f"{name} 资源限制不合法")
    return value


def checked_limits(limits):
    return {
        "cpus": positive(limits.get("cpus", 2), "CPU", 64),
        "memory_mb": positive(limits.get("memory_mb", 2048), "内存", 131072, integer=True),
        "pids": positive(limits.get("pids", 128), "进程数", 4096, integer=True),
        "max_log_bytes": positive(
            limits.get("max_log_bytes", 16777216), "日志", 1073741824, integer=True
        ),
        "max_output_bytes": int(
            positive(limits.get("max_output_bytes", 1073741824), "回传", 4294967296, integer=True)
        ),
    }


def labels_for(task, executor):
    owner = executor.get("owner_id", "")
    values = {
        "owner": owner,
        "project": task.project_id,
        "change": task.change_id,
        "verification": task.verification_id,
    }
    if not all(isinstance(value, str) and IDENTITY.fullmatch(value) for value in values.values()):
        raise ExecutionError("沙箱必须具有服务端生成的完整归属标识")
    return {f"{LABEL}.{key}": value for key, value in values.items()}


def create_arguments(executor, task, argv, timeout, limits, stage_volume=None):
    plan = base64.b64encode(
        json.dumps(
            {"argv": argv, "timeout": timeout, "max_log_bytes": limits["max_log_bytes"]}
        ).encode()
    ).decode()
    args = [
        "create",
        "--pull=never",
        "--network=none",
        "--restart=no",
        "--no-healthcheck",
        "--cpus",
        str(limits["cpus"]),
        "--memory",
        f"{limits['memory_mb']}m",
        "--log-driver=json-file",
        "--log-opt",
        f"max-size={limits['max_log_bytes']}",
        "--log-opt",
        "max-file=1",
        "--env",
        f"ARKS_PLAN={plan}",
    ]
    for key, value in labels_for(task, executor).items():
        args += ["--label", f"{key}={value}"]
    if stage_volume:
        if not IDENTITY.fullmatch(stage_volume):
            raise ExecutionError("临时卷归属不合法")
        args += ["--mount", f"type=volume,source={stage_volume},target=/stage,volume-nocopy"]
    if executor["platform"] == "linux":
        args += [
            "--read-only",
            "--user=0:0",
            "--cap-drop=ALL",
            "--cap-add=SETUID",
            "--cap-add=SETGID",
            "--cap-add=KILL",
            "--security-opt",
            "no-new-privileges=true",
            "--pids-limit",
            str(limits["pids"]),
            "--memory-swap",
            f"{limits['memory_mb']}m",
            "--tmpfs",
            f"/work:rw,nosuid,nodev,size={limits['max_output_bytes']},uid=1000,gid=1000",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=67108864,uid=1000,gid=1000",
            "--tmpfs",
            "/run/arks:rw,nosuid,nodev,noexec,size=1048576,mode=0700,uid=0,gid=0",
        ]
    else:
        args += [
            "--isolation=hyperv",
            "--user=ContainerUser",
            "--storage-opt",
            f"size={limits['max_output_bytes'] * 2 + 1073741824}",
        ]
    return [*args, executor["image"]]


def pipe_to_file(process, destination, maximum, exceeded):
    """限定落盘字节数；超额立即通知主线程销毁容器。"""
    with destination.open("wb") as output:
        size = 0
        while block := process.stdout.read(65536):
            remaining = maximum - size
            output.write(block[: max(0, remaining)])
            size += len(block)
            if size > maximum:
                exceeded.set()
                break


def start_pipe(executor, args, destination, maximum):
    process = subprocess.Popen(
        command(executor, *args),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
        **options(),
    )
    exceeded = threading.Event()
    worker = threading.Thread(
        target=pipe_to_file, args=(process, destination, maximum, exceeded), daemon=True
    )
    worker.start()
    return process, worker, exceeded


def stop_pipe(process, worker):
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)
    worker.join(timeout=10)
    if process.stdout:
        process.stdout.close()


def transport(executor, container, action):
    path = (
        "C:\\arks\\transport.py" if executor["platform"] == "windows" else "/opt/arks/transport.py"
    )
    return ["exec", container, "/usr/local/bin/python", "-I", path, action]


def wait_result(task, executor, container, timeout, log_path, maximum):
    logging, worker, overflow = start_pipe(
        executor, ["logs", "--follow", container], log_path, maximum
    )
    waiter = subprocess.Popen(
        command(executor, *transport(executor, container, "wait")),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=False,
        **options(),
    )
    started = time.monotonic()
    try:
        while waiter.poll() is None:
            if task.cancel.is_set():
                return "cancelled", None, ""
            if overflow.is_set():
                return "failed", None, "沙箱日志超过项目额度，已终止"
            if time.monotonic() - started >= timeout + 30:
                return "timed_out", None, "沙箱准备或验证超过时间限制"
            task.cancel.wait(0.05)
        raw = waiter.stdout.read(8193)
        if waiter.returncode or len(raw) > 8192:
            raise ExecutionError("沙箱未返回有效验证结果")
        result = json.loads(raw)
        if result.get("protocol") != 2:
            raise ExecutionError("沙箱未返回受保护的版本 2 验证证明")
        if result.get("status") not in {"passed", "failed", "timed_out"}:
            raise ExecutionError("沙箱结果状态不合法")
        if overflow.is_set():
            return "failed", None, "沙箱日志超过项目额度，已终止"
        return result["status"], result.get("exit_code"), str(result.get("error", ""))[:2000]
    finally:
        if waiter.poll() is None:
            waiter.kill()
        waiter.wait(timeout=10)
        waiter.stdout.close()
        stop_pipe(logging, worker)


def return_files(task, executor, container, root, temporary, maximum):
    archive = temporary / "result.tar"
    # tar 头也占空间，限制成员数后允许固定的元数据开销，仍限制总流量。
    process, worker, overflow = start_pipe(
        executor, transport(executor, container, "export"), archive, maximum + 32 * 1024 * 1024
    )
    started = time.monotonic()
    try:
        while process.poll() is None:
            if task.cancel.is_set():
                raise ExecutionError("回传时验证已取消")
            if overflow.is_set() or time.monotonic() - started > 90:
                raise ExecutionError("沙箱回传超过流量或时间限制")
            task.cancel.wait(0.05)
        worker.join(timeout=10)
        if process.returncode or worker.is_alive() or overflow.is_set():
            raise ExecutionError("沙箱回传失败或超过流量限制")
        with archive.open("rb") as source:
            replace_worktree(source, root, maximum)
    finally:
        stop_pipe(process, worker)


def run_container(task, argv, cwd, log_path, timeout_seconds, executor, limits):
    """只操作调用者给定的副本；失败不会回退到宿主命令。"""
    if executor.get("platform") == "windows":
        from .windows import run_windows

        return run_windows(task, argv, cwd, log_path, timeout_seconds, executor, limits)
    container = None
    stage_volume = None
    log_path = Path(log_path)
    try:
        if task.cancel.is_set():
            return "cancelled", None, ""
        if not argv or not all(isinstance(arg, str) and arg and "\x00" not in arg for arg in argv):
            raise ExecutionError("验证 argv 不合法")
        positive(timeout_seconds, "时限", 86400)
        limits = checked_limits(limits)
        labels_for(task, executor)
        probe = probe_executor(executor)
        if not probe["available"]:
            raise ExecutionError(probe["error"])
        # 镜像名称在探测后固定成不可变 ID，避免标签或配置竞态。
        configured_image = executor["image"]
        executor = {**executor, "image": probe["image_id"]}
        with tempfile.TemporaryDirectory(prefix="arks-transfer-", dir=Path(cwd).parent) as temp:
            temporary = Path(temp)
            source = temporary / "source.tar"
            write_source(Path(cwd), source, limits["max_output_bytes"])
            stage_volume = "arks-stage-" + uuid.uuid4().hex
            volume_args = ["volume", "create"]
            for key, value in labels_for(task, executor).items():
                volume_args += ["--label", f"{key}={value}"]
            call(executor, *volume_args, stage_volume)
            container = (
                call(
                    executor,
                    *create_arguments(executor, task, argv, timeout_seconds, limits, stage_volume),
                )
                .decode()
                .strip()
            )
            if not container or not all(character in "0123456789abcdef" for character in container):
                raise ExecutionError("沙箱节点返回无效容器标识")
            stage = "C:\\stage" if executor["platform"] == "windows" else "/stage"
            with source.open("rb") as stream:
                process = subprocess.run(
                    command(executor, "cp", "-a", "-", f"{container}:{stage}"),
                    stdin=stream,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                    shell=False,
                    **options(),
                )
            if process.returncode:
                raise ExecutionError("源码传入隔离副本失败")
            if task.cancel.is_set():
                return "cancelled", None, ""
            call(executor, "start", container)
            task.executor_evidence = {
                "image_id": probe["image_id"],
                "platform": executor["platform"],
                "protocol": 2,
                "isolated": True,
                "configured_image": configured_image,
                "configured_context": executor.get("context", "default"),
            }
            result = wait_result(
                task, executor, container, timeout_seconds, log_path, limits["max_log_bytes"]
            )
            if result[0] in {"passed", "failed"}:
                return_files(
                    task, executor, container, Path(cwd), temporary, limits["max_output_bytes"]
                )
            return result
    except (
        ExecutionError,
        OSError,
        ValueError,
        subprocess.TimeoutExpired,
        tarfile.TarError,
    ) as exc:
        error = str(exc) if isinstance(exc, ExecutionError) else "隔离执行或安全回传失败"
        return "cancelled" if task.cancel.is_set() else "failed", None, error
    finally:
        if container:
            try:
                call(executor, "rm", "--force", "--volumes", container)
            except ExecutionError:
                # 精确标签保留供下次启动清理；不会使用全局 prune。
                pass
        if stage_volume:
            try:
                call(executor, "volume", "rm", stage_volume)
            except ExecutionError:
                pass


def cleanup_orphans(executors, owner_id, active_ids=()):
    """只清理本数据目录的遗留容器，保留当前活跃验证和其他服务资源。"""
    if not isinstance(owner_id, str) or not IDENTITY.fullmatch(owner_id):
        raise ExecutionError("遗留清理缺少有效服务归属")
    removed = 0
    volumes_removed = 0
    errors = []
    contexts = {executor.get("context", "default"): executor for executor in executors}
    for executor in contexts.values():
        try:
            identities = (
                call(executor, "ps", "-aq", "--filter", f"label={LABEL}.owner={owner_id}")
                .decode()
                .split()
            )
            for identity in identities:
                data = object_result(executor, "inspect", identity)[0]
                labels = (data.get("Config") or {}).get("Labels") or {}
                if labels.get(f"{LABEL}.owner") != owner_id:
                    continue
                verification = labels.get(f"{LABEL}.verification")
                if not verification or verification in active_ids:
                    continue
                call(executor, "rm", "--force", "--volumes", identity)
                removed += 1
            volumes = (
                call(executor, "volume", "ls", "-q", "--filter", f"label={LABEL}.owner={owner_id}")
                .decode()
                .split()
            )
            for name in volumes:
                data = object_result(executor, "volume", "inspect", name)[0]
                labels = data.get("Labels") or {}
                if (
                    labels.get(f"{LABEL}.owner") != owner_id
                    or not labels.get(f"{LABEL}.verification")
                    or labels[f"{LABEL}.verification"] in active_ids
                ):
                    continue
                call(executor, "volume", "rm", name)
                volumes_removed += 1
        except ExecutionError as exc:
            errors.append(str(exc))
    return {"removed": removed, "volumes_removed": volumes_removed, "errors": errors}
