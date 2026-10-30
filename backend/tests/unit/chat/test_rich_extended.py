"""新增展示块必须与前端白名单一致，并保留核查、代码字面量及旧文档边界。"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.chat.rich_content import RichDocument
from app.modules.chat.rich_presentation import project_rich_content, rich_documents, source_pointers
from app.modules.source_analysis.evidence import citation_matches, disable_invalid_citations

FIXTURE = (
    Path(__file__).resolve().parents[4] / "frontend/tests/chat/fixtures/rich-content-extended.json"
)


def fence(blocks):
    return "```rich-content\n" + json.dumps({"version": 1, "blocks": blocks}) + "\n```"


def test_shared_extended_fixture_preserves_all_types_and_numeric_data():
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document = RichDocument.model_validate(original)
    assert document.model_dump(exclude_unset=True) == original
    assert [block.type for block in document.blocks] == [
        "markdown",
        "chart",
        "mermaid",
        "mindmap",
        "file",
        "tool_call",
        "source_reference",
    ]
    projected = project_rich_content(fence(original["blocks"]))
    assert "| 甲 | 0 |" in projected and "| 丙 | — |" in projected
    assert "富内容 → 图表" in projected and "flowchart LR" in projected
    assert "fixture-file" in projected and "read-entry" in projected
    assert "source:Program.cs#L2-L2" in projected
    assert [source.path for source in source_pointers(fence(original["blocks"]))] == ["Program.cs"]


def chart(**changes):
    return {
        "id": "chart",
        "type": "chart",
        "chart_type": "bar",
        "labels": ["甲", "乙"],
        "series": [{"id": "s", "name": "输入", "values": [0, 7]}],
        **changes,
    }


@pytest.mark.parametrize(
    "block",
    [
        chart(labels=[]),
        chart(labels=["甲"]),
        chart(series=[]),
        chart(series=[{"id": "s", "name": "n", "values": [None, None]}]),
        *[
            chart(series=[{"id": "s", "name": "n", "values": [value, 0]}])
            for value in (True, "7", float("inf"), float("nan"))
        ],
        chart(chart_type="pie", series=[{"id": "s", "name": "n", "values": [-1, 0]}]),
        chart(
            chart_type="pie",
            series=[
                {"id": "s1", "name": "n", "values": [1, 0]},
                {"id": "s2", "name": "n", "values": [1, 0]},
            ],
        ),
        chart(
            series=[
                {"id": "s", "name": "n", "values": [1, 0]},
                {"id": "s", "name": "n", "values": [1, 0]},
            ]
        ),
        chart(option={"formatter": "eval()"}),
        chart(labels=["x"] * 501),
        {"id": "f", "type": "file", "record_id": "../secret", "name": "bad"},
        {"id": "f", "type": "file", "record_id": "r", "name": "bad", "version": "1"},
        {"id": "f", "type": "file", "record_id": "r", "name": "bad", "url": "javascript:bad()"},
        {"id": "t", "type": "tool_call", "tool": {"id": "call", "name": "x", "status": "forged"}},
        {"id": "t", "type": "tool_call", "tool": {"id": "call", "name": "x", "cached": 1}},
    ],
)
def test_new_blocks_reject_invalid_data_and_arbitrary_runtime_options(block):
    with pytest.raises(ValidationError):
        RichDocument.model_validate({"version": 1, "blocks": [block]})


@pytest.mark.parametrize(
    "nodes",
    [
        [],
        [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
        [{"id": "r", "label": "R"}, {"id": "a", "label": "A", "parent_id": "missing"}],
        [
            {"id": "r", "label": "R"},
            {"id": "a", "label": "A", "parent_id": "b"},
            {"id": "b", "label": "B", "parent_id": "a"},
        ],
    ],
)
def test_mindmap_requires_one_connected_acyclic_tree(nodes):
    with pytest.raises(ValidationError):
        RichDocument.model_validate(
            {"version": 1, "blocks": [{"id": "m", "type": "mindmap", "nodes": nodes}]}
        )


@pytest.mark.parametrize(
    "content",
    [
        " ",
        "---\nconfig: {}\n---\nflowchart LR\nA-->B",
        '%%{init: {"securityLevel":"loose"}}%%\nflowchart LR\nA-->B',
        'flowchart LR\nA-->B\nclick A "https://evil.test"',
        "flowchart LR\nA-->B\nclassDef x fill:red",
        "flowchart LR\nA-->B\nstyle A fill:red",
    ],
)
def test_mermaid_rejects_model_configuration_styles_and_navigation(content):
    with pytest.raises(ValidationError):
        RichDocument.model_validate(
            {"version": 1, "blocks": [{"id": "m", "type": "mermaid", "content": content}]}
        )


def test_new_literals_are_not_treated_as_source_links_or_rewritten_as_markdown():
    link = "[字面量](source:Program.cs#L2-L2)"
    blocks = [
        chart(labels=[link, "乙"]),
        {"id": "mermaid", "type": "mermaid", "content": f'flowchart LR\nA["{link}"]'},
        {
            "id": "tool",
            "type": "tool_call",
            "tool": {
                "id": "call",
                "name": "read_source",
                "arguments": {"path": link},
                "result": link,
            },
        },
        {"id": "text", "type": "markdown", "content": link},
    ]
    original = fence(blocks)
    matches = citation_matches(project_rich_content(original))
    assert len(matches) == 1 and matches[0][2] == "Program.cs#L2-L2"
    rewritten = disable_invalid_citations(original, {"Program.cs#L2-L2"})
    document = next(doc for _, _, doc in rich_documents(rewritten))
    assert document.blocks[0].labels[0] == link
    assert document.blocks[1].content == blocks[1]["content"]
    assert document.blocks[2].tool.result == link
    assert document.blocks[3].content == "字面量（引用未核对）"


def test_null_tool_arguments_survive_source_rewrite_without_becoming_empty_object():
    blocks = [
        {
            "id": "tool",
            "type": "tool_call",
            "tool": {"id": "call", "name": "read_source", "arguments": None},
        },
        {"id": "text", "type": "markdown", "content": "[源码](source:Program.cs#L2-L2)"},
    ]
    revised = disable_invalid_citations(fence(blocks), {"Program.cs#L2-L2"})
    document = next(doc for _, _, doc in rich_documents(revised))
    assert document.blocks[0].tool.arguments is None
    assert '"arguments":null' in revised
