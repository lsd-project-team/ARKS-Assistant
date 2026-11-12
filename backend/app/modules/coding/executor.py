"""项目内命令执行：审批策略、超时、进程树、输出截断和后台任务。"""

import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from threading import RLock

MAX_OUTPUT = 24_000
DEFAULT_TIMEOUT = 120
MAX_BACKGROUND = 5

ALLOW = [
    r"^(ls|dir|pwd|cd|cat|type|head|tail|rg|grep|findstr)\b",
    r"^git\s+(status|diff|log|show|rev-parse)\b",
    r"^(dotnet\s+(build|test|restore|run|publish|--info|--version|--list-sdks)|msbuild)\b",
    r"^(npm\s+(test|run|ci)|npx\s+tsc|node\s+--version)\b",
    r"^(python|py)\s+(-m\s+)?(pytest|unittest)",
    r"^(pip|pip3)\s+(list|show)\b",
    r"^(where|which)\s+",
]
DANGEROUS = [
    r"\b(format|diskpart|shutdown|cipher\s+/w)\b",
    r"\b(rm|del|rmdir)\b.*(\s/[sf]|\s-rf|\s-fr)\b",
    r"\bgit\s+(clean\s+-[a-z]*f|reset\s+--hard)\b",
    r"\breg\s+(add|delete)\b",
    r"\b(sc|schtasks|net\s+user)\b",
    r"(-EncodedCommand|Invoke-Expression|\|\s*(bash|sh|powershell|pwsh)\b)",
]


class ApprovalRequired(Exception):
    """命令不在自动放行范围，需要用户确认。"""

    def __init__(self, command, cwd, timeout, message):
        super().__init__(message)
        self.command = command
        self.cwd = cwd
        self.timeout = timeout


class Executor:
    def __init__(self, root, logs, mode="allowlist"):
        self.root = Path(root).resolve()
        self.logs = Path(logs)
        self.logs.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self._lock = RLock()
        self._jobs = {}

    # ---------- 策略 ----------
    def classify(self, command):
        text = command.strip()
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in DANGEROUS):
            return "dangerous"
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in ALLOW):
            return "safe"
        return "unknown"

    def allowed(self, command):
        if self.mode == "full":
            return self.classify(command) != "dangerous"
        if self.mode == "confirm":
            return False
        return self.classify(command) == "safe"

    # ---------- 前台 ----------
    def run(self, command, cwd=".", timeout=DEFAULT_TIMEOUT, approved=False):
        command = (command or "").strip()
        if not command:
            raise ValueError("命令不能为空")
        if not approved and not self.allowed(command):
            kind = self.classify(command)
            raise ApprovalRequired(
                command, cwd or ".", timeout, f"命令需要用户确认（{kind}）：{command}"
            )
        workdir = self._workdir(cwd)
        job_id = uuid.uuid4().hex[:12]
        log = self.logs / f"{job_id}.log"
        started = time.time()
        creation = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            cwd=str(workdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creation,
            env=self._environment(),
        )
        try:
            output, _ = process.communicate(timeout=max(5, min(int(timeout), 900)))
            code = process.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            self._kill(process.pid)
            output, _ = process.communicate()
            code, timed_out = -1, True
        text = output.decode("utf-8", "replace")
        log.write_text(text, encoding="utf-8")
        return {
            "command": command,
            "cwd": str(workdir.relative_to(self.root)) or ".",
            "exit_code": code,
            "timed_out": timed_out,
            "duration_ms": int((time.time() - started) * 1000),
            "output": text[-MAX_OUTPUT:],
            "log": str(log),
            "job_id": job_id,
        }

    # ---------- 后台 ----------
    def start(self, command, cwd=".", approved=False):
        command = (command or "").strip()
        if not command:
            raise ValueError("命令不能为空")
        if not approved and not self.allowed(command):
            raise ApprovalRequired(
                command, cwd or ".", DEFAULT_TIMEOUT, f"命令需要用户确认：{command}"
            )
        if len(self._jobs) >= MAX_BACKGROUND:
            raise ValueError("后台任务数量已达上限，请先停止部分任务")
        workdir = self._workdir(cwd)
        job_id = uuid.uuid4().hex[:12]
        log = self.logs / f"{job_id}.log"
        stream = log.open("wb")
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            cwd=str(workdir),
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            env=self._environment(),
        )
        self._jobs[job_id] = {"process": process, "stream": stream, "log": log, "command": command}
        return {"job_id": job_id, "pid": process.pid, "command": command, "log": str(log)}

    def read(self, job_id, lines=80):
        job = self._jobs.get(job_id)
        if not job:
            raise FileNotFoundError("后台任务不存在或已结束")
        text = job["log"].read_text(encoding="utf-8", errors="replace")
        return {
            "job_id": job_id,
            "running": job["process"].poll() is None,
            "exit_code": job["process"].poll(),
            "output": "\n".join(text.splitlines()[-max(1, min(lines, 1000)) :]),
        }

    def stop(self, job_id):
        job = self._jobs.pop(job_id, None)
        if not job:
            raise FileNotFoundError("后台任务不存在或已结束")
        if job["process"].poll() is None:
            self._kill(job["process"].pid)
        try:
            job["stream"].close()
        except OSError:
            pass
        return {"job_id": job_id, "stopped": True}

    def stop_all(self):
        for job_id in list(self._jobs):
            try:
                self.stop(job_id)
            except (OSError, ValueError):
                pass

    # ---------- 辅助 ----------
    def _workdir(self, cwd):
        relative = (cwd or ".").replace("\\", "/")
        if Path(relative).is_absolute():
            raise ValueError("cwd 必须是项目内相对路径")
        target = (self.root / relative).resolve()
        if target != self.root and not target.is_relative_to(self.root):
            raise ValueError("cwd 超出项目目录")
        if not target.is_dir():
            raise ValueError("cwd 不是已存在的目录")
        return target

    def _environment(self):
        keep = (
            "SystemRoot",
            "PATH",
            "PATHEXT",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "USERNAME",
            "APPDATA",
            "LOCALAPPDATA",
            "ProgramData",
            "ProgramFiles",
            "ProgramFiles(x86)",
            "HOMEDRIVE",
            "HOMEPATH",
            "COMSPEC",
        )
        env = {key: os.environ[key] for key in keep if key in os.environ}
        env.update(
            {
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                "DOTNET_CLI_UI_LANGUAGE": "en",
                "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
            }
        )
        return env

    def _kill(self, pid):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            try:
                os.killpg(os.getpgid(pid), 9)
            except OSError:
                pass
