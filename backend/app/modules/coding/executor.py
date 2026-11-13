"""项目内命令执行：审批策略、超时、进程树、实时输出和后台任务。"""

import codecs
import json
import os
import queue
import re
import subprocess
import threading
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
    r"^(dotnet\s+(build|test|restore|run|publish|new|add|sln|nuget|format|watch|ef|--info|--version|--list-sdks)|msbuild)\b",
    r"^(npm\s+(test|run|ci)|npx\s+(tsc|eslint|prettier)|node\s+--version)\b",
    r"^(pnpm|yarn)\s+(test|run|build|lint)\b",
    r"^(cargo\s+(build|test|check|run|fmt|clippy)|go\s+(build|test|run|vet|fmt)|mvn\s+(test|package|compile)|gradle\w*\s+(test|build))\b",
    r"^(make|cmake|ninja)\b",
    r"^(python|py)\s+(-m\s+)?(pytest|unittest)",
    r"^pytest\b",
    r"^(pip|pip3)\s+(list|show)\b",
    r"^(uv|poetry)\s+(run|test)\b",
    r"^(ruff|black|mypy|eslint|prettier)\b",
    r"^(java|javac|composer|php|ruby)\s",
    r"^(where|which)\s+",
]
DANGEROUS = [
    r"\b(format|diskpart|shutdown|cipher\s+/w)\b",
    r"\b(Clear-Disk|Initialize-Disk|Remove-Partition|Set-Partition)\b",
    r"\b(rm|del|rmdir)\b.*(\s/[sf]|\s-rf|\s-fr)\b",
    r"\bgit\s+(clean\s+-[a-z]*f|reset\s+--hard)\b",
    r"\breg\s+(add|delete)\b",
    r"\b(sc|schtasks|net\s+user)\b",
    r"(-EncodedCommand|Invoke-Expression|\|\s*(bash|sh|powershell|pwsh)\b)",
]
# 这些命令会改动文件；绝对路径在项目外、使用环境变量或 .. 时直接拒绝。
DESTRUCTIVE = re.compile(
    r"\b(Remove-Item|Remove-ItemProperty|ri|rd|rmdir|del|erase|Clear-Content|"
    r"Set-Content|Add-Content|Out-File|Move-Item|mv|ren|rename|Copy-Item|New-Item|mkdir|md)\b",
    re.IGNORECASE,
)
ABSOLUTE_PATH = re.compile(r'(?:[A-Za-z]:[\\/]|\\\\)[^\s"\'|;<>)]*')
ENVIRONMENT_PATH = re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%|\$env:", re.IGNORECASE)
PARENT_PATH = re.compile(r'(^|[\s"\'=])\.\.[\\/]')


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
        self._running = {}
        self.jobs_path = self.logs / "jobs.json"
        self.history = self._load_history()

    # ---------- 策略 ----------
    def classify(self, command):
        text = command.strip()
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in DANGEROUS):
            return "dangerous"
        if self._escapes_project(text):
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

    def _escapes_project(self, text):
        """文件类命令引用项目外路径、环境变量或 .. 时按危险命令处理。"""
        if not DESTRUCTIVE.search(text):
            return False
        if ENVIRONMENT_PATH.search(text) or PARENT_PATH.search(text):
            return True
        for raw in ABSOLUTE_PATH.findall(text):
            candidate = raw.strip("\"'")
            try:
                target = Path(candidate).resolve()
            except (OSError, ValueError):
                return True
            if target != self.root and not target.is_relative_to(self.root):
                return True
        return False

    # ---------- 前台 ----------
    def run(
        self,
        command,
        cwd=".",
        timeout=DEFAULT_TIMEOUT,
        approved=False,
        *,
        on_output=None,
        cancel=None,
        run_id="",
    ):
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
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                self._shell(command),
            ],
            cwd=str(workdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creation,
            env=self._environment(),
        )
        key = run_id or job_id
        self._running[key] = process
        chunks = queue.Queue()

        def reader():
            try:
                while True:
                    data = process.stdout.read1(4096)
                    if not data:
                        break
                    chunks.put(data)
            except (OSError, ValueError):
                pass
            finally:
                chunks.put(None)

        threading.Thread(target=reader, name=f"coding-read-{job_id}", daemon=True).start()
        deadline = started + max(5, min(int(timeout), 900))
        timed_out = cancelled = False
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        collected = []
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("wb") as stream:
            while True:
                if cancel is not None and cancel.is_set():
                    cancelled = True
                    self._kill(process.pid)
                    break
                remaining = deadline - time.time()
                if remaining <= 0:
                    timed_out = True
                    self._kill(process.pid)
                    break
                try:
                    data = chunks.get(timeout=min(0.25, max(0.01, remaining)))
                except queue.Empty:
                    continue
                if data is None:
                    break
                stream.write(data)
                stream.flush()
                text = decoder.decode(data)
                if not text:
                    continue
                collected.append(text)
                if on_output is not None:
                    try:
                        on_output(text)
                    except Exception:
                        # 输出推送失败不能影响命令本身。
                        pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        tail = decoder.decode(b"", final=True)
        if tail:
            collected.append(tail)
        try:
            process.stdout.close()
        except (OSError, ValueError):
            pass
        self._running.pop(key, None)
        text = "".join(collected)[-MAX_OUTPUT:]
        code = process.returncode
        if timed_out or cancelled:
            code = -1
        return {
            "command": command,
            "cwd": str(workdir.relative_to(self.root)) or ".",
            "exit_code": code,
            "timed_out": timed_out,
            "cancelled": cancelled,
            "duration_ms": int((time.time() - started) * 1000),
            "output": text,
            "log": str(log),
            "job_id": job_id,
        }

    # ---------- 后台 ----------
    def start(self, command, cwd=".", approved=False, *, run_id="", thread_id=""):
        command = (command or "").strip()
        if not command:
            raise ValueError("命令不能为空")
        if not approved and not self.allowed(command):
            raise ApprovalRequired(
                command, cwd or ".", DEFAULT_TIMEOUT, f"命令需要用户确认：{command}"
            )
        self.reap()
        if len(self._jobs) >= MAX_BACKGROUND:
            raise ValueError("后台任务数量已达上限，请先停止部分任务")
        workdir = self._workdir(cwd)
        job_id = uuid.uuid4().hex[:12]
        log = self.logs / f"{job_id}.log"
        stream = log.open("wb")
        process = subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                self._shell(command),
            ],
            cwd=str(workdir),
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            env=self._environment(),
        )
        self._jobs[job_id] = {
            "process": process,
            "stream": stream,
            "log": log,
            "command": command,
            "run_id": run_id,
            "thread_id": thread_id,
            "started_at": time.time(),
        }
        self._persist()
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
        self._history(job_id, "stopped", job=job)
        return {"job_id": job_id, "stopped": True}

    def list_jobs(self, limit=30):
        with self._lock:
            rows = [
                {
                    "job_id": job_id,
                    "command": job["command"],
                    "pid": job["process"].pid,
                    "status": "running",
                    "thread_id": job.get("thread_id", ""),
                    "run_id": job.get("run_id", ""),
                    "started_at": job.get("started_at"),
                }
                for job_id, job in self._jobs.items()
            ]
            rows += list(reversed(self.history))[: max(1, min(limit, 100))]
            return rows[: max(1, min(limit, 100))]

    def _history(self, job_id, status, *, job=None, exit_code=None):
        row = {
            "job_id": job_id,
            "command": (job or {}).get("command", ""),
            "status": status,
            "thread_id": (job or {}).get("thread_id", ""),
            "run_id": (job or {}).get("run_id", ""),
            "started_at": (job or {}).get("started_at"),
            "exit_code": exit_code,
        }
        self.history.append(row)
        self.history = self.history[-50:]
        self._persist()

    def _persist(self):
        with self._lock:
            rows = [
                {
                    "job_id": job_id,
                    "command": job["command"],
                    "pid": job["process"].pid,
                    "status": "running",
                    "thread_id": job.get("thread_id", ""),
                    "run_id": job.get("run_id", ""),
                    "started_at": job.get("started_at"),
                }
                for job_id, job in self._jobs.items()
            ]
            rows += self.history[-50:]
            try:
                self.jobs_path.write_text(
                    json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except OSError:
                pass

    def _load_history(self):
        if not self.jobs_path.exists():
            return []
        try:
            rows = json.loads(self.jobs_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        history = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            if row.get("status") == "running":
                row = {**row, "status": "interrupted", "exit_code": None}
            history.append(row)
        return history[-50:]

    def stop_thread(self, thread_id):
        for job_id, job in list(self._jobs.items()):
            if job.get("thread_id") == thread_id:
                try:
                    self.stop(job_id)
                except (OSError, ValueError):
                    pass

    def reap(self):
        """回收已经自然退出的后台任务，避免占满并发额度。"""
        for job_id, job in list(self._jobs.items()):
            if job["process"].poll() is not None:
                try:
                    job["stream"].close()
                except OSError:
                    pass
                self._jobs.pop(job_id, None)
                self._history(job_id, "exited", job=job, exit_code=job["process"].returncode)

    def cancel(self, run_id):
        process = self._running.get(run_id)
        if process is not None and process.poll() is None:
            self._kill(process.pid)

    def stop_all(self):
        for process in list(self._running.values()):
            if process.poll() is None:
                try:
                    self._kill(process.pid)
                except OSError:
                    pass
        for job_id in list(self._jobs):
            try:
                self.stop(job_id)
            except (OSError, ValueError):
                pass

    # ---------- 辅助 ----------
    def _shell(self, command):
        # 统一控制台输出编码，并让 Get-Content 按 UTF-8 读取源码，避免中文乱码。
        return (
            "$PSDefaultParameterValues['Get-Content:Encoding']='UTF8'; "
            "$OutputEncoding=[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + command
        )

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
