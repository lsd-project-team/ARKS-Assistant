"""发现已有的分析器运行时；正常源码请求不安装 SDK 或构建任何工程。"""

import os
import platform
import shutil
from pathlib import Path

from app.core.config import PROJECT_ROOT

SDK_VERSION = "8.0.426"
HELPER = PROJECT_ROOT / "backend/tools/SourceAnalysis/bin/Release/net8.0/SourceAnalysis.dll"


def executable_name(system=None):
    return "dotnet.exe" if (system or platform.system()) == "Windows" else "dotnet"


def bundled_dotnet(root=PROJECT_ROOT, *, system=None):
    return Path(root) / ".tools" / "dotnet" / executable_name(system)


DOTNET = bundled_dotnet()


def _program(path, system):
    return path.is_file() and (system == "Windows" or os.access(path, os.X_OK))


def find_dotnet(*, root=PROJECT_ROOT, system=None):
    system = system or platform.system()
    if configured := os.environ.get("ARKS_DOTNET_PATH"):
        path = Path(configured).expanduser()
        if not path.is_absolute() or not _program(path, system):
            raise ValueError("ARKS_DOTNET_PATH 必须是当前平台可执行的 dotnet 绝对文件路径")
        return path.resolve()
    candidates = [bundled_dotnet(root, system=system)]
    if directory := os.environ.get("DOTNET_ROOT"):
        candidates.append(Path(directory).expanduser() / executable_name(system))
    if program := shutil.which(executable_name(system)):
        candidates.append(Path(program))
    return next((path.resolve() for path in candidates if _program(path, system)), None)


def helper_path(default=HELPER):
    path = Path(os.environ.get("ARKS_ROSLYN_HELPER", str(default))).expanduser()
    if not path.is_absolute():
        raise ValueError("ARKS_ROSLYN_HELPER 必须是预构建分析器的绝对文件路径")
    return path


def setup_instruction():
    return (
        "在 backend 目录显式运行 python -m app.modules.source_analysis.setup；离线加 --no-download"
    )


def roslyn_command(*, default_dotnet=None, default_helper=HELPER):
    try:
        # 保留原有受控注入点；显式环境配置仍拥有最高优先级。
        dotnet = (
            Path(default_dotnet)
            if default_dotnet is not None and not os.environ.get("ARKS_DOTNET_PATH")
            else find_dotnet()
        )
        helper = helper_path(default_helper)
    except ValueError as error:
        return None, str(error)
    if dotnet is None or not dotnet.is_file():
        return None, "未找到 .NET 8 分析运行时；" + setup_instruction()
    if not helper.is_file():
        return None, "未找到预构建 Roslyn 分析器；" + setup_instruction()
    return [str(dotnet), str(helper)], ""


def dotnet_environment(dotnet):
    return {
        **os.environ,
        "DOTNET_ROOT": str(Path(dotnet).parent),
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE": "true",
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_NOLOGO": "1",
    }
