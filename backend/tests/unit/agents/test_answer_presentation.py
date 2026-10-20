import re

from app.agents.runtime.answer_presentation import format_answer, present


def test_long_bold_and_paragraph_layout_preserves_every_word_number_and_negation():
    text = "**" + "记录中216颗无刺穿，不能据此确定长期稳定。" * 12 + "**"
    formatted = present(text, "讲下经验")
    assert "**" not in formatted and "\n\n" in formatted
    assert re.sub(r"\s", "", formatted) == text.replace("**", "")
    assert present(formatted, "讲下经验") == formatted


def test_original_code_quotes_links_tables_and_ranges_are_unchanged():
    text = "**" + "原文" * 40 + "**\n\n```cs\nvar n = 280~300;\n```\n\n> " + "引文" * 120
    assert present(text, "逐字提取完整原文") == text
    protected = "```cs\n**" + "代码" * 40 + "**\n```\n\n> " + "引文" * 120
    protected += (
        "\n\n[范围-4~2μm](source:Test.cs#L1-L3)\n\n| 参数 | 值 |\n| --- | --- |\n| 高度 | 280~300 |"
    )
    assert present(protected, "解释") == protected


def test_named_parameter_combination_becomes_one_group_without_numeric_or_word_changes():
    raw = "- 组合方案：更换075顶针 + 焊头力20~30g + 顶针速度3mm/s + 顶针高度280~300"
    formatted = present(raw, "给成功参数")
    assert (
        formatted
        == "- 组合方案：\n  - 更换075顶针\n  - 焊头力20~30g\n  - 顶针速度3mm/s\n  - 顶针高度280~300"
    )
    assert re.sub(r"[\s+\-]", "", formatted) == re.sub(r"[\s+\-]", "", raw)
    assert present(formatted, "给成功参数") == formatted
    assert present(raw, "完整原文") == raw


def test_arithmetic_and_signed_range_are_not_treated_as_parameter_lists():
    raw = "公式：1+2+3+4=10\n\n范围：-4~+4μm\n\n`高度1 + 速度2 + 压力3 + 温度4`"
    assert present(raw, "解释") == raw


def test_observed_narrative_parameter_combination_does_not_break_bold_or_become_a_list():
    raw = (
        "先看无效尝试：单项调整作用有限。有效组合是**075顶针 + 焊头力20~30g + "
        "顶针速度3mm/s + 顶针高度280~300**，这是记录人的判断。"
    )
    formatted = present(raw, "蓝膜处理经验")
    assert formatted.replace("**", "") == raw.replace("**", "")
    assert "\n- " not in formatted and formatted.count("**") in {0, 2}
    payroll = "收入：基本工资2000 + 岗位奖金300 + 通勤补贴100 + 餐饮补贴100"
    assert present(payroll, "算收入") == payroll


def test_presentation_failure_preserves_checked_answer(monkeypatch):
    text = "已核对的事实216颗。"
    events = []

    def broken(*_):
        raise ValueError("format failed")

    monkeypatch.setattr("app.agents.runtime.answer_presentation.present", broken)

    assert format_answer(text, "经验", lambda *e: events.append(e)) == text
    assert events == [("answer_presentation", {"changed": False, "code": "formatting_failed"})]
