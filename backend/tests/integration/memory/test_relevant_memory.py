"""记忆按条目检索：真实聊天、数据库与快照，仅替换模型和指定的检索依赖。"""

import pytest

from app.agents.context.tokens import text_tokens
from app.agents.runtime.engine import AgentRuntime
from app.modules.auth.context import request_identity
from app.modules.chat.models import Message
from app.modules.knowledge.search import catalog
from app.modules.memory.service import MemoryService
from app.modules.source_analysis.workspace import Workspace
from tests.helpers.memories import MemorySeed, seed_memory
from tests.helpers.models import DeterministicModel


@pytest.fixture
def lexical(services, monkeypatch):
    engine = catalog(services[1]).retrieval
    monkeypatch.setattr(engine, "scores", lambda *_: {})
    return engine


@pytest.fixture
def topics(services):
    memory, workspace = services[4], services[2]
    (workspace.root / "Pump.cs").write_text("class Pump {}", encoding="utf-8")
    (workspace.root / "Palette.cs").write_text("class Palette {}", encoding="utf-8")
    seed_memory(
        memory, MemorySeed("真空恢复", "真空恢复前需确认负压已释放。", source_paths=["Pump.cs"])
    )
    seed_memory(memory, MemorySeed("外观设置", "界面背景选择浅绿色。", source_paths=["Palette.cs"]))
    bundle = memory.generated.bundle("local", workspace.id)
    facts = [fact for group in bundle["document"]["groups"] for fact in group["memories"]]
    # 同一个整理主题下也可能包含多条事实，命中主题不能带入整个主题。
    memory.generated.publish(
        {"owner_id": "local", "workspace_id": workspace.id},
        {"groups": [{"title": "操作约定", "memories": facts}]},
    )
    return facts


def test_selected_fact_and_snapshot_exclude_unrelated_content_evidence_and_sources(
    services, topics, lexical
):
    memory = services[4]
    before = memory.list()
    prompt, rows = memory.prompt_snapshot("真空恢复要注意什么")
    assert "真空恢复前需确认负压已释放。" in prompt
    assert "浅绿色" not in prompt and "外观设置" not in prompt and "Palette.cs" not in prompt
    assert rows[0]["source_thread_ids"] == [topics[0]["thread_id"]]
    assert [row["path"] for row in rows[0]["sources"]] == ["Pump.cs"]
    assert "浅绿色" not in rows[0]["content"]
    assert rows[0]["injected_text"] == prompt and rows[0]["partial"]
    assert "当前问题" in rows[0]["inclusion_reason"]
    assert memory.list() == before  # 筛选不修改完整记忆与发布版本。


@pytest.mark.parametrize("query", [None, "", "  ", "你好", "怎么处理这个问题", "标定精度"])
def test_empty_generic_or_unrelated_question_does_not_fall_back_to_all_memories(
    services, topics, lexical, query
):
    assert services[4].prompt_snapshot(query) == ("", [])


def test_question_with_selected_source_path_can_match_memory(services, topics, lexical):
    prompt, rows = services[4].prompt_snapshot("解释当前选区\nPump.cs")
    assert "真空恢复" in prompt and "浅绿色" not in prompt
    assert rows[0]["source_thread_ids"] == [topics[0]["thread_id"]]


def test_shared_alarm_word_does_not_make_another_device_topic_relevant(services, lexical):
    memory = services[4]
    seed_memory(memory, MemorySeed("真空报警", "真空报警时检查管路是否漏气。"))
    seed_memory(memory, MemorySeed("电机报警", "电机报警时检查驱动器过流状态。"))
    prompt, _ = memory.prompt_snapshot("真空异常怎么处理")
    assert "管路是否漏气" in prompt and "驱动器过流" not in prompt


def test_original_evidence_and_group_title_do_not_expand_matches(services, lexical):
    memory = services[4]
    seed_memory(memory, MemorySeed("外观", "界面背景选择浅绿色。聊天里另外提到真空恢复。"))
    bundle = memory.generated.bundle("local", memory.workspace.id)
    fact = bundle["document"]["groups"][0]["memories"][0]
    fact["content"] = "界面背景选择浅绿色。"
    memory.generated.publish(
        {"owner_id": "local", "workspace_id": memory.workspace.id},
        {"groups": [{"title": "真空恢复与外观", "memories": [fact]}]},
    )
    assert memory.prompt_snapshot("真空恢复") == ("", [])


@pytest.mark.parametrize("budget", [0, -1, 20])
def test_insufficient_budget_does_not_inject_partial_conditions(services, topics, lexical, budget):
    assert services[4].prompt_snapshot("真空恢复", max_tokens=budget) == ("", [])


def test_complete_fact_fits_exact_budget_but_not_one_token_less(services, lexical):
    memory = services[4]
    seed_memory(memory, MemorySeed("真空条件", "真空释放后才能启动，压力未恢复时保持停止。"))
    prompt, _ = memory.prompt_snapshot("真空条件")
    boundary = text_tokens(prompt)
    assert memory.prompt_snapshot("真空条件", max_tokens=boundary)[0] == prompt
    assert memory.prompt_snapshot("真空条件", max_tokens=boundary - 1) == ("", [])


