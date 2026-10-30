"""冲突状态的持久化、原文依据和整体带入；真实数据库与文件，模型使用可控替身。"""

import json
from datetime import UTC, datetime, timedelta
from time import time

import pytest
from langchain_core.messages import AIMessage

from app.agents.context.tokens import text_tokens
from app.core.config import dump_json
from app.modules.auth.context import request_identity
from app.modules.chat.models import Message, Thread
from app.modules.knowledge.search import catalog
from app.modules.memory.conflicts import (
    ReconciliationResponse,
    checked_decisions,
    fact_states,
    pair_id,
    retrieval_units,
)
from app.modules.memory.models import MemoryExtraction
from app.modules.memory.reconciliation import comparison_pairs, pair_batches
from app.modules.memory.selection import MemorySelection
from tests.helpers.memories import MemorySeed, seed_memory
from tests.integration.memory.test_background_memory import worker as worker


@pytest.fixture
def facts(services, monkeypatch, request):
    memory = services[4]
    monkeypatch.setattr(catalog(services[1]).retrieval, "scores", lambda *_: {})
    kind = getattr(request, "param", None)
    if kind is None and hasattr(request.node, "callspec"):
        kind = request.node.callspec.params.get("kind")
    old = "ZX2200 V2真空等待超时是5秒。"
    newer = {
        "duplicate": old,
        "complementary": "ZX2200 V2真空等待开始前必须先释放负压。",
        "different_conditions": "ZX2200 V1真空等待超时是10秒。",
        "conflict": "ZX2200 V2真空等待超时是10秒。",
    }.get(kind, "更正：ZX2200 V2真空等待超时改为10秒。")
    seed_memory(memory, MemorySeed("ZX2200真空超时旧记录", old))
    seed_memory(memory, MemorySeed("ZX2200真空超时新记录", newer))
    bundle = memory.generated.bundle("local", memory.workspace.id)
    return [fact for group in bundle["document"]["groups"] for fact in group["memories"]]


def relation(left, right, kind, *, winner=None):
    return {
        "pair_id": pair_id(left["id"], right["id"]),
        "left_id": left["id"],
        "right_id": right["id"],
        "relation": kind,
        "replacement_id": winner,
        "basis": None,
        "fingerprints": {row["id"]: row["fingerprint"] for row in (left, right)},
    }


def publish(memory, facts, relations):
    return memory.generated.publish(
        {"owner_id": "local", "workspace_id": memory.workspace.id},
        {
            "groups": [{"title": "真空等待", "memories": facts}],
            "relations": relations,
            "relation_version": 1,
        },
    )


@pytest.mark.parametrize(
    "kind,units,label",
    [
        ("duplicate", 1, "重复记录"),
        ("complementary", 1, None),
        ("different_conditions", 2, None),
        ("conflict", 1, "待核实冲突"),
        ("supersedes", 1, "已替代"),
    ],
)
async def test_old_completed_bundle_is_reconciled_and_keeps_history(
    services, worker, facts, monkeypatch, kind, units, label
):
    background, calls = worker
    original = background.invoke
    comparisons = []
    with services[1].session.begin() as session:
        for fact in facts:
            session.get(Thread, fact["thread_id"]).updated_at = (
                datetime.now(UTC) - timedelta(days=40)
            ).isoformat()

    async def invoke(config, ledger, prompt, payload, **kwargs):
        if "你负责比较长期记忆" not in prompt:
            return await original(config, ledger, prompt, payload, **kwargs)
        comparisons.extend(payload)
        decisions = []
        for pair in payload:
            row = {"pair_id": pair["id"], "relation": kind}
            if kind == "supersedes":
                newer = next(fact for fact in pair["facts"] if "新记录" in fact["title"])
                row.update(replacement_id=newer["id"], basis=newer["evidence"][0])
            decisions.append(row)
        return dump_json({"decisions": decisions})

    monkeypatch.setattr(background, "invoke", invoke)
    await background.run_once()
    bundle = services[4].generated.bundle("local", services[2].id)
    assert bundle["document"]["relation_version"] == 1
    assert len(bundle["document"]["relations"]) == 1 and len(comparisons) == 1
    assert calls == ["consolidate"]  # 旧输入直接复用，不重新提取、不受30天候选窗口影响。
    assert len(services[4].candidates("ZX2200真空超时")["matches"]) == units
    rendered = services[4].list()[0]["content"]
    assert all(fact["content"] in rendered for fact in facts)
    if label:
        assert label in rendered
        files = list(services[0].memories.rglob("MEMORY.md"))
        assert any(label in path.read_text(encoding="utf-8") for path in files)
    prompt, rows = services[4].prompt_snapshot("ZX2200真空超时")
    if kind == "supersedes":
        assert facts[0]["content"] not in prompt and facts[1]["content"] in prompt
        assert rows[0]["memory_ids"] == [facts[1]["id"]]
    else:
        assert set(rows[0]["memory_ids"]) == {fact["id"] for fact in facts}
        assert set(rows[0]["source_thread_ids"]) == {fact["thread_id"] for fact in facts}
    await background.run_once()
    assert calls == ["consolidate"] and len(comparisons) == 1


