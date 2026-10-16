"""跨平台发现与显式准备；临时文件真实，下载与 SDK CLI 是外部依赖替身。"""

import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.modules.source_analysis import csharp, dotnet_runtime, setup
from app.modules.source_analysis.csharp import CSharpAnalysis
from app.modules.source_analysis.dotnet_runtime import (
    SDK_VERSION,
    bundled_dotnet,
    find_dotnet,
    roslyn_command,
)
from app.modules.source_analysis.workspace import Workspace


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch):
    for name in ("ARKS_DOTNET_PATH", "ARKS_ROSLYN_HELPER", "DOTNET_ROOT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(dotnet_runtime.shutil, "which", lambda _: None)


def executable(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"test executable placeholder")
    path.chmod(0o755)
    return path


@pytest.mark.parametrize(
    "system,name", [("Windows", "dotnet.exe"), ("Linux", "dotnet"), ("Darwin", "dotnet")]
)
def test_bundled_executable_matches_platform_instead_of_windows_only(tmp_path, system, name):
    expected = executable(tmp_path / ".tools" / "dotnet" / name)
    assert bundled_dotnet(tmp_path, system=system) == expected
    assert find_dotnet(root=tmp_path, system=system) == expected.resolve()


def test_explicit_program_has_priority_and_invalid_config_never_falls_back(tmp_path, monkeypatch):
    bundled = executable(bundled_dotnet(tmp_path, system="Linux"))
    configured = executable(tmp_path / "chosen" / "dotnet")
    monkeypatch.setenv("ARKS_DOTNET_PATH", str(configured))
    assert find_dotnet(root=tmp_path, system="Linux") == configured.resolve()
    monkeypatch.setenv("ARKS_DOTNET_PATH", str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="ARKS_DOTNET_PATH"):
        find_dotnet(root=tmp_path, system="Linux")
    assert bundled.exists()


def test_dotnet_root_and_path_discovery_use_platform_executable(tmp_path, monkeypatch):
    expected = executable(tmp_path / "system-sdk" / "dotnet")
    monkeypatch.setenv("DOTNET_ROOT", str(expected.parent))
    assert find_dotnet(root=tmp_path, system="Linux") == expected.resolve()
    monkeypatch.delenv("DOTNET_ROOT")
    looked_up = []

    def find(name):
        looked_up.append(name)
        return str(expected)

    monkeypatch.setattr(dotnet_runtime.shutil, "which", find)
    assert find_dotnet(root=tmp_path, system="Linux") == expected.resolve()
    assert looked_up == ["dotnet"]


def test_prebuilt_helper_config_and_missing_toolchain_are_explicit(tmp_path, monkeypatch):
    monkeypatch.setenv("ARKS_DOTNET_PATH", sys.executable)
    helper = tmp_path / "prebuilt" / "SourceAnalysis.dll"
    helper.parent.mkdir()
    helper.write_bytes(b"prebuilt")
    monkeypatch.setenv("ARKS_ROSLYN_HELPER", str(helper))
    command, error = roslyn_command()
    assert not error and command == [str(Path(sys.executable).resolve()), str(helper)]
    monkeypatch.setenv("ARKS_ROSLYN_HELPER", "relative/SourceAnalysis.dll")
    assert "ARKS_ROSLYN_HELPER" in roslyn_command()[1]
    monkeypatch.setenv("ARKS_DOTNET_PATH", str(tmp_path / "missing"))
    assert "ARKS_DOTNET_PATH" in roslyn_command()[1]


def test_missing_runtime_returns_setup_instruction_without_download_or_build(tmp_path, monkeypatch):
    (tmp_path / "Program.cs").write_text("class Program {}\n")
    monkeypatch.setattr(csharp, "analysis_command", lambda: (None, "未找到.NET 8；显式运行 setup"))

    def forbidden(*args, **kwargs):
        pytest.fail("正常源码请求不能下载或构建SDK")

    monkeypatch.setattr(setup.urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(csharp.subprocess, "Popen", forbidden)
    index = CSharpAnalysis(Workspace(tmp_path))
    assert index.analyze("Program.cs", 1) == {
        "analysis": "unavailable",
        "reason": "未找到.NET 8；显式运行 setup",
    }


def test_dead_helper_reports_unavailable_and_syntax_uses_real_offline_fallback(
    tmp_path, monkeypatch
):
    root = tmp_path / "source"
    root.mkdir()
    (root / "Program.cs").write_text("class Program { static void Main() {} }\n")
    failed = tmp_path / "dead-helper.py"
    failed.write_text("raise SystemExit(2)\n")
    monkeypatch.setattr(csharp, "DOTNET", Path(sys.executable))
    monkeypatch.setattr(csharp, "HELPER", failed)
    index = CSharpAnalysis(Workspace(root))
    try:
        result = index.analyze("Program.cs", 1)
        assert result["analysis"] == "unavailable" and ".NET 8" in result["reason"]
        assert index.process is None
        syntax = index.workspace.symbols("Program.cs")
        assert {item["name"] for item in syntax["symbols"]} == {"Program", "Main"}
        assert syntax["syntax_engine"] == "tree_sitter"
    finally:
        index.close()


def own_project(root):
    project = root / "backend/tools/SourceAnalysis/SourceAnalysis.csproj"
    project.parent.mkdir(parents=True)
    project.write_text('<Project Sdk="Microsoft.NET.Sdk"/>')
    return project


def sdk_cli(monkeypatch, root, *, existing=None, produce_output=True):
    calls, downloads = [], []
    sdks = existing or {}

    def download(url, **kwargs):
        downloads.append(url)
        return io.BytesIO(b"# official installer test double\n")

    def run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        if arguments[-1] == "--list-sdks":
            return SimpleNamespace(
                stdout="".join(f"{version} [test-sdk]\n" for version in sdks.get(arguments[0], []))
            )
        if arguments[0] in {"bash", "powershell"}:
            suffix = "Windows" if arguments[0] == "powershell" else "Linux"
            program = executable(bundled_dotnet(root, system=suffix))
            sdks[str(program)] = [SDK_VERSION]
        elif arguments[1] == "build":
            selected = json.loads((kwargs["cwd"] / "global.json").read_text())
            assert selected["sdk"]["rollForward"] == "disable"
            assert arguments[2] == str(root / "backend/tools/SourceAnalysis/SourceAnalysis.csproj")
            assert "-p:NuGetAudit=false" in arguments
            package_source = next(
                value for value in arguments if value.startswith("-p:RestoreSources=")
            )
            assert Path(package_source.split("=", 1)[1]).is_dir()
            if produce_output:
                output = root / "backend/tools/SourceAnalysis/bin/Release/net8.0/SourceAnalysis.dll"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"compiled helper test double")
        else:
            raise AssertionError("准备命令超出已授权的SDK发现/安装/helper构建")
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(setup.urllib.request, "urlopen", download)
    monkeypatch.setattr(setup.subprocess, "run", run)
    return calls, downloads


@pytest.mark.parametrize(
    "system,script,flag",
    [("Linux", "dotnet-install.sh", "--version"), ("Windows", "dotnet-install.ps1", "-Version")],
)
def test_explicit_setup_uses_official_platform_script_fixed_sdk_and_only_own_helper(
    tmp_path, monkeypatch, system, script, flag
):
    own_project(tmp_path)
    calls, downloads = sdk_cli(monkeypatch, tmp_path)
    result = setup.prepare(root=tmp_path, system=system)
    assert result["sdk_version"] == SDK_VERSION == "8.0.426"
    assert downloads == ["https://dot.net/v1/" + script]
    install = calls[0][0]
    assert install[install.index(flag) + 1] == SDK_VERSION
    assert result["dotnet"] == str(bundled_dotnet(tmp_path, system=system))
    assert [arguments[1] for arguments, _ in calls[1:]] == ["--list-sdks", "build"]
    assert not list((tmp_path / ".tools").glob("roslyn-setup-*"))


def test_existing_sdk_425_is_reused_offline_without_automatic_upgrade(tmp_path, monkeypatch):
    own_project(tmp_path)
    program = executable(bundled_dotnet(tmp_path, system="Linux"))
    calls, downloads = sdk_cli(
        monkeypatch, tmp_path, existing={str(program): ["8.0.425", "9.0.100"]}
    )
    result = setup.prepare(root=tmp_path, system="Linux", allow_download=False)
    assert result["sdk_version"] == "8.0.425"
    assert downloads == [] and len(calls) == 2
    assert calls[1][1]["env"]["DOTNET_CLI_TELEMETRY_OPTOUT"] == "1"
    assert calls[1][1]["env"]["DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE"] == "true"


def test_offline_setup_without_sdk_never_downloads_or_builds(tmp_path, monkeypatch):
    own_project(tmp_path)
    calls, downloads = sdk_cli(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="离线准备缺少"):
        setup.prepare(root=tmp_path, system="Linux", allow_download=False)
    assert calls == downloads == []


def test_explicit_runtime_without_sdk_is_not_silently_replaced(tmp_path, monkeypatch):
    own_project(tmp_path)
    program = executable(tmp_path / "external" / "dotnet")
    monkeypatch.setenv("ARKS_DOTNET_PATH", str(program))
    calls, downloads = sdk_cli(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="ARKS_DOTNET_PATH"):
        setup.prepare(root=tmp_path, system="Linux")
    assert downloads == [] and len(calls) == 1


def test_success_exit_without_helper_artifact_is_not_reported_ready(tmp_path, monkeypatch):
    own_project(tmp_path)
    program = executable(bundled_dotnet(tmp_path, system="Linux"))
    sdk_cli(monkeypatch, tmp_path, existing={str(program): ["8.0.425"]}, produce_output=False)
    with pytest.raises(ValueError, match="未产生预期程序集"):
        setup.prepare(root=tmp_path, system="Linux", allow_download=False)


def test_build_failure_propagates_and_cleans_own_temporary_sdk_selection(tmp_path, monkeypatch):
    own_project(tmp_path)
    program = executable(bundled_dotnet(tmp_path, system="Linux"))
    calls, downloads = sdk_cli(monkeypatch, tmp_path, existing={str(program): ["8.0.425"]})
    original = setup.subprocess.run

    def failing_build(arguments, **kwargs):
        if arguments[1] == "build":
            raise subprocess.CalledProcessError(1, arguments)
        return original(arguments, **kwargs)

    monkeypatch.setattr(setup.subprocess, "run", failing_build)
    with pytest.raises(subprocess.CalledProcessError):
        setup.prepare(root=tmp_path, system="Linux", allow_download=False)
    assert downloads == [] and len(calls) == 1
    assert not list((tmp_path / ".tools").glob("roslyn-setup-*"))
