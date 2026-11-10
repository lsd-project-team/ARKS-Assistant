"""管理员指定可信本机 Simulation 工程；普通对话不能提交执行命令。"""

import os
import shutil
import subprocess
from pathlib import Path
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field

from app.modules.code_work.files import PROJECT, read_json, save_json

_lock = RLock()


class EnvironmentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_root: str = Field(default="", max_length=1024)
    msbuild: str = Field(default="", max_length=1024)
    timeout_seconds: int = Field(default=300, ge=30, le=900)
    version: str = ""


class CodeEnvironment:
    def __init__(self, data):
        self.path = Path(data) / "code-work.local.json"

    def load(self):
        value = read_json(self.path) if self.path.exists() else {}
        return EnvironmentWrite.model_validate(value)

    def version(self):
        from app.infrastructure.storage.files import digest

        return digest(self.path.read_bytes() if self.path.exists() else b"")

    def public(self):
        return {**self.load().model_dump(), "version": self.version(), "windows": os.name == "nt"}

    def save(self, body):
        with _lock:
            if body.version != self.version():
                raise ValueError("执行环境已更新，请刷新后重试")
            if body.source_root:
                root = Path(body.source_root).expanduser()
                if not root.is_absolute() or not root.is_dir():
                    raise ValueError("请选择包含 AKRS.ZX2200 工程的本机绝对目录")
                required = root / PROJECT / "Infrastructure/Simulation/OriginalSimulation.cs"
                if not required.is_file() or not (root / PROJECT / f"{PROJECT}.csproj").is_file():
                    raise ValueError("来源缺少原工程 Simulation 实现，请选择它的 trunk 目录")
                body.source_root = str(root.resolve())
            if body.msbuild:
                compiler = Path(body.msbuild)
                if (
                    not compiler.is_absolute()
                    or not compiler.is_file()
                    or compiler.name.lower() != "msbuild.exe"
                ):
                    raise ValueError("MSBuild 必须是本机 MSBuild.exe 的绝对路径")
                body.msbuild = str(compiler.resolve())
            save_json(self.path, body.model_dump(exclude={"version"}))
            return self.public()

    def compiler(self):
        config = self.load()
        if os.name != "nt":
            raise ValueError("此执行环境需要 Windows 与 .NET Framework 4.8")
        if config.msbuild:
            return config.msbuild
        if compiler := shutil.which("MSBuild.exe"):
            return compiler
        finder = (
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
            / "Microsoft Visual Studio/Installer/vswhere.exe"
        )
        if finder.is_file():
            result = subprocess.run(
                [str(finder), "-latest", "-products", "*", "-find", "MSBuild/**/Bin/MSBuild.exe"],
                capture_output=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            candidates = result.stdout.decode("utf-8-sig", errors="replace").splitlines()
            if candidates and Path(candidates[0]).is_file():
                return candidates[0]
        raise ValueError("未找到 MSBuild.exe，请由管理员配置")