async def test_reconciliation_error_preserves_previous_bundle_and_durable_input(
    services, worker, facts, monkeypatch
):
    before = services[4].generated.bundle("local", services[2].id)
    original = worker[0].invoke

    async def invalid(config, ledger, prompt, payload, **kwargs):
        if "你负责比较长期记忆" in prompt:
            return '{"decisions":[]}'
        return await original(config, ledger, prompt, payload, **kwargs)

    monkeypatch.setattr(worker[0], "invoke", invalid)
    await worker[0].run_once()
    assert services[4].generated.bundle("local", services[2].id) == before
    assert worker[1] == []
    with services[1].session() as session:
        jobs = [session.get(MemoryExtraction, fact["thread_id"]) for fact in facts]
        assert all(job.raw_json and job.state == "failed" for job in jobs)
        assert all(job.error_code == "memory_relation_invalid_pairs" for job in jobs)


async def test_other_source_changed_during_relationship_review_prevents_publish(
    services, worker, facts, monkeypatch
):
    memory = services[4]
    before = memory.generated.bundle("local", memory.workspace.id)
    original = worker[0].invoke
    snapshot = worker[0].snapshot(facts[1]["thread_id"], services[5].load())
    claim = worker[0].claim(snapshot, time(), reconcile_existing=True)

    async def changed(config, ledger, prompt, payload, **kwargs):
        if "你负责比较长期记忆" in prompt:
            with services[1].session.begin() as session:
                session.get(
                    Message, facts[0]["evidence"][0]["message_id"]
                ).content = "已撤回原记录。"
            return dump_json(
                {"decisions": [{"pair_id": row["id"], "relation": "conflict"} for row in payload]}
            )
        return await original(config, ledger, prompt, payload, **kwargs)

    monkeypatch.setattr(worker[0], "invoke", changed)
    await worker[0].process(snapshot, services[5].load(), worker[0].ledger(services[2].id), claim)
    assert memory.generated.bundle("local", memory.workspace.id) == before
    with services[1].session() as session:
        assert (
            session.get(MemoryExtraction, snapshot["thread_id"]).error_code
            == "memory_source_changed"
        )


def decision_input(facts):
    left, right = facts
    right = {**right, "origin_roles": {right["evidence"][0]["message_id"]: "user"}}
    pair = {"id": pair_id(left["id"], right["id"]), "facts": [left, right]}
    decision = {
        "pair_id": pair["id"],
        "relation": "supersedes",
        "replacement_id": right["id"],
        "basis": right["evidence"][0],
    }
    return pair, decision


@pytest.mark.parametrize("reason", ["assistant", "no_change_words"])
def test_replacement_without_explicit_user_change_becomes_unresolved_conflict(facts, reason):
    pair, decision = decision_input(facts)
    right = pair["facts"][1]
    if reason == "assistant":
        right["origin_roles"] = {decision["basis"]["message_id"]: "assistant"}
    else:
        right["evidence"] = [{**right["evidence"][0], "quote": "ZX2200 V2真空等待超时是10秒。"}]
        decision["basis"] = right["evidence"][0]
    checked = checked_decisions(
        ReconciliationResponse.model_validate({"decisions": [decision]}), [pair]
    )
    assert checked[0]["relation"] == "conflict" and checked[0]["replacement_id"] is None
    assert checked[0]["basis"] is None


