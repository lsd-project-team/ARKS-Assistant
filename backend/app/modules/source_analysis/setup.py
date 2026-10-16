"""显式安装阶段准备分析器，正常问答不下载 SDK 或执行业务项目。"""

import subprocess
import urllib.request

from app.core.config import PROJECT_ROOT
from app.modules.source_analysis.csharp import DOTNET


def main():
    folder = PROJECT_ROOT / ".tools"
    folder.mkdir(exist_ok=True)
    if not DOTNET.is_file():
        installer = folder / "dotnet-install.ps1"
        with urllib.request.urlopen("https://dot.net/v1/dotnet-install.ps1", timeout=60) as source:
            installer.write_bytes(source.read())
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(installer),
                "-Version",
                "8.0.425",
                "-InstallDir",
                str(DOTNET.parent),
            ],
            check=True,
        )
    subprocess.run(
        [
            str(DOTNET),
            "build",
            str(PROJECT_ROOT / "backend/tools/SourceAnalysis/SourceAnalysis.csproj"),
            "-c",
            "Release",
            "--nologo",
        ],
        check=True,
        env={**__import__("os").environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1"},
    )
    print("Roslyn 分析器已准备；业务源码不会参与此构建。")


if __name__ == "__main__":
    main()
