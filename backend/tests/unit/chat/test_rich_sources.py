"""坏引用只失去点击能力，不能破坏其他展示结构或篡改代码示例。"""

import json
from pathlib import Path

from app.modules.chat.rich_presentation import project_rich_content, rich_documents, source_pointers
from app.modules.source_analysis.evidence import citation_matches, disable_invalid_citations

INVALID = "Program.cs#L2-L2"
BAD_LINK = "[未读位置](source:" + INVALID + ")"


def fence(document):
    return "```rich-content\n" + json.dumps(document, ensure_ascii=False) + "\n```"


def test_invalid_source_in_every_pointer_field_keeps_all_components_and_valid_source():
    path = Path(__file__).resolve().parents[4] / "frontend/tests/chat/fixtures/rich-content.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    original["blocks"][2]["steps"][1]["sources"] = [{"path": "Program.cs", "start_line": 1}]
    original["blocks"][4]["content"] += "\n// " + BAD_LINK
    original["blocks"][-1]["blocks"].append(
        {
            "id": "nested-flow",
            "type": "step_flow",
            "steps": [
                {
                    "id": "nested-step",
                    "title": "补充步骤",
                    "description": "保持默认收起。",
                    "sources": [{"path": "Program.cs", "start_line": 2}],
                }
            ],
        }
    )
    result = disable_invalid_citations(fence(original), {INVALID})
    document = next(doc for _, _, doc in rich_documents(result))
    assert document is not None
    assert [block.type for block in document.blocks] == [
        block["type"] for block in original["blocks"]
    ]
    assert document.blocks[1].items[0].source is None
    assert document.blocks[2].steps[0].sources == []
    assert document.blocks[2].steps[0].description == "确认前置条件。"
    assert document.blocks[2].steps[0].details == "失败时返回，不继续执行。"
    assert document.blocks[3].sources == [] and document.blocks[4].source is None
    assert document.blocks[4].content == original["blocks"][4]["content"]
    assert document.blocks[5].rows[1].cells == ["未知", None]
    assert document.blocks[6].edges[0].from_ == "entry"
    assert document.blocks[-1].default_open is False
    assert document.blocks[-1].blocks[-1].steps[0].sources == []
    assert [(p.path, p.start_line) for p in source_pointers(result)] == [("Program.cs", 1)]
    assert [match[2] for match in citation_matches(project_rich_content(result))] == [
        "Program.cs#L1-L1"
    ]
    assert result.count("Program.cs:2–2（引用未核对）") == 1
    assert disable_invalid_citations(result, {INVALID}) == result


def test_markdown_links_in_rich_prose_are_disabled_without_rewriting_literals_or_metadata():
    document = {
        "version": 1,
        "blocks": [
            {"id": "text", "type": "text", "content": BAD_LINK + " `" + BAD_LINK + "`"},
            {
                "id": "flow",
                "type": "step_flow",
                "steps": [
                    {
                        "id": "one",
                        "title": "入口",
                        "description": BAD_LINK,
                        "details": BAD_LINK,
                    }
                ],
            },
            {
                "id": "table",
                "type": "table",
                "columns": [{"id": "a", "label": BAD_LINK}],
                "rows": [{"id": "one", "cells": [BAD_LINK]}],
            },
            {"id": "code", "type": "code", "content": BAD_LINK, "filename": "Program.cs"},
        ],
    }
    code_example = "\n\n```markdown\n" + BAD_LINK + "\n```"
    broken = '\n\n```rich-content\n{"version":9,"blocks":[]}\n```'
    original = BAD_LINK + "\n\n" + fence(document) + code_example + broken + "\n\n" + BAD_LINK
    result = disable_invalid_citations(original, {INVALID})
    revised = next(doc for _, _, doc in rich_documents(result))
    assert revised.blocks[0].content == "未读位置（引用未核对） `" + BAD_LINK + "`"
    assert revised.blocks[1].steps[0].description == "未读位置（引用未核对）"
    assert revised.blocks[1].steps[0].details == "未读位置（引用未核对）"
    assert revised.blocks[2].columns[0].label == "未读位置（引用未核对）"
    assert revised.blocks[2].rows[0].cells == ["未读位置（引用未核对）"]
    assert revised.blocks[3].content == BAD_LINK and revised.blocks[3].filename == "Program.cs"
    assert code_example in result and broken in result
    assert result.startswith("未读位置（引用未核对）") and result.endswith("未读位置（引用未核对）")
    assert not citation_matches(project_rich_content(result))


def test_protocol_limits_and_noop_are_preserved_when_warnings_are_added():
    document = {
        "version": 1,
        "blocks": [
            {
                "id": "flow",
                "type": "step_flow",
                "steps": [
                    {
                        "id": "one",
                        "title": "条件",
                        "description": "条" * 4000,
                        "sources": [{"path": "Program.cs", "start_line": 2}],
                    }
                ],
            }
        ]
        + [{"id": f"text-{i}", "type": "text", "content": "保留正文"} for i in range(127)],
    }
    original = fence(document)
    assert disable_invalid_citations(original, set()) == original
    assert disable_invalid_citations(original, {"Elsewhere.cs#L1"}) == original
    result = disable_invalid_citations(original, {INVALID})
    revised = next(doc for _, _, doc in rich_documents(result))
    assert len(revised.blocks) == 128 and revised.blocks[0].steps[0].description == "条" * 4000
    assert "引用未核对" in result and not list(source_pointers(result))
