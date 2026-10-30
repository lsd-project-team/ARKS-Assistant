"""真实uvicorn子进程；只停止由本轮创建且仍持有的进程句柄。"""

import socket
import subprocess
import sys
import time
from contextlib import contextmanager

import httpx

from .safety import PROJECT, SmokeFailure, require


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def command(port):
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--workers",
        "1",
        "--no-access-log",
        "--log-level",
        "warning",
    ]


def launch(environment, port, output):
    return subprocess.Popen(
        command(port),
        cwd=PROJECT / "backend",
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=output,
        stderr=output,
        shell=False,
        start_new_session=sys.platform != "win32",
    )


@contextmanager
def running(environment, log, host):
    port = free_port()
    with log.open("wb") as output:
        process = launch(environment, port, output)
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}",
                timeout=30,
                headers={"Host": host},
                trust_env=False,
            ) as client:
                deadline = time.monotonic() + 90
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise SmokeFailure("uvicorn_start_failed")
                    try:
                        response = client.get("/api/health", timeout=1)
                        if response.status_code == 200:
                            health = response.json()
                            require(
                                health.get("ok") is True
                                and health.get("process_id") == process.pid
                                and health.get("data_directory")
                                == environment["TRUNK_AGENT_DATA_DIR"]
                                and health.get("workspace") == environment["TRUNK_AGENT_WORKSPACE"],
                                "uvicorn_health_identity_mismatch",
                            )
                            break
                    except (httpx.HTTPError, ValueError):
                        pass
                    time.sleep(0.1)
                else:
                    raise SmokeFailure("uvicorn_health_timeout")
                yield client
        finally:
            stop(process)


def reject_duplicate(environment, log):
    with log.open("wb") as output:
        process = launch(environment, free_port(), output)
        try:
            try:
                result = process.wait(timeout=60)
            except subprocess.TimeoutExpired as error:
                raise SmokeFailure("duplicate_service_not_rejected") from error
        finally:
            stop(process)
    require(
        result != 0 and "此数据目录已被另一个" in log.read_text(encoding="utf-8"),
        "duplicate_service_lock_not_proven",
    )
