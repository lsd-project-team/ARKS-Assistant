"""实际文件、Agent源码工具及多目录检索；读取与HTTP搜索契约保持独立。"""

import json

import pytest

from app.agents.tools.source import source_tools
from app.modules.source_analysis.backend import SourceBackend
from app.modules.source_analysis.collection import SourceCollection
from app.modules.source_analysis.evidence import SourceEvidence


@pytest.mark.parametrize("query", ["取片", "Pickup"])
async def test_agent_search_finds_entry_after_dense_legacy_file_without_creating_evidence(
    services, query
):
    workspace = services[2]
    (workspace.root / "Legacy.cs").write_text((query + " legacy\n") * 160, encoding="utf-8")
    task = workspace.root / "Tasks"
    task.mkdir()
    (task / "CurrentActionNode.cs").write_text("// " + query + " current\n", encoding="utf-8")
    ledger = SourceEvidence(workspace, lambda *_: None)
    tools = {tool.name: tool for tool in source_tools(workspace, ledger)}
    response = json.loads(await tools["search_source"].ainvoke({"query": query}))
    assert response["matches"][0] == {
        "path": "Tasks/CurrentActionNode.cs",
        "line": 1,
        "text": "// " + query + " current",
    }
    assert response["truncated"] and not ledger.reads
    assert len(workspace.search(query)["matches"]) == 100
    assert await tools["read_source"].ainvoke(
        {"path": "Tasks/CurrentActionNode.cs", "start_line": 1, "end_line": 1}
    )
    assert ledger.reads[0]["path"] == "Tasks/CurrentActionNode.cs"


@pytest.mark.parametrize("query", ["取片", "Pickup"])
def test_scoped_grep_filters_before_limit_and_keeps_complete_specific_file_matches(services, query):
    workspace = services[2]
    (workspace.root / "A.cs").write_text((query + " outside\n") * 200, encoding="utf-8")
    folder = workspace.root / "Later"
    folder.mkdir()
    (folder / "Work.cs").write_text((query + " wanted\n") * 6, encoding="utf-8")
    backend = SourceBackend(workspace)
    scoped = backend.grep(query, "/Later")
    assert scoped.matches and {row["path"] for row in scoped.matches} == {"/Later/Work.cs"}
    assert scoped.truncated
    specific = backend.grep(query, "/Later/Work.cs", max_count=20)
    assert len(specific.matches) == 6 and not specific.truncated
    assert [row["line"] for row in specific.matches] == list(range(1, 7))
    assert backend.grep(query, "/../outside").error


async def test_attached_sources_share_diversity_without_losing_prefix_or_scope(services, tmp_path):
    primary = services[2].root
    (primary / "Legacy.cs").write_text("// Pickup\n" * 200)
    attached = tmp_path / "attached"
    attached.mkdir()
    (attached / "CurrentTask.cs").write_text("// Pickup current\n")
    collection = SourceCollection(
        primary, [{"source_id": "extra", "label": "附加源码", "root": str(attached)}]
    )
    tools = {tool.name: tool for tool in source_tools(collection)}
    result = json.loads(await tools["search_source"].ainvoke({"query": "Pickup"}))
    assert result["matches"][0]["path"] == "@sources/extra/CurrentTask.cs"
    scoped = SourceBackend(collection).grep("Pickup", "/@sources/extra")
    assert scoped.matches == [
        {"path": "/@sources/extra/CurrentTask.cs", "line": 1, "text": "// Pickup current"}
    ]
    assert not scoped.truncated
