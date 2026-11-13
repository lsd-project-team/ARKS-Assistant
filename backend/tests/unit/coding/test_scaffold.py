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
    assert "EnableDefaultCompileItems" in project


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
