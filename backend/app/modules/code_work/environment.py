"""按项目保存可信本机源码与编译环境；普通对话不能提交执行命令。"""

import os
import shutil
import subprocess
from pathlib import Path
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field

from app.modules.code_work.files import main_project, read_json, save_json

_lock = RLock()
FILE_NAME = "code-work.local.json"


class EnvironmentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_root: str = Field(default="", max_length=1024)
    msbuild: str = Field(default="", max_length=1024)
    timeout_seconds: int = Field(default=300, ge=30, le=900)
    version: str = ""


class ProjectProfile(EnvironmentWrite):
    project: str = Field(default="", max_length=200)


def migrate_legacy(data, project_id):
    """旧版只有一份全局执行环境；升级时归到默认项目，其他项目不继承。"""
    path = Path(data) / FILE_NAME
    if not path.exists() or not project_id:
        return
    raw = read_json(path)
    if not isinstance(raw, dict) or "projects" in raw:
        return
    entry = {key: raw[key] for key in ("source_root", "msbuild", "timeout_seconds") if key in raw}
    if entry.get("source_root"):
        save_json(path, {"projects": {project_id: entry}})


class CodeEnvironment:
    def __init__(self, data, project_id=None):
        self.path = Path(data) / FILE_NAME
        self.project_id = project_id or "default"

    def _projects(self):
        if not self.path.exists():
            return {}
        raw = read_json(self.path)
        if not isinstance(raw, dict):
            return {}
        projects = raw.get("projects")
        return projects if isinstance(projects, dict) else {}

    def load(self):
        value = ProjectProfile.model_validate(self._projects().get(self.project_id) or {})
        if not value.project and value.source_root:
            try:
                value.project = main_project(value.source_root)
            except (OSError, ValueError):
                value.project = ""
        return value

    def version(self):
        from app.infrastructure.storage.files import digest

        return digest(self.path.read_bytes() if self.path.exists() else b"")

    def public(self):
        return {
            **self.load().model_dump(),
            "version": self.version(),
            "windows": os.name == "nt",
        }

    def save(self, body):
        with _lock:
            if body.version != self.version():
                raise ValueError("执行环境已更新，请刷新后重试")
            source, project = "", ""
            if body.source_root:
                root = Path(body.source_root).expanduser()
                if not root.is_absolute() or not root.is_dir():
                    raise ValueError("请填写本机已存在的绝对源码目录")
                # 主工程按目录结构识别，不再要求某个固定项目名。
                project = main_project(root)
                source = str(root.resolve())
            variant = body.msbuild
            if variant:
                compiler = Path(variant)
                if (
                    not compiler.is_absolute()
                    or not compiler.is_file()
                    or compiler.name.lower() != "msbuild.exe"
                ):
                    raise ValueError("MSBuild 必须是本机 MSBuild.exe 的绝对路径")
                variant = str(compiler.resolve())
            entry = {
                "source_root": source,
                "project": project,
                "msbuild": variant,
                "timeout_seconds": body.timeout_seconds,
            }
            projects = dict(self._projects())
            projects[self.project_id] = entry
            save_json(self.path, {"projects": projects})
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
