from types import SimpleNamespace

from app.modules.coding.service import CodingWorkspace


def make_workspace(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    paths = SimpleNamespace(workspace=tmp_path, data=data)
    repository = SimpleNamespace(project_id="p1", workspace_id="p1")
    return CodingWorkspace(paths, repository)


def test_sdk_style_project_uses_dotnet_build(tmp_path):
    (tmp_path / "App.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n<PropertyGroup>'
        "<TargetFramework>net8.0</TargetFramework></PropertyGroup>\n</Project>",
        encoding="utf-8",
    )
    assert make_workspace(tmp_path)._build_command() == 'dotnet build "App.csproj"'


def test_nested_sdk_project_is_discovered(tmp_path):
    project = tmp_path / "src" / "App"
    project.mkdir(parents=True)
    (project / "App.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n<PropertyGroup>'
        "<TargetFramework>net8.0</TargetFramework></PropertyGroup>\n</Project>",
        encoding="utf-8",
    )
    command = make_workspace(tmp_path)._build_command()
    assert command == 'dotnet build "src/App/App.csproj"'


def test_legacy_framework_project_uses_msbuild(tmp_path, monkeypatch):
    (tmp_path / "Legacy.csproj").write_text(
        '<Project ToolsVersion="15.0">\n<PropertyGroup>'
        "<TargetFrameworkVersion>v4.8</TargetFrameworkVersion></PropertyGroup>\n</Project>",
        encoding="utf-8",
    )
    (tmp_path / "Legacy.sln").write_text("Microsoft Visual Studio Solution File", encoding="utf-8")
    workspace = make_workspace(tmp_path)
    monkeypatch.setattr(workspace, "_msbuild_path", lambda: r"D:\VS\MSBuild.exe")
    command = workspace._build_command()
    assert r"D:\VS\MSBuild.exe" in command
    assert "Legacy.sln" in command
    assert "/p:Configuration=Debug" in command


def test_legacy_test_command_is_not_guessed(tmp_path):
    (tmp_path / "Legacy.csproj").write_text(
        "<Project><PropertyGroup><TargetFrameworkVersion>v4.8</TargetFrameworkVersion></PropertyGroup></Project>",
        encoding="utf-8",
    )
    assert make_workspace(tmp_path)._default_test_command() == ""


def test_check_app_rejects_paths_outside_project(tmp_path):
    import pytest

    workspace = make_workspace(tmp_path)
    with pytest.raises(ValueError):
        workspace.check_app(r"..\evil.exe")
    with pytest.raises(ValueError):
        workspace.check_app(r"bin\Debug\missing.exe")


def test_csharp_project_takes_priority_over_node(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "App.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        "<TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>",
        encoding="utf-8",
    )
    assert make_workspace(tmp_path)._build_command() == 'dotnet build "App.csproj"'


def test_csharp_test_project_enables_dotnet_test(tmp_path):
    (tmp_path / "Demo.sln").write_text("Microsoft Visual Studio Solution File", encoding="utf-8")
    (tmp_path / "App.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        "<TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>",
        encoding="utf-8",
    )
    (tmp_path / "App.Tests.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        "<TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>",
        encoding="utf-8",
    )
    assert make_workspace(tmp_path)._default_test_command() == 'dotnet test "Demo.sln"'


def test_multiple_projects_without_solution_build_all(tmp_path):
    for name in ("Core", "Cli"):
        (tmp_path / f"{name}.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
            "<TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>",
            encoding="utf-8",
        )
    command = make_workspace(tmp_path)._build_command()
    assert "Core.csproj" in command and "Cli.csproj" in command
    assert "foreach" in command


def test_compile_check_filters_diagnostics_by_file(tmp_path, monkeypatch):
    (tmp_path / "App.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        "<TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>",
        encoding="utf-8",
    )
    workspace = make_workspace(tmp_path)
    monkeypatch.setattr(
        workspace,
        "verify",
        lambda kind, timeout=None: {
            "ok": False,
            "command": "dotnet build",
            "summary": "1 error",
            "errors": [
                {"file": "A.cs", "line": 1, "code": "CS1", "message": "a"},
                {"file": "B.cs", "line": 2, "code": "CS2", "message": "b"},
            ],
            "warnings": [],
        },
    )
    result = workspace.compile_check("A.cs")
    assert [item["file"] for item in result["errors"]] == ["A.cs"]
    assert result["ok"] is False


def test_compile_check_requires_csharp_project(tmp_path):
    workspace = make_workspace(tmp_path)
    result = workspace.compile_check()
    assert result["ok"] is False
    assert "没有 C# 工程" in result["error"]


def test_compile_check_caches_until_sources_change(tmp_path, monkeypatch):
    (tmp_path / "App.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        "<TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>",
        encoding="utf-8",
    )
    source = tmp_path / "A.cs"
    source.write_text("public class A { }\n", encoding="utf-8")
    workspace = make_workspace(tmp_path)
    calls = []

    def fake_verify(kind, timeout=None):
        calls.append(1)
        return {
            "ok": True,
            "command": "dotnet build",
            "summary": "ok",
            "errors": [],
            "warnings": [],
        }

    monkeypatch.setattr(workspace, "verify", fake_verify)
    first = workspace.compile_check()
    second = workspace.compile_check()
    assert len(calls) == 1
    assert second.get("cached") is True
    assert first["ok"] is True

    source.write_text("public class A { public int X; }\n", encoding="utf-8")
    third = workspace.compile_check()
    assert len(calls) == 2
    assert third.get("cached") is None
