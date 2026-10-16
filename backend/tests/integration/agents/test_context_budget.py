"""用真实 Agent 框架验证预算边界；所有模型调用使用本地确定性替身。"""

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_core.exceptions import ContextOverflowError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.context.tokens import (
    estimate_tokens,
    fit_text,
    input_budget,
    request_budget,
    text_tokens,
)
from app.agents.runtime.engine import AgentRuntime
from app.agents.runtime.feedback import error_feedback
from app.core.config import AppSettings, McpSettings, ModelSettings
from app.modules.chat.context import ConversationContext
from app.modules.chat.schemas import MemoryWrite, SummaryCorrection
from tests.helpers.models import DeterministicModel


def wiki_tool(description="读取项目说明"):
    def lookup(topic: str) -> str:
        return topic

    return StructuredTool.from_function(lookup, name="mcp_wiki_lookup", description=description)


def test_full_counter_includes_schemas_and_tool_arguments():
    message = AIMessage(
        content="",
        tool_calls=[{"name": "lookup", "args": {"topic": "架构" * 5000}, "id": "call1"}],
    )
    assert estimate_tokens([message]) > 9000
    short = [HumanMessage(content="说明入口")]
    assert estimate_tokens(short, tools=[wiki_tool("工具说明" * 3000)]) > 10000
    original = "中文🙂与 C# 参数\r\n" * 1000
    prefix = fit_text(original, 257)
    assert original.startswith(prefix) and text_tokens(prefix) <= 257
    assert text_tokens(original[: len(prefix) + 1]) > 257


def test_breakdown_does_not_double_count_memory_or_selection():
    memory = "已核实的用户偏好" * 60
    request = ModelRequest(
        model=DeterministicModel(),
        system_message=SystemMessage(content="系统提示\n" + memory),
        messages=[
            HumanMessage(
                content="说明\n<code_selection path='Program.cs'>\n源码\n</code_selection>"
            )
        ],
        tools=[wiki_tool()],
    )
    budget = request_budget(request, 8192, 512, memory)
    assert all(value > 0 for value in budget["breakdown"].values())
    assert sum(budget["breakdown"].values()) == budget["tokens"]
    assert budget["tokens"] == estimate_tokens(
        [request.system_message, *request.messages], tools=request.tools
    )
    assert budget["input_limit"] + budget["output_reserved"] + budget["headroom"] == 8192


def test_memory_injection_respects_token_budget_and_preserves_original(services):
    _, _, _, _, memories, _ = services
    original = "用户偏好：默认中文回答。\n" + "稳定偏好" * 1000
    saved = memories.save(MemoryWrite(name="偏好.md", scope="user", content=original))
    memories.save(MemoryWrite(name="项目.md", content="入口：Program.cs\n" + "项目事实" * 1000))
    prompt, selected = memories.prompt_snapshot("Program.cs 入口", max_tokens=400)
    assert text_tokens(prompt) <= 400
    assert selected[0]["scope"] == "user" and selected[0]["partial"]
    assert "源码来源：" in selected[0]["injected_text"]
    assert memories.read("user", "偏好.md")["content"] == original
    assert memories.read("user", "偏好.md")["version"] == saved["version"]


async def test_framework_budget_snapshot_survives_configuration_change(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    configuration = AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=512))
    settings.save(configuration)
    memories.save(MemoryWrite(name="偏好.md", scope="user", content="回答偏好：中文"))
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: DeterministicModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("预算快照")
    run = repository.create_run(
        thread["id"],
        "解释入口",
        [
            {
                "path": "Program.cs",
                "start_line": 1,
                "end_line": 2,
                "content": "class Program {\n static void Main() {}",
                "version": "a" * 64,
            }
        ],
    )
    answer = await runtime.execute(
        run, lambda kind, payload: repository.event(run["id"], kind, payload)
    )
    repository.finish(run["id"], answer)
    snapshot = ConversationContext(runtime).run_sources(run["id"])["budget"]
    assert snapshot["complete"] and snapshot["phase"] == "model_request"
    assert all(value > 0 for value in snapshot["breakdown"].values())
    assert snapshot["tokens"] <= snapshot["input_limit"]
    settings.save(AppSettings(model=ModelSettings(context_tokens=32768)))
    restored = await ConversationContext(runtime).read(thread["id"])
    assert restored["limit"] == 16384 and restored["output_reserved"] == 512
    # 引用纠正可包含临时提示；下一轮状态预算应和运行收尾一致，而非保留临时开销。
    assert restored["tokens"] == repository.latest_event(thread["id"], "context")["tokens"]


