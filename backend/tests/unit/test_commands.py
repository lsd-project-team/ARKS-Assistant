"""MCP 触发命令的文本解析与配置校验。"""

import pytest

from app.core.commands import normalize_trigger, split_command, used_triggers


def test_trigger_normalization_rejects_reserved_and_bad_words():
    assert normalize_trigger("  /参数复用 ") == "参数复用"
    assert normalize_trigger("参数_reuse-2") == "参数_reuse-2"
    assert normalize_trigger("") == ""
    assert normalize_trigger("/") == ""
    for value in ("/记录问题", "/record-issue", "/compact", "带 空格", "a" * 21, "命令!"):
        with pytest.raises(ValueError):
            normalize_trigger(value)


def test_split_command_only_matches_leading_standalone_command():
    triggers = {"参数复用"}
    assert split_command("/参数复用 点胶针偏移能直接复用吗", triggers) == (
        "参数复用",
        "点胶针偏移能直接复用吗",
    )
    assert split_command("  /参数复用\n那 Dispenser.EditState 呢", triggers) == (
        "参数复用",
        "那 Dispenser.EditState 呢",
    )
    assert split_command("/参数复用", triggers) == ("参数复用", "")
    for text in ("解释 /参数复用 的用法", "/参数复用的用法", "```\n/参数复用 x\n```", "/unknown 问题"):
        assert split_command(text, triggers) == (None, text)
    assert split_command("/PARAM 参数复用", {"PARAM"}) == ("PARAM", "参数复用")


def test_used_triggers_scans_user_messages_only():
    triggers = {"参数复用", "wiki"}
    texts = ["点胶针偏移能直接复用吗", "/参数复用 点胶针偏移", "那 Dispenser.EditState 呢"]
    assert used_triggers(texts, triggers) == {"参数复用"}
    assert used_triggers([], triggers) == set()


def test_mcp_trigger_config_validation():
    from app.core.config import AppSettings, McpSettings

    with pytest.raises(ValueError, match="内置命令重名"):
        McpSettings(id="a", name="A", trigger="记录问题", transport="stdio", command="python")
    server = McpSettings(id="a", name="A", trigger="/参数复用", transport="stdio", command="python")
    assert server.trigger == "参数复用"
    with pytest.raises(ValueError, match="触发命令不能重复"):
        AppSettings(
            mcp_servers=[
                McpSettings(
                    id="a", name="A", trigger="参数复用", transport="stdio", command="python"
                ),
                McpSettings(
                    id="b", name="B", trigger="参数复用", transport="stdio", command="python"
                ),
            ]
        )
