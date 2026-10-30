"""交接资料接入、改写命中、条件排除、固定版本与缓存的行为验收。"""

import hashlib

from sqlalchemy import event

from app.modules.handover.application.commands import Action, DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus
from app.modules.knowledge.corpora.handover_materials import HandoverMaterialCorpus
from app.modules.knowledge.search import catalog


def source(
    store, title="恢复生产", content="机器停止后重新启动生产，需要先恢复运行条件。", **payload
):
    return store.create(
        "source",
        title,
        {
            "content": content,
            "filename": title + ".txt",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            **payload,
        },
        "测试",
    )


def test_handover_documents_fixed_versions_archive_supersede_and_partial(services):
    store = HandoverStore(database=services[1])
    row = source(store)
    old = HandoverMaterialCorpus(services[1])
    match = old.search("停机以后怎样重新生产")[0]
    assert match["citation"] == f"handover-source:{row['id']}/1#L1-L1"
    changed = store.action(
        row["id"], "confirm", Action(version=1, actor="测试", opinion="复核固定资料")
    )
    assert old.excerpt(row["id"])["version"] == 1
    assert "机器停止" in old.excerpt(row["id"])["content"]
    assert HandoverMaterialCorpus(services[1]).excerpt(row["id"])["version"] == 2
    store.action(
        row["id"], "archive", Action(version=changed["version"], actor="测试", opinion="归档测试")
    )
    assert HandoverMaterialCorpus(services[1]).search("恢复生产") == []
    original = source(store, "旧版规程")
    replacement = source(store, "新版规程", supersedes=original["id"], parse_status="partial")
    scan = source(store, "恢复生产扫描件", content="", parse_status="needs_ocr")
    corpus = HandoverMaterialCorpus(services[1])
    matches = corpus.search("恢复生产")
    assert {item["id"] for item in matches} == {replacement["id"]}
    assert "部分解析" in matches[0]["notice"]
    assert scan["id"] not in {item["id"] for item in matches}


async def test_runtime_excludes_paused_handover_sources_and_preserves_records(
    services, monkeypatch
):
    from app.agents.runtime.engine import AgentRuntime

    store = HandoverStore(database=services[1])
    row = source(store, content="接料报警 E607：先检查托盘是否到位。")
    runtime = AgentRuntime(services[0], services[5], services[2], services[3], services[4])
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_deep_agent", lambda **kwargs: kwargs
    )
    events = []
    graph = await runtime.graph(
        "x",
        None,
        lambda kind, payload: events.append((kind, payload)),
        inspection=True,
        memory_query="接料报警 E607",
    )
    assert "先检查托盘是否到位" not in graph["system_prompt"]
    assert not any("handover_material" in item.name for item in graph["tools"])
    assert not any(kind == "knowledge_reference" for kind, _item in events)
    assert HandoverMaterialCorpus(services[1]).excerpt(row["id"])["version"] == 1
    assert store.get(row["id"])["state"] != "archived"
    off = await runtime.graph(
        "off",
        None,
        lambda *_: None,
        inspection=True,
        memory_query="E607",
        source_options={"use_knowledge": False},
    )
    assert "先检查托盘" not in off["system_prompt"]
    assert not any("handover_material" in tool.name for tool in off["tools"])


def test_incremental_cache_avoids_reloading_body_and_n_plus_one_queries(services, monkeypatch):
    store = HandoverStore(database=services[1])
    first = source(store)
    second = source(store, "其他资料", "按钮字体大小")
    index = catalog(services[1])
    monkeypatch.setattr(index.retrieval, "scores", lambda *_: {})
    before = index.loaded_documents
    corpus = HandoverMaterialCorpus(services[1])
    assert index.loaded_documents - before == 2
    statements = []

    def observed(_conn, _cursor, statement, *_):
        statements.append(statement)

    event.listen(services[1].engine, "before_cursor_execute", observed)
    try:
        another = HandoverMaterialCorpus(services[1])
        another.search("恢复生产")
        another.search("机器恢复")
    finally:
        event.remove(services[1].engine, "before_cursor_execute", observed)
    assert index.loaded_documents - before == 2
    assert len(statements) == 1 and "payload_json" not in statements[0]
    store.action(first["id"], "confirm", Action(version=1, actor="测试", opinion="复核固定资料"))
    latest = HandoverMaterialCorpus(services[1])
    assert index.loaded_documents - before == 3
    assert latest.excerpt(first["id"])["version"] == 2
    assert corpus.excerpt(first["id"])["version"] == 1
    assert latest.items[second["id"]] is corpus.items[second["id"]]


