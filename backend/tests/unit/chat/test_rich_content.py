import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.chat.rich_content import RichDocument
from app.modules.chat.rich_presentation import project_rich_content, rich_documents
from app.modules.source_analysis.evidence import (
    SourceEvidence,
    disable_invalid_citations,
    source_excerpt,
)


def fence(document):
    return "```rich-content\n" + json.dumps(document, ensure_ascii=False) + "\n```"


def test_shared_frontend_backend_fixture_and_projection():
    path = Path(__file__).resolve().parents[4] / "frontend/tests/chat/fixtures/rich-content.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    assert len(RichDocument.model_validate(document).blocks) == 8
    projected = project_rich_content("前文\n" + fence(document) + "\n后文")
    for text in [
        "前文",
        "功能入口",
        "检查条件",
        "失败时返回",
        "static void Main",
        "空闲 | 0",
        "入口 → 工作方法",
        "这里保留细节",
        "后文",
    ]:
        assert text in projected
    assert "source:Program.cs#L2-L2" in projected
    assert "rich-content" not in projected


@pytest.mark.parametrize(
    "block",
    [
        {"id": "x", "type": "text"},
        {"id": "x", "type": "text", "content": "ok", "onClick": "delete()"},
        {"id": "x", "type": "iframe"},
        {
            "id": "x",
            "type": "source_reference",
            "sources": [{"path": "../secret", "start_line": 1}],
        },
        {
            "id": "x",
            "type": "source_reference",
            "sources": [{"path": "Program.cs", "start_line": True}],
        },
        {
            "id": "x",
            "type": "table",
            "columns": [{"id": "a", "label": "A"}],
            "rows": [{"id": "r", "cells": []}],
        },
        {"id": "x", "type": "text", "content": None},
    ],
)
def test_invalid_schema_keeps_original_text(block):
    value = {"version": 1, "blocks": [block]}
    with pytest.raises(ValidationError):
        RichDocument.model_validate(value)
    original = fence(value)
    assert project_rich_content(original) == original


def test_schema_duplicate_ids_and_limits():
    block = {"id": "x", "type": "text", "content": "内容"}
    for value in [
        {"version": 2, "blocks": []},
        {"version": True, "blocks": []},
        {"version": 1, "blocks": [block, block]},
    ]:
        with pytest.raises(ValidationError):
            RichDocument.model_validate(value)
    for i in range(6):
        block = {"id": f"nest{i}", "type": "collapsible", "title": "细节", "blocks": [block]}
    with pytest.raises(ValidationError):
        RichDocument.model_validate({"version": 1, "blocks": [block]})
    oversized = fence(
        {"version": 1, "blocks": [{"id": "x", "type": "code", "content": "a" * 270000}]}
    )
    assert list(rich_documents(oversized))[0][2] is None


def test_literal_code_and_incomplete_blocks_are_not_projected():
    original = fence(
        {"version": 1, "blocks": [{"id": "x", "type": "text", "content": "不能变成组件"}]}
    )
    for content in ["````markdown\n" + original + "\n````", original[:-3], "普通旧历史"]:
        assert project_rich_content(content) == content


def test_structured_source_runs_through_existing_evidence_guard(services):
    workspace = services[2]
    ledger = SourceEvidence(workspace, lambda *_: None, required=True)
    ledger.record(source_excerpt(workspace, "Program.cs", 2, 2))
    answer = fence(
        {
            "version": 1,
            "blocks": [
                {
                    "id": "s",
                    "type": "step_flow",
                    "steps": [
                        {
                            "id": "main",
                            "title": "入口",
                            "description": "执行 Main",
                            "sources": [{"path": "Program.cs", "start_line": 2}],
                        }
                    ],
                }
            ],
        }
    )
    report = ledger.check(answer)
    assert report["passed"]
    assert report["citations"][0]["path"] == "Program.cs"
    invalid = answer.replace('"start_line": 2', '"start_line": 3')
    report = ledger.check(invalid)
    assert not report["passed"]
    lowered = disable_invalid_citations(
        invalid, {row["target"] for row in report["citations"] if not row["valid"]}
    )
    assert "引用未核对" in lowered and "rich-content" not in lowered


@pytest.mark.parametrize(
    "metadata", [{"version": "forged-version"}, {"source_workspace_id": "other-source"}]
)
def test_structured_citation_cannot_forge_snapshot_or_repository(services, metadata):
    workspace = services[2]
    ledger = SourceEvidence(workspace, lambda *_: None, required=True)
    ledger.record(source_excerpt(workspace, "Program.cs", 2, 2))
    answer = fence(
        {
            "version": 1,
            "blocks": [
                {
                    "id": "source",
                    "type": "source_reference",
                    "sources": [{"path": "Program.cs", "start_line": 2, **metadata}],
                }
            ],
        }
    )
    report = ledger.check(answer)
    assert not report["passed"]
    assert "不一致" in report["citations"][0]["reason"]
