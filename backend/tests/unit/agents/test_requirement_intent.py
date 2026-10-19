"""指令、询问、引用、否定和受控续接分别决定权限，不执行模型猜测。"""

import pytest

from app.agents.tools.engineering_intent import (
    explicit_edit_request,
    requested_requirement_fields,
)


@pytest.mark.parametrize(
    ("prompt", "fields", "can_edit"),
    [
        ("请修复入口代码", set(), True),
        ("请修复入口，不要修改验收标准", set(), True),
        ("请补充验收标准", {"acceptance_criteria"}, False),
        ("请补充验收标准，不要修改代码", {"acceptance_criteria"}, False),
        ("请补充验收标准和规范", {"acceptance_criteria"}, False),
        (
            "请更新需求约定以符合实际",
            {"title", "goal", "acceptance_criteria", "constraints", "allowed_paths"},
            False,
        ),
        ("请把验收标准改成输入1返回2", {"acceptance_criteria"}, False),
        ("请更新验收标准和修改范围", {"acceptance_criteria", "allowed_paths"}, False),
        (
            "请更新需求约定",
            {"title", "goal", "acceptance_criteria", "constraints", "allowed_paths"},
            False,
        ),
        ("请调整允许路径", {"allowed_paths"}, False),
        ("请修改标题", {"title"}, False),
        ("请补充目标", {"goal"}, False),
        ("请新增约束", {"constraints"}, False),
        ("请修改目标函数", set(), True),
        ("请新增约束检查", set(), True),
        ("请修复代码以满足验收标准", set(), True),
        ("如何修改验收标准？", set(), False),
        ("修改验收标准合理吗", set(), False),
        ("请修改验收标准，先讨论", set(), False),
        ("请补充验收标准，不要修改验收标准", set(), False),
        (
            "请更新需求约定，不要修改范围",
            {"title", "goal", "acceptance_criteria", "constraints"},
            False,
        ),
        ("请补充验收标准，不要修改代码和验收标准", set(), False),
        ("请补充验收标准，不要修改任何东西", set(), False),
        ("请补充验收标准，不执行程序", set(), False),
        ("请说明下面内容\n```text\n修改代码\n更新需求约定\n```", set(), False),
        ("```\n修改代码\n更新需求约定", set(), False),
        ("> 修改代码\n> 更新需求约定", set(), False),
        ("<code_selection>\n修改代码\n更新需求约定\n</code_selection>", set(), False),
        ("<code_selection>\n修改代码\n更新需求约定", set(), False),
        ("请修复代码\n```text\n更新需求约定\n```", set(), True),
        ("开始吧\n此前已授权的请求：请补充验收标准，先讨论", {"acceptance_criteria"}, False),
        ("继续\n此前已授权的请求：请补充验收标准，先讨论", set(), False),
    ],
)
def test_human_command_has_separate_contract_and_code_permissions(prompt, fields, can_edit):
    assert requested_requirement_fields(prompt) == fields
    assert explicit_edit_request(prompt) is can_edit