def test_debug_synonyms_versions_devices_conditions_and_unresolved(services):
    issues = DebugIssues(HandoverStore(database=services[1]))
    row = issues.save(
        DebugWrite(
            title="中转台取片异常",
            payload={
                "problem": "取片不稳定",
                "device": "ZX2200 HS",
                "software_version": "1.20",
                "conditions": "加热生产",
                "cause": "背胶粘连",
                "solution": "增加吹气",
                "resolution_status": "resolved",
            },
        ),
        {},
    )
    corpus = DebugIssueCorpus(services[1])
    for query in ("中间平台吸不起来", "中转台芯片黏住怎么办", "IPT 抓取失败", "背胶脱模问题"):
        assert corpus.search(query)[0]["id"] == row["id"]
    assert corpus.search("ZX2300 中转台取片异常") == []
    assert corpus.search("请问ZX2300中转台取片异常") == []
    assert corpus.search("V1.2 中转台取片异常") == []
    assert corpus.search("我用V1.2中转台取片异常") == []
    assert corpus.search("常温中转台取片异常") == []
    bound = DebugIssueCorpus(services[1], context_query="我用ZX2300 V3.0.0，常温取片异常")
    assert bound.search("取片异常", device="ZX2200 HS", software_version="1.20") == []
    assert bound.read(row["id"])["compatibility"]["status"] == "mismatch"
    summary = bound.search_report("取片异常")
    assert summary["excluded_records"][0]["id"] == row["id"]
    prompt, included = bound.prompt("取片异常", 2500)
    assert "条件不符的记录仍然存在" in prompt
    assert included[0]["id"] == row["id"]
    matched = corpus.search("ZX2200 HS V1.20 加热中转台取片异常", module="取片")
    assert matched[0]["compatibility"]["status"] == "needs_confirmation"
    assert corpus.search("中转台取片异常")[0]["compatibility"]["missing"]
    open_row = issues.save(
        DebugWrite(title="真空报警 E901", payload={"problem": "E901 负压不足"}), {}
    )
    assert (
        DebugIssueCorpus(services[1]).search("E901 怎么办")[0]["payload"]["resolution_status"]
        == "open"
    )
    assert DebugIssueCorpus(services[1]).search("E902 怎么办") == []
    codes = DebugIssueCorpus(services[1], context_query="请问报警E902怎么办")
    assert codes.search("负压不足 E901") == []
    assert open_row["id"]


def test_no_reference_event_for_candidates_outside_prompt_budget(services):
    source(HandoverStore(database=services[1]))
    events = []
    corpus = HandoverMaterialCorpus(
        services[1], lambda kind, payload: events.append((kind, payload))
    )
    assert corpus.prompt("恢复生产", 1) == ("", [])
    assert not any(kind == "knowledge_reference" for kind, _ in events)


def test_semantic_failure_is_visible_and_synonyms_still_work(services, monkeypatch):
    source(HandoverStore(database=services[1]), "中转台取片规程", "中转台取片异常先检查真空。")

    def unavailable():
        raise RuntimeError("测试：本地语义模型不可用")

    monkeypatch.setattr("app.modules.knowledge.semantic.local_encoder", unavailable)
    events = []
    corpus = HandoverMaterialCorpus(
        services[1], lambda kind, payload: events.append((kind, payload))
    )
    assert corpus.search("中间平台吸不起来")
    assert any(kind == "knowledge_search" and row["degraded"] for kind, row in events)


def test_superseded_records_cannot_hide_current_document_after_result_limit(services, monkeypatch):
    store = HandoverStore(database=services[1])
    previous = source(store)
    for _ in range(35):
        previous = source(store, supersedes=previous["id"])
    monkeypatch.setattr(catalog(services[1]).retrieval, "scores", lambda *_: {})
    rows = HandoverMaterialCorpus(services[1]).search("恢复生产")
    assert [row["id"] for row in rows] == [previous["id"]]
