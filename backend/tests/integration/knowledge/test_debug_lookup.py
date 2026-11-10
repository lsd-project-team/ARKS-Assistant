"""延迟检索的副作用、固定版本与并发边界，真实临时数据库。"""

import json
from concurrent.futures import ThreadPoolExecutor

from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus
from app.modules.knowledge.corpora.debug_lookup import DebugIssueLookup
from app.modules.knowledge.semantic import SemanticRetrieval


def test_defining_tools_and_unused_review_does_not_open_the_corpus(services, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("工具尚未调用，不应加载资料")

    monkeypatch.setattr(DebugIssueCorpus, "__init__", forbidden)
    lookup = DebugIssueLookup(services[1], lambda *_: None, "你好")
    assert {tool.name for tool in lookup.tools()} == {"search_debug_issues", "read_debug_issue"}
    assert lookup.review_records({"old-record": 1}) == []


async def test_first_tool_call_freezes_one_version_and_next_run_gets_new_version(
    services, monkeypatch
):
    monkeypatch.setattr(SemanticRetrieval, "scores", lambda *_: {})
    issues = DebugIssues(HandoverStore(database=services[1]))
    saved = issues.save(DebugWrite(title="E901 真空报警", payload={"problem": "最初记录"}), {})
    lookup = DebugIssueLookup(services[1], lambda *_: None, "E901")
    tools = {tool.name: tool for tool in lookup.tools()}
    # 仅装配定义时还没有冻结旧内容；第一次实际调用应读取此时版本。
    updated = issues.save(
        DebugWrite(title=saved["title"], payload={"problem": "调用前已更新"}, version=1),
        {},
        saved["id"],
    )
    first = json.loads(await tools["read_debug_issue"].ainvoke({"record_id": saved["id"]}))
    assert first["version"] == updated["version"] and "调用前已更新" in first["content"]
    issues.save(
        DebugWrite(title=saved["title"], payload={"problem": "调用后再更新"}, version=2),
        {},
        saved["id"],
    )
    result = json.loads(await tools["search_debug_issues"].ainvoke({"query": "E901"}))
    assert result["matches"][0]["version"] == 2
    assert lookup.review_records({saved["id"]: 2})[0]["content"]["问题"] == "调用前已更新"
    other = DebugIssueLookup(services[1], lambda *_: None, "E901")
    assert other.read(saved["id"])["version"] == 3


def test_parallel_tools_build_one_shared_snapshot(services, monkeypatch):
    monkeypatch.setattr(SemanticRetrieval, "scores", lambda *_: {})
    issues = DebugIssues(HandoverStore(database=services[1]))
    saved = issues.save(DebugWrite(title="E901 真空报警", payload={"problem": "本次现象"}), {})
    constructed = []
    original = DebugIssueCorpus.__init__

    def counted(corpus, *args):
        constructed.append(corpus)
        original(corpus, *args)

    monkeypatch.setattr(DebugIssueCorpus, "__init__", counted)
    lookup = DebugIssueLookup(services[1], lambda *_: None, "E901")
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: lookup.read(saved["id"]), range(8)))
    assert len(constructed) == 1
    assert all(row["version"] == 1 and "本次现象" in row["content"] for row in results)


def test_reused_reference_reads_only_matching_version_without_semantic_search(
    services, monkeypatch
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("已知引用应直接核对编号与版本，无须相似度检索")

    monkeypatch.setattr(SemanticRetrieval, "scores", forbidden)
    issues = DebugIssues(HandoverStore(database=services[1]))
    saved = issues.save(DebugWrite(title="E901 记录", payload={"problem": "已知事实42"}), {})
    events = []
    lookup = DebugIssueLookup(services[1], lambda *row: events.append(row), "结果是什么")
    records = lookup.resolve_references({f"debug-issue:{saved['id']}/1"})
    assert records[0]["content"]["问题"] == "已知事实42"
    assert [kind for kind, _ in events] == ["knowledge_reference"]
    assert lookup.resolve_references({f"debug-issue:{saved['id']}/99"}) == []
    assert len(events) == 1
