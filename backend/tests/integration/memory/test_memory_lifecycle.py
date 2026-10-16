import json

import pytest
from langchain_core.messages import AIMessage

from app.agents.tools.conversation import conversation_tools
from app.modules.chat.schemas import MemoryWrite
from app.modules.source_analysis.evidence import SourceEvidence, source_excerpt


async def test_natural_conflict_review_requires_confirmation_and_preserves_versions(services):
    memory = services[4]
    old = memory.save(MemoryWrite(name="旧条件.md", content="生产必须先检查安全门关闭。"))
    request = MemoryWrite(name="新条件.md", content="生产可以跳过安全门关闭检查。")

    class Reviewer:
        async def ainvoke(self, _messages):
            return AIMessage(
                content=json.dumps(
                    [
                        {
                            "name": old["name"],
                            "relation": "conflict",
                            "reason": "同一生产启动条件一个要求检查，一个允许跳过。",
                            "left_quote": "可以跳过",
                            "right_quote": "必须先检查",
                        }
                    ],
                    ensure_ascii=False,
                )
            )

    rows = await memory.semantic_review(request, Reviewer())
    assert any(row["kind"] == "conflict" and row["basis"] == "semantic_review" for row in rows)
    with pytest.raises(ValueError, match="核对"):
        memory.save(request)
    confirmed = request.model_copy(
        update={"confirm_conflicts": True, "reviewed_versions": {old["name"]: old["version"]}}
    )
    saved = memory.save(confirmed)
    assert saved["lifecycle"] == "valid"
    invalid = memory.save(
        confirmed.model_copy(update={"version": saved["version"], "lifecycle": "invalid"})
    )
    assert invalid["lifecycle"] == "invalid" and "跳过" not in memory.prompt_snapshot("安全门")[0]
    assert memory.history.list("project", request.name)[0]["lifecycle"] == "invalid"


def test_source_changed_memory_requires_review_and_old_history_stays(services):
    _, _, workspace, _, memory, _ = services
    row = memory.save(
        MemoryWrite(name="入口.md", content="入口在 Program.cs。", source_paths=["Program.cs"])
    )
    (workspace.root / "Program.cs").write_text("class Changed {}")
    assert memory.read("project", row["name"])["lifecycle"] == "needs_review"
    assert "needs_review" in memory.prompt_snapshot("入口")[0]


def test_concurrent_lifecycle_edit_cannot_overwrite_newer_metadata(services):
    memory = services[4]
    row = memory.save(MemoryWrite(name="事实.md", content="保留相同内容。"))
    memory.save(
        MemoryWrite(
            name=row["name"],
            content=row["content"],
            version=row["version"],
            record_version=row["record_version"],
            lifecycle="invalid",
        )
    )
    with pytest.raises(ValueError, match="状态或来源已更新"):
        memory.save(
            MemoryWrite(
                name=row["name"],
                content=row["content"],
                version=row["version"],
                record_version=row["record_version"],
                lifecycle="valid",
            )
        )


@pytest.mark.parametrize("verified", [False, True])
async def test_automatic_project_memory_requires_current_run_source(services, verified):
    _, _, workspace, repository, memory, _ = services
    evidence = SourceEvidence(workspace, lambda *_: None)
    if verified:
        evidence.record(source_excerpt(workspace, "Program.cs", 1, 3))
    tools = {
        item.name: item for item in conversation_tools(repository, memory, None, evidence=evidence)
    }
    result = json.loads(
        await tools["remember"].ainvoke(
            {
                "name": "依据.md",
                "content": "入口函数为 Main。",
                "source_paths": ["/workspace/Program.cs"],
            }
        )
    )
    assert result["lifecycle"] == ("valid" if verified else "needs_review")
    assert result["sources"][0]["path"] == "Program.cs"


async def test_failed_memory_tool_can_recover_and_cannot_reactivate_invalid_record(services):
    _, _, workspace, repository, memory, _ = services
    tools = {item.name: item for item in conversation_tools(repository, memory, None)}
    failed = await tools["remember"].ainvoke(
        {
            "name": "错误路径.md",
            "content": "不能保存未读取来源。",
            "source_paths": ["../private.cs"],
        }
    )
    assert "对话工具未完成" in failed and not memory.list()
    saved = memory.save(
        MemoryWrite(name="失效.md", content="已经停用的事实。", lifecycle="invalid")
    )
    result = json.loads(
        await tools["remember"].ainvoke({"name": saved["name"], "content": "恢复旧事实。"})
    )
    assert (
        result["requires_review"]
        and memory.read("project", saved["name"])["lifecycle"] == "invalid"
    )