def test_oversized_match_is_skipped_and_smaller_relevant_fact_can_fit(services, lexical):
    memory = services[4]
    seed_memory(memory, MemorySeed("真空真空真空", "真空约定" * 2000))
    seed_memory(memory, MemorySeed("真空", "真空释放后再恢复。"))
    before = memory.list()
    prompt, rows = memory.prompt_snapshot("真空约定", max_tokens=400)
    assert "真空释放后再恢复。" in prompt and "真空约定" not in prompt
    assert text_tokens(prompt) <= 400 and rows[0]["partial"]
    assert len(rows[0]["source_thread_ids"]) == 1 and memory.list() == before


def test_matches_are_bounded_even_when_many_facts_share_a_topic(services, lexical):
    memory = services[4]
    for index in range(8):
        seed_memory(memory, MemorySeed(f"真空约定{index}", f"真空维护要求第{index}项。"))
    prompt, rows = memory.prompt_snapshot("真空维护")
    assert len(rows[0]["source_thread_ids"]) == 6
    assert "第6项" not in prompt and "第7项" not in prompt
    assert memory.list()[0]["content"].count("\n- 真空维护要求") == 8


def test_changed_source_chat_cannot_match_and_unrelated_fact_is_not_substituted(
    services, topics, lexical
):
    with services[1].session.begin() as session:
        session.get(Message, topics[0]["evidence"][0]["message_id"]).content = "已撤回旧条件。"
    assert services[4].prompt_snapshot("真空恢复") == ("", [])
    assert "浅绿色" in services[4].list()[0]["content"]


def test_retrieval_is_scoped_before_documents_reach_the_encoder(services, monkeypatch, tmp_path):
    memory = services[4]
    for owner in ("alpha", "beta"):
        token = request_identity.set({"user": {"id": owner, "role": "user"}})
        try:
            seed_memory(memory, MemorySeed("真空", f"真空恢复由{owner}确认。"))
        finally:
            request_identity.reset(token)
    seen = []

    def scores(_query, documents):
        seen.extend(documents.values())
        return {}

    monkeypatch.setattr(catalog(services[1]).retrieval, "scores", scores)
    token = request_identity.set({"user": {"id": "alpha", "role": "user"}})
    try:
        prompt, _ = memory.prompt_snapshot("真空恢复")
        assert "alpha" in prompt and "beta" not in prompt
        assert seen and all("beta" not in text for text in seen)
        other_root = tmp_path / "other-source"
        other_root.mkdir()
        other = MemoryService(services[0], services[1], Workspace(other_root))
        assert other.prompt_snapshot("真空恢复") == ("", [])
    finally:
        request_identity.reset(token)


def test_local_encoder_failure_uses_lexical_hits_without_full_document_fallback(
    services, topics, monkeypatch
):
    def unavailable():
        raise RuntimeError("model is not installed")

    monkeypatch.setattr("app.modules.knowledge.semantic.local_encoder", unavailable)
    prompt, _ = services[4].prompt_snapshot("真空恢复")
    assert "真空恢复" in prompt and "浅绿色" not in prompt
    assert catalog(services[1]).retrieval.error
    assert services[4].prompt_snapshot("标定精度") == ("", [])


def test_real_local_semantics_can_match_a_paraphrase_without_shared_keywords(services):
    memory = services[4]
    seed_memory(memory, MemorySeed("恢复", "机器停止后重新启动生产，需要先恢复运行条件。"))
    seed_memory(memory, MemorySeed("外观", "界面颜色设置与字体大小。"))
    prompt, rows = memory.prompt_snapshot("停机后如何复工")
    assert not catalog(services[1]).retrieval.error
    assert "恢复运行条件" in prompt and "字体大小" not in prompt
    assert len(rows[0]["source_thread_ids"]) == 1


async def test_runtime_injects_only_current_question_matches_and_honors_source_switch(
    services, topics, lexical, monkeypatch
):
    paths, _, workspace, repository, memory, settings = services
    captured = []
    original = DeterministicModel._generate

    def generate(model, messages, *args, **kwargs):
        captured.append(messages)
        return original(model, messages, *args, **kwargs)

    monkeypatch.setattr(DeterministicModel, "_generate", generate)
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: DeterministicModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memory)
    for question, enabled, expected in (
        ("真空恢复有哪些条件", True, True),
        ("标定精度有哪些要求", True, False),
        ("真空恢复有哪些条件", False, False),
    ):
        captured.clear()
        run = repository.create_run(None, question, [], source_options={"use_memory": enabled})
        await runtime.execute(
            run,
            lambda kind, payload, run_id=run["id"]: repository.event(run_id, kind, payload),
        )
        model_context = "\n".join(message.text for batch in captured for message in batch)
        assert ("真空恢复前需确认负压已释放。" in model_context) is expected
        assert "界面背景选择浅绿色。" not in model_context
        event = repository.latest_event(run["thread_id"], "context_sources")
        assert bool(event["memories"]) is expected