async def test_tool_overhead_triggers_native_compaction_without_losing_originals(
    services, monkeypatch
):
    paths, _, workspace, repository, memories, settings = services
    limit, output = 8192, 512
    settings.save(AppSettings(model=ModelSettings(context_tokens=limit, output_tokens=output)))
    generated = []
    original_generate = DeterministicModel._generate

    def capture(model, messages, *args, **kwargs):
        generated.append(messages)
        return original_generate(model, messages, *args, **kwargs)

    monkeypatch.setattr(DeterministicModel, "_generate", capture)
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: DeterministicModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("全请求压缩")
    initial = repository.create_run(thread["id"], "准备", [])
    repository.finish(
        initial["id"],
        await runtime.execute(
            initial, lambda kind, payload: repository.event(initial["id"], kind, payload)
        ),
    )
    frame = repository.latest_event(thread["id"], "context_budget")["breakdown"]
    overhead = frame["system"] + frame["tools"] + frame["memory"]
    threshold = min(int(limit * 0.75), int(input_budget(limit, output) * 0.9))
    length = max(20, (threshold - overhead + 500) // 12)
    history = []
    for index in range(6):
        old = repository.create_run(thread["id"], f"原问题{index}:" + "中" * length, [])
        history += [
            HumanMessage(
                content=repository.message(old["message_id"])["content"], id=old["message_id"]
            ),
            AIMessage(content="答" * length),
        ]
        repository.finish(old["id"], "答" * length)
    async with AsyncSqliteSaver.from_conn_string(str(paths.data / "checkpoints.sqlite3")) as saver:
        graph = await runtime.graph(thread["id"], saver, lambda *_args: None)
        await graph.aupdate_state(
            {"configurable": {"thread_id": thread["id"]}}, {"messages": history}, as_node="model"
        )
    assert estimate_tokens(history) < threshold
    old_contents = [row["content"] for row in repository.thread(thread["id"])["messages"]]
    following = repository.create_run(thread["id"], "继续", [])
    repository.finish(
        following["id"],
        await runtime.execute(
            following, lambda kind, payload: repository.event(following["id"], kind, payload)
        ),
    )
    events = repository.events(following["id"])
    assert any(row["kind"] == "stage" and row["payload"]["stage"] == "compacting" for row in events)
    budgets = [row["payload"] for row in events if row["kind"] == "context_budget"]
    assert budgets[0]["tokens"] > threshold
    assert budgets[-1]["tokens"] <= input_budget(limit, output)
    context = ConversationContext(runtime)
    shown = await context.read(thread["id"])
    assert shown["summary"].startswith("目标：")
    assert "conversation_history" not in shown["summary"]
    corrected = await context.correct(
        thread["id"], SummaryCorrection(summary="纠正后的目标与待办", version=shown["version"])
    )
    assert corrected["summary"] == "纠正后的目标与待办"
    async with AsyncSqliteSaver.from_conn_string(str(paths.data / "checkpoints.sqlite3")) as saver:
        graph = await runtime.graph(thread["id"], saver, lambda *_args: None, inspection=True)
        state = await graph.aget_state({"configurable": {"thread_id": thread["id"]}})
    raw = state.values["_summarization_event"]["summary_message"].text
    assert "conversation_history" in raw and "<summary>\n纠正后的目标与待办\n</summary>" in raw
    summaries = [messages for messages in generated if "Context Extraction" in messages[0].text]
    assert summaries and all(
        estimate_tokens(messages) <= input_budget(limit, output) for messages in summaries
    )
    assert any(
        "原问题0" in file.read_text(encoding="utf-8") for file in paths.scratch.rglob("*.md")
    )
    assert [row["content"] for row in repository.thread(thread["id"])["messages"]][
        : len(old_contents)
    ] == old_contents


@pytest.mark.parametrize("oversized", ["tools", "selection"])
async def test_irreducible_request_is_not_sent_and_keeps_original(services, monkeypatch, oversized):
    paths, _, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(
            model=ModelSettings(context_tokens=8192, output_tokens=512),
            deepwiki_repo="example/project" if oversized == "tools" else "",
            mcp_servers=[McpSettings(id="wiki", name="DeepWiki", url="https://example.com/mcp")]
            if oversized == "tools"
            else [],
        )
    )
    called = []

    def generate(*_args, **_kwargs):
        called.append(True)
        raise AssertionError("已知超量请求不应发送")

    monkeypatch.setattr(DeterministicModel, "_generate", generate)
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_args, **_kwargs: DeterministicModel(),
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    if oversized == "tools":

        async def remote(*_args):
            return [wiki_tool("很长的外部工具定义" * 20000)]

        monkeypatch.setattr(runtime, "remote_tools", remote)
    selections = (
        []
        if oversized == "tools"
        else [
            {
                "path": "Program.cs",
                "start_line": 1,
                "end_line": 2,
                "content": "完整选区原文" * 20000,
                "version": "a" * 64,
            }
        ]
    )
    thread = repository.create_thread("超量原文保护")
    run = repository.create_run(thread["id"], "请解释", selections)
    with pytest.raises(ContextOverflowError) as rejected:
        await runtime.execute(run, lambda kind, payload: repository.event(run["id"], kind, payload))
    assert not called
    message = repository.message(run["message_id"])
    assert message["content"] == "请解释" and message["selections"] == selections
    assert error_feedback(rejected.value, settings.load().model)["code"] == "context_limit"
    assert repository.latest_event(thread["id"], "context_budget")["tokens"] > input_budget(
        8192, 512
    )


async def test_legacy_record_does_not_claim_a_complete_budget(services):
    paths, _, workspace, repository, memories, settings = services
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("旧记录")
    context = await ConversationContext(runtime).read(thread["id"])
    assert not context["complete"] and context["basis"] == "legacy_messages"
    assert "system" not in context["breakdown"]
