"""可信镜像入口：即使应用服务退出，工作进程也有独立截止时间。"""

import base64
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

WORK = Path("/work")
STAGE = Path("/stage")
RESULT = Path("/run/arks/result.json")


def target_identity():
    os.setgroups([])
    os.setgid(1000)
    os.setuid(1000)


def stop_targets():
    # setsid 脱离会话的后代仍属于固定 target UID，证明生成前必须全部终止。
    for _ in range(50):
        remaining = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                status = (entry / "status").read_text()
                uid = next(
                    line.split()[1] for line in status.splitlines() if line.startswith("Uid:")
                )
                if uid == "1000" and "State:\tZ" not in status:
                    remaining.append(int(entry.name))
            except (OSError, StopIteration):
                continue
        if not remaining:
            return
        for identity in remaining:
            try:
                os.kill(identity, signal.SIGKILL)
            except ProcessLookupError:
                pass
        while True:
            try:
                if os.waitpid(-1, os.WNOHANG)[0] == 0:
                    break
            except ChildProcessError:
                break
        time.sleep(0.05)
    raise RuntimeError("目标进程未全部停止，拒绝生成验证证明")


def forward_output(process, maximum, overflow):
    size = 0
    while block := os.read(process.stdout.fileno(), 65536):
        remaining = maximum - size
        sys.stdout.buffer.write(block[: max(0, remaining)])
        sys.stdout.buffer.flush()
        size += len(block)
        if size > maximum:
            overflow.set()
            return


def main():
    if os.name == "nt":
        raise RuntimeError("Windows 监督身份尚未验收，禁止执行")
    plan = json.loads(base64.b64decode(os.environ["ARKS_PLAN"]))
    # 可信复制程序以目标身份创建文件，不给监督进程增加 CHOWN 能力。
    subprocess.run(
        [sys.executable, "-I", "/opt/arks/transport.py", "prepare"],
        check=True,
        preexec_fn=target_identity,
    )
    # 传入卷只用于 staging，目标不能绕过 /work tmpfs 向宿主磁盘写入。
    STAGE.chmod(0o700)
    started = time.monotonic()
    process = subprocess.Popen(
        plan["argv"],
        cwd=WORK,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        preexec_fn=target_identity,
    )
    overflow = threading.Event()
    output = threading.Thread(
        target=forward_output, args=(process, plan["max_log_bytes"], overflow), daemon=True
    )
    output.start()
    try:
        while process.poll() is None:
            if overflow.is_set() or time.monotonic() - started >= plan["timeout"]:
                process.kill()
                break
            time.sleep(0.02)
        code = process.wait()
        result = {"status": "passed" if code == 0 else "failed", "exit_code": code, "error": ""}
    except BaseException:
        process.kill()
        process.wait()
        raise
    finally:
        stop_targets()
        output.join(timeout=5)
        if output.is_alive():
            raise RuntimeError("输出进程未退出，拒绝生成验证证明")
    if overflow.is_set():
        result = {"status": "failed", "exit_code": None, "error": "沙箱日志超过项目额度"}
    elif time.monotonic() - started >= plan["timeout"]:
        result = {"status": "timed_out", "exit_code": None, "error": "验证命令超过时间限制"}
    result["elapsed"] = time.monotonic() - started
    result["protocol"] = 2
    RESULT.write_text(json.dumps(result), encoding="utf-8")
    # 保留 tmpfs 供应用校验回传；应用崩溃时也不会永久留下运行容器。
    time.sleep(120)


if __name__ == "__main__":
    main()