@pytest.mark.parametrize(
    "invalid",
    [
        "unknown_pair",
        "missing_pair",
        "duplicate_pair",
        "unknown_winner",
        "fake_quote",
        "extra_replacement",
    ],
)
def test_invalid_relation_output_cannot_change_states(facts, invalid):
    pair, decision = decision_input(facts)
    decisions = [decision]
    if invalid == "unknown_pair":
        decision["pair_id"] = "unknown"
    elif invalid == "missing_pair":
        decisions = []
    elif invalid == "duplicate_pair":
        decisions *= 2
    elif invalid == "unknown_winner":
        decision["replacement_id"] = "unknown"
    elif invalid == "fake_quote":
        decision["basis"] = {
            "message_id": decision["basis"]["message_id"],
            "quote": "更正这条虚构记录",
        }
    else:
        decision["relation"] = "different_conditions"
    with pytest.raises(ValueError, match="memory_relation_"):
        checked_decisions(ReconciliationResponse.model_validate({"decisions": decisions}), [pair])


def test_conflict_is_atomic_at_exact_context_budget_and_retains_both_sources(services, facts):
    memory = services[4]
    publish(memory, facts, [relation(*facts, "conflict")])
    prompt, rows = memory.prompt_snapshot("ZX2200真空超时")
    assert "待核实冲突" in prompt and "不能任选一方" in prompt
    assert all(fact["content"] in prompt for fact in facts)
    boundary = text_tokens(prompt)
    assert memory.prompt_snapshot("ZX2200真空超时", max_tokens=boundary)[0] == prompt
    assert memory.prompt_snapshot("ZX2200真空超时", max_tokens=boundary - 1) == ("", [])
    assert set(rows[0]["memory_ids"]) == {fact["id"] for fact in facts}


@pytest.mark.parametrize("change", ["delete", "edit"])
async def test_change_to_either_conflict_member_invalidates_whole_model_approval(
    services, facts, change
):
    memory = services[4]
    publish(memory, facts, [relation(*facts, "conflict")])
    events = []

    class Picker:
        async def ainvoke(self, messages, **_kwargs):
            payload = json.loads(messages[-1].text)
            assert len(payload["candidates"]) == 1
            assert payload["candidates"][0]["state"] == "conflicted"
            unit = payload["candidates"][0]
            other = next(fact for fact in facts if fact["id"] != unit["id"])
            with services[1].session.begin() as session:
                if change == "delete":
                    session.get(Thread, other["thread_id"]).state = "deleted"
                else:
                    session.get(
                        Message, other["evidence"][0]["message_id"]
                    ).content = "撤回此依据。"
            return AIMessage(content=dump_json({"memory_ids": [unit["id"]]}))

    gate = MemorySelection(
        memory, Picker(), services[5].load().model, lambda *row: events.append(row)
    )
    assert await gate.prepare("ZX2200真空超时") == ("", [])


@pytest.mark.parametrize("facts", ["duplicate"], indirect=True)
def test_duplicate_content_is_recalled_once_with_all_original_evidence(services, facts):
    memory = services[4]
    publish(memory, facts, [relation(*facts, "duplicate")])
    candidates = memory.candidates("ZX2200真空超时")
    assert len(candidates["matches"]) == 1
    unit = candidates["matches"][0][1]
    assert unit["content"].count(facts[0]["content"]) == 1
    assert len(unit["evidence"]) == 2
    assert {member["id"] for member in unit["members"]} == {fact["id"] for fact in facts}
    assert {dump_json(member["evidence"]) for member in unit["members"]} == {
        dump_json(fact["evidence"]) for fact in facts
    }


def test_deleted_replacement_cannot_keep_suppressing_valid_original(services, facts):
    memory = services[4]
    publish(memory, facts, [relation(*facts, "supersedes", winner=facts[1]["id"])])
    assert facts[0]["content"] not in memory.prompt_snapshot("ZX2200真空超时")[0]
    with services[1].session.begin() as session:
        session.get(Thread, facts[1]["thread_id"]).state = "deleted"
    prompt, rows = memory.prompt_snapshot("ZX2200真空超时")
    assert facts[0]["content"] in prompt and facts[1]["content"] not in prompt
    assert rows[0]["memory_ids"] == [facts[0]["id"]]


