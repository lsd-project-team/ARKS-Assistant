"""WinForms 骨架：写入空目录、拒绝覆盖、占位符替换。"""

from types import SimpleNamespace

import pytest

from app.core.config import Paths
from app.modules.coding.service import CodingWorkspace


def make_workspace(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    paths = Paths(tmp_path / "data", root)
    repository = SimpleNamespace(project_id="p", workspace_id="p")
    work = CodingWorkspace(paths, repository)
    work.save_settings({"approval_mode": "full"})
    return work, root


def test_build_and_test_command_detection(tmp_path):
    work, root = make_workspace(tmp_path)
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    (root / "main.py").write_text("print('x')\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_main.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    assert work._build_command() == "python -m compileall -q ."
    assert work._default_test_command() == "python -m pytest -q"


def test_dotnet_project_commands_are_detected(tmp_path):
    work, root = make_workspace(tmp_path)
    (root / "App.csproj").write_text("<Project />", encoding="utf-8")
    assert work._build_command() == "dotnet build"
    assert work._default_test_command() == "dotnet test"


def test_deliverables_require_readme_and_files_named_in_task(tmp_path):
    work, root = make_workspace(tmp_path)
    (root / "任务书.md").write_text(
        "创建 `index.html` 与 `app.js`，并写 README。", encoding="utf-8"
    )
    missing = work.deliverables()
    assert any("README" in item for item in missing)
    assert any("index.html" in item for item in missing)
    (root / "README.md").write_text("# x", encoding="utf-8")
    (root / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "app.js").write_text("console.log(1)\n", encoding="utf-8")
    assert work.deliverables() == []
    (root / "app.js").write_text("// TODO 实现\n", encoding="utf-8")
    assert any("app.js" in item for item in work.deliverables())


def test_deliverables_split_slash_separated_names(tmp_path):
    work, root = make_workspace(tmp_path)
    (root / "README.md").write_text("# x", encoding="utf-8")
    (root / "A.cs").write_text("// a\n", encoding="utf-8")
    (root / "B.cs").write_text("// b\n", encoding="utf-8")
    (root / "任务书.md").write_text("不要改 `A.cs/B.cs`。", encoding="utf-8")
    assert work.deliverables() == []


def test_scaffold_creates_skeleton_with_replacements(tmp_path):
    work, root = make_workspace(tmp_path)
    result = work.scaffold("winforms", {"__PRODUCT__": "测试上位机"})
    assert set(result["files"]) == {
        "Actions.cs",
        "App.csproj",
        "MainForm.cs",
        "Program.cs",
        "README.md",
        "ScreenshotTool.cs",
        "UiParts.cs",
    }
    main = (root / "MainForm.cs").read_text(encoding="utf-8")
    assert "测试上位机" in main
    assert "__PRODUCT__" not in main
    assert "namespace Sp900App;" in main
    project = (root / "App.csproj").read_text(encoding="utf-8")
    assert "<Compile Include=\"MainForm.cs\" />" in project
    assert "<Compile Include=\"Actions.cs\" />" in project
    assert "EnableDefaultCompileItems" in project


def test_scaffold_protects_layout_files(tmp_path):
    work, root = make_workspace(tmp_path)
    result = work.scaffold()
    assert "MainForm.cs" in result["protected"]
    with pytest.raises(ValueError, match="受保护"):
        work.write_file("MainForm.cs", "// rewrite")
    with pytest.raises(ValueError, match="受保护"):
        work.edit_file("UiParts.cs", [{"old": "x", "new": "y"}], "hash")
    # Actions.cs 是业务入口，允许写；新文件也允许。
    work.write_file("Sp900Protocol.cs", "// 实现协议调用")
    assert (root / "Sp900Protocol.cs").is_file()


def test_scaffold_refuses_existing_source(tmp_path):
    work, root = make_workspace(tmp_path)
    (root / "Existing.cs").write_text("class Existing {}", encoding="utf-8")
    with pytest.raises(ValueError, match="已有源码"):
        work.scaffold()


def test_scaffold_refuses_second_run(tmp_path):
    work, _ = make_workspace(tmp_path)
    work.scaffold()
    with pytest.raises(ValueError, match="已有源码"):
        work.scaffold()


async def test_scaffold_tool_returns_file_list(tmp_path):
    from app.agents.tools.coding import coding_tools

    work, root = make_workspace(tmp_path)
    events = []
    tool = {item.name: item for item in coding_tools(work, "t", lambda *a: events.append(a))}[
        "scaffold_winforms"
    ]
    result = await tool.ainvoke({"product": "点胶机测试"})
    assert "App.csproj" in result and '"ok":true' in result.replace(" ", "")
    assert (root / "App.csproj").is_file()
