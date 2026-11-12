from pathlib import Path

import pytest

from app.agents.runtime.graph_builder import is_parameter_reuse_request
from app.modules.parameter_migration.mcp_server import decision_for, find_rules, load_rules


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("/参数复用 点胶压力", True),
        (" /参数复用\tDispenser.EditState", True),
        ("请问/参数复用 点胶压力", False),
        ("/参数复用说明", False),
    ],
)
def test_parameter_reuse_is_explicit_only(content, expected):
    assert is_parameter_reuse_request(content) is expected


@pytest.mark.parametrize(
    ("protection", "category", "registration", "decision"),
    [
        ("否", "配方共用", "一致", "recipe_shared"),
        ("是", "机器参数·坐标", "一致", "protected"),
        ("否", "机器参数·其他", "一致", "pending"),
        ("否", "配方共用", "新增字段-程序未登记，请一并确认", "pending"),
        ("是", "设备专属", "❌不一致：工艺=是/程序=否", "pending"),
        ("是", "机器参数·坐标", "❌程序中未找到该字段", "pending"),
    ],
)
def test_reuse_requires_more_than_a_default_protection_value(
    protection, category, registration, decision
):
    cells = ("SampleLibrary", "SampleField", protection, category, "示例", "", registration, "")
    assert decision_for(cells)[0] == decision


def test_field_name_collision_keeps_library_identity():
    rows = [
        (10, ("LibraryA", "EditState", "是", "运行时", "编辑状态", "", "一致", "")),
        (40, ("LibraryB", "EditState", "是", "运行时", "编辑状态", "", "一致", "")),
        (50, ("LibraryB", "EditStateNew", "是", "运行时", "另一字段", "", "一致", "")),
    ]
    assert find_rules(rows, "EditState", "") == ("exact", rows[:2])
    assert find_rules(rows, "editstate", "libraryb") == ("exact", rows[1:2])
    assert find_rules(rows, "LibraryA.EditState", "") == ("exact", rows[:1])


def test_dispensing_scope_accepts_the_module_name_as_filter():
    rows = [
        (10, ("EpoxyApplication", "Pressure", "否", "机器参数·其他", "点胶时正压", "", "一致", "")),
        (20, ("Nozzle", "Pressure", "是", "设备专属", "吸嘴正压", "", "一致", "")),
    ]
    assert find_rules(rows, "正压", "点胶") == ("partial", rows[:1])
    assert find_rules(rows, "正压", "未知库") == ("unknown_library", [])


def test_rejects_a_workbook_with_a_different_fingerprint(tmp_path: Path):
    workbook = tmp_path / "wrong-version.xlsx"
    workbook.write_bytes(b"not the fixed version")
    with pytest.raises(ValueError, match="SHA-256"):
        load_rules(workbook)