def graph_fact(key, content):
    return {
        "id": key,
        "fingerprint": key,
        "title": "真空超时",
        "kind": "project",
        "content": content,
        "evidence": [],
        "sources": [],
    }


@pytest.mark.parametrize(
    "case", ["cycle", "multiple_winners", "duplicate_old", "chain", "diamond", "inherited_conflict"]
)
def test_relationship_chains_do_not_silently_lose_or_resurrect_conflicting_facts(case):
    a, b, c = [graph_fact(key, f"超时{index}秒") for index, key in enumerate("abc", 1)]
    rows = {
        "cycle": [
            relation(a, b, "supersedes", winner="b"),
            relation(b, c, "supersedes", winner="c"),
            relation(a, c, "supersedes", winner="a"),
        ],
        "multiple_winners": [
            relation(a, b, "supersedes", winner="b"),
            relation(a, c, "supersedes", winner="c"),
        ],
        "duplicate_old": [relation(a, b, "duplicate"), relation(a, c, "supersedes", winner="c")],
        "chain": [
            relation(a, b, "supersedes", winner="b"),
            relation(b, c, "supersedes", winner="c"),
        ],
        "inherited_conflict": [
            relation(a, b, "conflict"),
            relation(b, c, "supersedes", winner="c"),
        ],
        "diamond": [
            relation(a, b, "supersedes", winner="b"),
            relation(b, c, "supersedes", winner="c"),
            relation(a, c, "supersedes", winner="c"),
        ],
    }[case]
    facts = [a, b, c]
    states = fact_states(facts, rows)
    units = retrieval_units([{"title": "真空", "memories": facts}], rows)
    if case in {"cycle", "multiple_winners"}:
        assert all(state["state"] == "conflicted" for state in states.values())
        assert len(units) == 1 and units[0]["memories"][0]["state"] == "conflicted"
    elif case in {"duplicate_old", "chain", "diamond"}:
        assert states["a"]["state"] == states["b"]["state"] == "superseded"
        assert [fact["id"] for group in units for fact in group["memories"]] == ["c"]
    else:
        assert states["b"]["state"] == "superseded"
        assert states["a"]["state"] == states["c"]["state"] == "conflicted"
        assert {fact["id"] for fact in units[0]["memories"][0]["members"]} == {"a", "c"}


def test_cached_relations_are_reused_but_source_fingerprint_change_requires_review(facts):
    retrieval = type("Lexical", (), {"scores": lambda *_: {}})()
    previous = [relation(*facts, "different_conditions")]
    assert comparison_pairs(facts, previous, retrieval) == []
    altered = [{**facts[0], "fingerprint": "new-source"}, facts[1]]
    from app.modules.memory.conflicts import live_relations

    assert len(comparison_pairs(altered, live_relations(previous, altered), retrieval)) == 1


def test_pair_batches_preserve_whole_facts_and_reject_oversized_pair(services, facts):
    config = services[5].load()
    pairs = [{"id": str(index), "facts": facts} for index in range(17)]
    batches = pair_batches(pairs, config)
    assert [row for batch in batches for row in batch] == pairs
    assert all(len(batch) <= 16 for batch in batches)
    config = config.model_copy(
        update={
            "model": config.model.model_copy(update={"context_tokens": 1024, "output_tokens": 512})
        }
    )
    with pytest.raises(ValueError, match="memory_relation_input_too_large"):
        pair_batches([{"id": "huge", "facts": [{**facts[0], "content": "条件" * 10000}]}], config)


@pytest.mark.parametrize("choose_member", [False, True])
async def test_selector_cannot_inject_only_one_side_of_a_conflict(services, facts, choose_member):
    memory = services[4]
    publish(memory, facts, [relation(*facts, "conflict")])

    class Picker:
        async def ainvoke(self, messages, **_kwargs):
            unit = json.loads(messages[-1].text)["candidates"][0]
            selected = (
                next(fact["id"] for fact in facts if fact["id"] != unit["id"])
                if choose_member
                else unit["id"]
            )
            return AIMessage(content=dump_json({"memory_ids": [selected]}))

    prompt, rows = await MemorySelection(
        memory, Picker(), services[5].load().model, lambda *_: None
    ).prepare("ZX2200真空超时")
    if choose_member:
        assert (prompt, rows) == ("", [])
    else:
        assert all(fact["content"] in prompt for fact in facts)
        assert "待核实冲突" in prompt
        assert set(rows[0]["memory_ids"]) == {fact["id"] for fact in facts}


