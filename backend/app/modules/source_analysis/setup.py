"""显式安装阶段准备分析器，正常问答不下载 SDK 或执行业务项目。"""

import argparse
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from app.core.config import PROJECT_ROOT
from app.modules.source_analysis.dotnet_runtime import (
    SDK_VERSION,
    bundled_dotnet,
    dotnet_environment,
    find_dotnet,
)


def installed_sdks(program):
    result = subprocess.run(
        [str(program), "--list-sdks"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=dotnet_environment(program),
    )
    return re.findall(r"(?m)^(8\.0\.\d+)\s+\[", result.stdout)


def install_sdk(root, system):
    folder = root / ".tools"
    folder.mkdir(exist_ok=True)
    windows = system == "Windows"
    filename = "dotnet-install.ps1" if windows else "dotnet-install.sh"
    installer, program = folder / filename, bundled_dotnet(root, system=system)
    with urllib.request.urlopen("https://dot.net/v1/" + filename, timeout=60) as source:
        content = source.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise ValueError("官方安装脚本超过预期大小，未执行")
    installer.write_bytes(content)
    arguments = (
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(installer),
            "-Version",
            SDK_VERSION,
            "-InstallDir",
            str(program.parent),
            "-NoPath",
        ]
        if windows
        else [
            "bash",
            str(installer),
            "--version",
            SDK_VERSION,
            "--install-dir",
            str(program.parent),
            "--no-path",
        ]
    )
    subprocess.run(arguments, check=True, timeout=900)
    if not program.is_file() or SDK_VERSION not in installed_sdks(program):
        raise ValueError("安装未产生预期的固定 .NET 8 SDK，未构建分析器")
    return program, SDK_VERSION


def build_helper(program, version, root):
    helper = root / "backend/tools/SourceAnalysis/SourceAnalysis.csproj"
    folder = root / ".tools"
    folder.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="roslyn-setup-", dir=folder) as temporary:
        temporary = Path(temporary)
        (temporary / "global.json").write_text(
            json.dumps(
                {"sdk": {"version": version, "rollForward": "disable", "allowPrerelease": False}}
            ),
            encoding="utf-8",
        )
        packages = temporary / "packages"
        packages.mkdir()
        # 仅构建应用自带helper；清空包源，不让准备阶段还原业务工程或私有包。
        subprocess.run(
            [
                str(program),
                "build",
                str(helper),
                "-c",
                "Release",
                "--nologo",
                "-p:NuGetAudit=false",
                "-p:RestoreSources=" + str(packages),
            ],
            check=True,
            timeout=180,
            cwd=temporary,
            env=dotnet_environment(program),
        )
    output = helper.parent / "bin/Release/net8.0/SourceAnalysis.dll"
    if not output.is_file():
        raise ValueError("helper构建未产生预期程序集，尚不能用于语义分析")
    return {"dotnet": str(program), "sdk_version": version, "project": str(helper)}


def prepare(*, allow_download=True, root=PROJECT_ROOT, system=None):
    import platform

    root, system = Path(root), system or platform.system()
    if not (root / "backend/tools/SourceAnalysis/SourceAnalysis.csproj").is_file():
        raise ValueError("应用自带的 SourceAnalysis.csproj 不存在，未安装SDK或执行构建")
    program = find_dotnet(root=root, system=system)
    versions = installed_sdks(program) if program else []
    if versions:
        # 保留既有8.x SDK，不因准备helper隐式升级系统或原有本地SDK。
        version = max(versions, key=lambda value: tuple(map(int, value.split("."))))
    else:
        if not allow_download:
            raise ValueError("离线准备缺少 .NET 8 SDK；请预装SDK或显式移除 --no-download 后重试")
        if os.environ.get("ARKS_DOTNET_PATH"):
            raise ValueError("ARKS_DOTNET_PATH 中未找到 .NET 8 SDK；请选择含SDK的主机或取消该配置")
        program, version = install_sdk(root, system)
    return build_helper(program, version, root)


def main():
    parser = argparse.ArgumentParser(description="显式准备应用自带的 Roslyn 分析器")
    parser.add_argument("--no-download", action="store_true", help="只用现有 .NET 8 SDK，禁止下载")
    arguments = parser.parse_args()
    try:
        result = prepare(allow_download=not arguments.no_download)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Roslyn 准备失败：{error}\n")
    print(f"Roslyn 分析器已准备（SDK {result['sdk_version']}）；业务源码未参与构建。")


if __name__ == "__main__":
    main()
