from app.modules.knowledge.citations import canonical_knowledge_citations
from app.modules.knowledge.feedback import numbered_prompt_block


def test_known_titles_and_ranges_are_preserved_without_guessing_unknown_links():
    rows = [
        {"id": "a", "title": "取片异常", "version": 2, "citation": "debug-issue:a/2"},
        {"id": "b", "title": "停机规程", "version": 3, "citation": "handover-source:b/3#L2-L8"},
    ]
    result = canonical_knowledge_citations(
        "[debug-issue:a/2](debug-issue:a/2) [原文](handover-source:b/3#L3-L5) "
        "[错误范围](handover-source:b/3#L1-L9) [猜测版本](debug-issue:a/1)",
        rows,
    )
    assert "[取片异常](debug-issue:a/2)" in result
    assert "· v2" not in result
    assert "[停机规程 · v3](handover-source:b/3#L3-L5)" in result
    assert "错误范围（资料引用未核对）" in result
    assert "猜测版本（资料引用未核对）" in result
    literal = "示例：`[示例](material:x/y/1#L1)`"
    assert canonical_knowledge_citations(literal, []) == literal
    assert (
        canonical_knowledge_citations("历史方案（debug-issue:a/2）", rows)
        == "历史方案（[取片异常](debug-issue:a/2)）"
    )


def test_truncated_prompt_reference_only_claims_lines_actually_included():
    row = {
        "id": "a",
        "title": "资料",
        "version": 1,
        "citation": "handover-source:a/1#L1-L80",
        "start_line": 1,
        "end_line": 80,
        "content": "\n".join(f"{i}: " + "现场说明" * 8 for i in range(1, 81)),
    }
    result, block = numbered_prompt_block(row, 400)
    assert result["end_line"] < 80
    assert result["citation"].endswith(f"#L1-L{result['end_line']}")
    assert "摘录未完整带入" in block