async def test_consolidation_omission_cannot_erase_either_side_of_conflict(
    services, worker, facts, monkeypatch
):
    original = worker[0].invoke

    async def invoke(config, ledger, prompt, payload, **kwargs):
        if "你负责比较长期记忆" in prompt:
            return dump_json(
                {"decisions": [{"pair_id": row["id"], "relation": "conflict"} for row in payload]}
            )
        if "整理已提取" in prompt:
            return '{"groups":[]}'
        return await original(config, ledger, prompt, payload, **kwargs)

    monkeypatch.setattr(worker[0], "invoke", invoke)
    await worker[0].run_once()
    prompt, rows = services[4].prompt_snapshot("ZX2200真空超时")
    assert all(fact["content"] in prompt for fact in facts)
    assert set(rows[0]["memory_ids"]) == {fact["id"] for fact in facts}
    assert "待核实冲突" in prompt


async def test_new_correction_resolves_existing_conflict_without_rejudging_cached_pair(
    services, worker, facts, monkeypatch
):
    memory = services[4]
    previous = relation(*facts, "conflict")
    seed_memory(
        memory, MemorySeed("ZX2200真空超时最终更正", "更正：ZX2200 V2真空等待超时统一改为15秒。")
    )
    bundle = memory.generated.bundle("local", memory.workspace.id)
    all_facts = [fact for group in bundle["document"]["groups"] for fact in group["memories"]]
    newest = next(fact for fact in all_facts if "最终更正" in fact["title"])
    publish(memory, all_facts, [previous])
    with services[1].session.begin() as session:
        session.get(MemoryExtraction, newest["thread_id"]).state = "extracted"
    original = worker[0].invoke
    compared = []

    async def invoke(config, ledger, prompt, payload, **kwargs):
        if "你负责比较长期记忆" not in prompt:
            return await original(config, ledger, prompt, payload, **kwargs)
        compared.extend(row["id"] for row in payload)
        return dump_json(
            {
                "decisions": [
                    {
                        "pair_id": row["id"],
                        "relation": "supersedes",
                        "replacement_id": newest["id"],
                        "basis": newest["evidence"][0],
                    }
                    for row in payload
                ]
            }
        )

    monkeypatch.setattr(worker[0], "invoke", invoke)
    await worker[0].run_once()
    assert len(compared) == 2 and previous["pair_id"] not in compared
    prompt, rows = memory.prompt_snapshot("ZX2200真空超时")
    assert newest["content"] in prompt and "待核实冲突" not in prompt
    assert all(fact["content"] not in prompt for fact in facts)
    assert rows[0]["memory_ids"] == [newest["id"]]


async def test_legacy_bundle_review_never_compares_private_memories_across_accounts(
    services, worker, monkeypatch
):
    memory = services[4]
    for owner in ("alpha", "beta"):
        token = request_identity.set({"user": {"id": owner, "role": "user"}})
        try:
            seed_memory(memory, MemorySeed("真空超时", f"ZX2200真空超时由{owner}确认。"))
        finally:
            request_identity.reset(token)
    seen = []
    original = worker[0].invoke

    async def invoke(config, ledger, prompt, payload, **kwargs):
        seen.append(payload)
        assert "你负责比较长期记忆" not in prompt
        return await original(config, ledger, prompt, payload, **kwargs)

    monkeypatch.setattr(worker[0], "invoke", invoke)
    await worker[0].run_once()
    assert len(seen) == 2
    assert all(not ("alpha" in dump_json(row) and "beta" in dump_json(row)) for row in seen)
    for owner in ("alpha", "beta"):
        bundle = memory.generated.bundle(owner, memory.workspace.id)
        assert bundle["document"]["relation_version"] == 1
        assert bundle["document"]["relations"] == []
