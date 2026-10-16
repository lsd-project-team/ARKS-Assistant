"""仅启动已配置 argv；副本只是工作目录，不承担操作系统进程沙箱职责。"""

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field

from app.modules.code_changes.windows_job import CREATE_SUSPENDED, WindowsJob


@dataclass
class VerificationTask:
    project_id: str
    change_id: str
    verification_id: str
    cancel: threading.Event = field(default_factory=threading.Event)
    finished: threading.Event = field(default_factory=threading.Event)
    process: subprocess.Popen | None = None
    thread: threading.Thread | None = None


def terminate_process(process):
    if os.name == "nt":
        if process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_process(task, argv, cwd, log_path, timeout_seconds, *, max_log_bytes=16 * 1024 * 1024):
    if task.cancel.is_set():
        return "cancelled", None, ""
    options = (
        {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
            | CREATE_SUSPENDED
        }
        if os.name == "nt"
        else {"start_new_session": True}
    )
    job = WindowsJob() if os.name == "nt" else None
    try:
        # 直接写入独立日志文件，不因前端输出截断丢失诊断，也避免 PIPE 缓冲堵塞。
        with log_path.open("wb") as output:
            task.process = subprocess.Popen(
                argv,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                shell=False,
                **options,
            )
            if job:
                try:
                    job.assign_and_resume(task.process.pid)
                except BaseException:
                    # 绑定失败时父进程仍挂起，必须结束它，不能退化为无容器执行。
                    terminate_process(task.process)
                    raise
            started = time.monotonic()
            while task.process.poll() is None:
                if output.tell() > max_log_bytes:
                    terminate_process(task.process)
                    output.truncate(max_log_bytes)
                    return "failed", task.process.returncode, "验证日志超过项目额度，已终止进程"
                if task.cancel.is_set():
                    terminate_process(task.process)
                    return "cancelled", task.process.returncode, ""
                if time.monotonic() - started >= timeout_seconds:
                    terminate_process(task.process)
                    return "timed_out", task.process.returncode, "验证命令超过配置的时间限制"
                task.cancel.wait(0.05)
            if output.tell() > max_log_bytes:
                output.truncate(max_log_bytes)
                return "failed", task.process.returncode, "验证日志超过项目额度"
            return (
                "passed" if task.process.returncode == 0 else "failed",
                task.process.returncode,
                "",
            )
    finally:
        if job:
            job.close()
        elif task.process:
            # 父进程即使已退出，组内后台后代也必须结束。
            terminate_process(task.process)
