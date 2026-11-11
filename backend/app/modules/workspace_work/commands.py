"""受控命令执行：白名单、超时、输出上限和进程树终止；不拼接 shell。"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

MAX_OUTPUT_BYTES = 4_000_000
TAIL_CHARS = 200_000


class CommandDenied(ValueError):
    """命令未命中白名单。"""


def matched_rule(argv, rules):
    if not isinstance(argv, list) or not 1 <= len(argv) <= 32:
        raise ValueError("命令必须是非空参数数组")
    if any(not isinstance(item, str) or not item or len(item) > 2_000 for item in argv):
        raise ValueError("命令参数必须是长度有限的字符串")
    name = Path(argv[0]).name.lower()
    for rule in rules:
        if not rule or Path(rule[0]).name.lower() != name:
            continue
        prefix = [item.lower() for item in rule[1:]]
        actual = [item.lower() for item in argv[1 : len(rule)]]
        if actual == prefix:
            return rule
    return None


def executable(argv):
    found = shutil.which(argv[0]) or shutil.which(argv[0] + ".exe")
    if not found:
        raise ValueError(f"找不到可执行程序：{argv[0]}")
    return found


def stop(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        process.kill()
    process.wait(timeout=15)


def run(argv, cwd, timeout, *, max_bytes=MAX_OUTPUT_BYTES):
    """在新进程组执行一条已授权命令，返回退出码、输出和终止原因。"""
    cwd = Path(cwd).resolve()
    if not cwd.is_dir():
        raise ValueError("命令工作目录不存在")
    executable(argv)
    descriptor, name = tempfile.mkstemp(prefix="ww-cmd-", suffix=".log")
    log = Path(name)
    timed_out = truncated = False
    try:
        with os.fdopen(descriptor, "wb") as stream:
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=stream,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                shell=False,
            )
            deadline = time.monotonic() + timeout
            try:
                while process.poll() is None:
                    if time.monotonic() >= deadline:
                        timed_out = True
                        break
                    if log.stat().st_size > max_bytes:
                        truncated = True
                        break
                    time.sleep(0.1)
            finally:
                stop(process)
            exit_code = process.returncode
        text = _decode(log.read_bytes())
        if len(text) > TAIL_CHARS:
            text = "（仅显示输出末尾）\n" + text[-TAIL_CHARS:]
            truncated = True
        return {
            "exit_code": exit_code,
            "output": text,
            "timed_out": timed_out,
            "truncated": truncated,
            "timeout_seconds": timeout,
        }
    finally:
        log.unlink(missing_ok=True)


def _decode(data):
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("gb18030", errors="replace")
