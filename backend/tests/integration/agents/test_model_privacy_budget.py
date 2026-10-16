"""供应商请求边界：真实 LangChain 回调与临时账本，只有供应商模型使用替身。"""

import asyncio
import copy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult, Generation, LLMResult
from pydantic import Field

from app.agents.context.budget import ContextBudget
from app.agents.runtime.model_budget import ProjectModelBudget, usage_tokens
from app.agents.runtime.privacy import MASK, redact, redact_messages
from app.agents.tools.debug_capture import capture_command
from app.core.config import AppSettings, ModelSettings
from app.modules.code_changes.policy import WorkPolicy
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.memory.conflicts import review_pairs
from app.modules.projects.models import Project
from app.modules.source_analysis.evidence import SourceEvidence, source_excerpt
from app.modules.source_analysis.review import review_answer
from tests.helpers.models import DeterministicModel


@pytest.fixture
def ledger(services, monkeypatch):
    paths, database, *_ = services
    ledger = WorkPolicy(paths, database, "provider-project")
    ledger.save({"reading_token_limit": 1000})
    monkeypatch.setattr(WorkPolicy, "day", staticmethod(lambda: "2026-10-16"))
    return ledger


class ObservedProvider(DeterministicModel):
    seen: list = Field(default_factory=list)
    usage: dict | None = None
    failure: bool = False
    answer: str = "完成"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(copy.deepcopy(messages))
        if self.failure:
            raise RuntimeError("simulated provider failure")
        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content=self.answer, usage_metadata=self.usage))
            ]
        )


class BlockingProvider(ObservedProvider):
    entered: asyncio.Event = Field(default_factory=asyncio.Event)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.entered.set()
        await asyncio.Event().wait()
        raise AssertionError("阻塞供应商只应通过测试取消退出")


@pytest.mark.parametrize(
    "text",
    [
        "class Program {\r\n  public void Run() {}\r\n}\r\n",
        '{\r\n  "title" : "正常资料",\r\n  "values" : [1, 2, 3]\r\n}\r\n',
        '{\n  "content": "class A {\\n  void Go() {}\\n}",\n  "version": "a123"\n}',
        '  [ {"line": 4, "text": "中文和 \\u4e2d 编码保留"} ]  ',
    ],
)
def test_redaction_preserves_nonsecret_source_exactly(text):
    assert redact(text) == text


@pytest.mark.parametrize(
    ("source", "secret"),
    [
        ('const string api_key = "dummy-value";\r\nNext();', "dummy-value"),
        ('password = "with\\"escaped-value";\nNext();', "escaped-value"),
        ("API_KEY=example-env-value\nNEXT=value", "example-env-value"),
        ("OPENAI_API_KEY=example-vendor-value\nNEXT=value", "example-vendor-value"),
        ("Server=db;Pwd=x;User=guest", "Pwd=x"),
        ("Authorization: Bearer short\r\n", "short"),
        ('<add key="ApiKey" value="xml-dummy" />\n', "xml-dummy"),
        ("<Password>xml-dummy</Password>\r\n", "xml-dummy"),
        (
            "-----BEGIN PRIVATE KEY-----\r\nFAKE-KEY\r\n\r\nFAKE-END\r\n"
            "-----END PRIVATE KEY-----\r\nNext();",
            "FAKE-KEY",
        ),
    ],
)
def test_common_credentials_are_masked_without_changing_line_terminators(source, secret):
    import re

    changed = redact(source)
    assert secret not in changed and MASK in changed
    assert re.findall(r"\r\n|\r|\n", changed) == re.findall(r"\r\n|\r|\n", source)
    assert redact(changed) == changed


def test_json_redacts_only_value_spans_and_embedded_source_preserves_source_line_numbers():
    source = 'class A {\r\n  string password = "dummy-secret";\r\n  void Go() {}\r\n}'
    payload = '{\r\n  "content" : ' + json.dumps(source) + ',\r\n  "line": 20\r\n}'
    changed = redact(payload)
    decoded = json.loads(changed)
    assert "dummy-secret" not in changed
    assert decoded["content"].splitlines()[2] == "  void Go() {}"
    assert '\r\n  "line": 20\r\n}' in changed
    assert decoded["content"].count("\r\n") == source.count("\r\n")
    assert "dummy-secret" in source and "dummy-secret" in payload


def test_json_secret_objects_numbers_and_escaped_keys_are_removed_without_losing_lines():
    raw = '{\n "pass\\u0077ord": 1234,\n "private_key": {\n "part": "fake-key"\n },\n "safe": 9\n}'
    changed = redact(raw)
    payload = json.loads(changed)
    assert payload == {"password": MASK, "private_key": MASK, "safe": 9}
    assert changed.count("\n") == raw.count("\n")
    assert "fake-key" not in changed
    assert redact({"AWS_SECRET_ACCESS_KEY": "aws-dummy", "azureApiKey": "azure-dummy"}) == {
        "AWS_SECRET_ACCESS_KEY": MASK,
        "azureApiKey": MASK,
    }


def test_message_copy_masks_tool_arguments_and_keeps_ids_and_originals():
    message = AIMessage(
        content="",
        id="answer-id",
        tool_calls=[{"name": "send", "id": "call-1", "args": {"api_key": "fake-api-value"}}],
        additional_kwargs={
            "function_call": {"name": "send", "arguments": '{"password":"fake-pwd"}'}
        },
    )
    original = copy.deepcopy(message.model_dump())
    changed = redact_messages([message])[0]
    assert changed.tool_calls[0]["args"]["api_key"] == MASK
    assert changed.tool_calls[0]["id"] == "call-1" and changed.id == "answer-id"
    assert "fake-pwd" not in changed.additional_kwargs["function_call"]["arguments"]
    assert message.model_dump() == original


async def test_real_langchain_boundary_masks_request_and_preserves_local_source(ledger, tmp_path):
    source = 'class A {\n string password = "local-dummy-secret";\n void Go() {}\n}'
    original = tmp_path / "source.cs"
    original.write_text(source, encoding="utf-8")
    model = ObservedProvider(
        callbacks=[ProjectModelBudget(ledger, 1_000_000, output_tokens=256)],
        usage={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
    )
    system = SystemMessage(content='api_key="system-dummy-secret"')
    tool = ToolMessage(content=json.dumps({"content": source}), tool_call_id="source-1")
    request = ModelRequest(model=model, system_message=system, messages=[tool])
    middleware = ContextBudget(16384, 256, "", lambda *_: None)

    async def invoke(prepared):
        reply = await prepared.model.ainvoke([prepared.system_message, *prepared.messages])
        return ModelResponse(result=[reply])

    response = await middleware.awrap_model_call(request, invoke)
    assert response.result[0].content == "完成"
    sent = model.seen[0]
    assert "system-dummy-secret" not in sent[0].content
    assert "local-dummy-secret" not in sent[1].content
    assert json.loads(sent[1].content)["content"].splitlines()[2] == " void Go() {}"
    assert original.read_text(encoding="utf-8") == source
    assert tool.content == json.dumps({"content": source})
    assert ledger.tokens()["reserved_tokens"] == 120 and ledger.tokens()["actual_tokens"] == 120


async def test_memory_conflict_direct_provider_call_masks_proposed_and_existing_records():
    content = '运行模式开启，password="proposed-dummy"'
    candidates = [{"name": "模式", "content": '运行模式关闭，api_key="existing-dummy"'}]
    model = ObservedProvider(
        answer=json.dumps(
            [
                {
                    "name": "模式",
                    "relation": "conflict",
                    "reason": "模式相反",
                    "left_quote": "运行模式开启",
                    "right_quote": "运行模式关闭",
                }
            ],
            ensure_ascii=False,
        )
    )
    checked, _ = await review_pairs(model, content, candidates)
    assert checked == {"模式": {"relation": "conflict", "reason": "模式相反"}}
    sent = model.seen[0][1].content
    assert "proposed-dummy" not in sent and "existing-dummy" not in sent
    assert "proposed-dummy" in content and "existing-dummy" in candidates[0]["content"]


async def test_source_audit_direct_provider_call_masks_current_source_and_keeps_version(services):
    _, _, workspace, *_ = services
    path = workspace.root / "Program.cs"
    path.write_text(
        'class Program {\n string password="source-audit-dummy";\n}\n', encoding="utf-8"
    )
    evidence = SourceEvidence(workspace, lambda *_: None, required=True)
    snapshot = source_excerpt(workspace, "Program.cs", 1, 3)
    evidence.record(snapshot)
    model = ObservedProvider(answer='{"verdict":"passed","issues":[]}')
    answer = "文件有字段。[字段](source:Program.cs#L2)"
    result = await review_answer(model, evidence, answer)
    assert result["verdict"] == "passed"
    sent = json.loads(model.seen[0][1].content)
    assert "source-audit-dummy" not in json.dumps(sent)
    assert sent["source"][0]["version"] == snapshot["version"]
    assert "source-audit-dummy" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("project", [False, True])
async def test_debug_capture_masks_provider_preserves_raw_record_and_only_budgets_project(
    services, monkeypatch, project
):
    from app.agents.runtime.engine import AgentRuntime

    paths, database, workspace, repository, memories, settings = services
    if project:
        with database.session.begin() as session:
            session.add(Project(id="provider-project", name="预算项目"))
        repository.project_id = "provider-project"
    settings.save(AppSettings(model=ModelSettings(context_tokens=8192, output_tokens=256)))
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    runtime.code_changes.policy.save({"reading_token_limit": 10000})
    model = ObservedProvider(
        answer='{"title":"真空报警","payload":{"problem":"真空报警","resolution_status":"open"}}',
        usage={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
    )
    monkeypatch.setattr("app.agents.tools.debug_capture.create_model", lambda _: model)
    thread = repository.create_thread("调试记录")
    original = '真空报警。password="debug-capture-dummy"'
    run = repository.create_run(thread["id"], "/记录问题 " + original, [])
    owned = []
    answer = await capture_command(runtime, run, lambda *_: None, owned)
    assert "已保存" in answer and owned == [model]
    (row,) = DebugIssues(HandoverStore(database=database)).rows()
    assert row["payload"]["original_text"] == original
    assert "debug-capture-dummy" not in model.seen[0][1].content
    assert runtime.code_changes.policy.tokens()["actual_tokens"] == (120 if project else 0)


async def test_real_langchain_rejects_start_before_provider_when_budget_insufficient(ledger):
    ledger.reserve(800)
    model = ObservedProvider(callbacks=[ProjectModelBudget(ledger, 1000)])
    with pytest.raises(ValueError, match="预算不足"):
        await model.ainvoke([HumanMessage(content="检查预算")])
    assert model.seen == []
    assert ledger.tokens()["calls"] == 1 and ledger.tokens()["reserved_tokens"] == 800


@pytest.mark.parametrize("failure", [False, True])
async def test_provider_unknown_usage_and_error_keep_reservation(ledger, failure):
    model = ObservedProvider(callbacks=[ProjectModelBudget(ledger, 1000)], failure=failure)
    if failure:
        with pytest.raises(RuntimeError, match="simulated provider failure"):
            await model.ainvoke([HumanMessage(content="消息")])
    else:
        await model.ainvoke([HumanMessage(content="消息")])
    assert ledger.tokens()["reserved_tokens"] == 1000
    assert ledger.tokens()["actual_tokens"] == 0
    assert ledger.tokens()["calls"] == 1


async def test_cancelled_provider_keeps_unknown_cost_and_releases_callback_state(ledger):
    callback = ProjectModelBudget(ledger, 1000)
    model = BlockingProvider(callbacks=[callback])
    task = asyncio.create_task(model.ainvoke([HumanMessage(content="消息")]))
    await asyncio.wait_for(model.entered.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert ledger.tokens()["reserved_tokens"] == 1000
    assert ledger.tokens()["actual_tokens"] == 0
    assert callback.reservations == {}


def test_usage_counts_all_generations_and_uses_aggregate_without_double_counting():
    def item(total):
        return ChatGeneration(
            message=AIMessage(
                content="ok",
                usage_metadata={"input_tokens": total, "output_tokens": 0, "total_tokens": total},
            )
        )

    response = LLMResult(generations=[[item(100), item(40)], [item(60)]])
    assert usage_tokens(response) == 200
    response.llm_output = {"token_usage": {"total_tokens": 230}}
    assert usage_tokens(response) == 230
    response.generations[1] = [Generation(text="unknown")]
    response.llm_output = None
    assert usage_tokens(response) is None


@pytest.mark.parametrize("value", [True, -1, "200", 1.5])
def test_invalid_provider_usage_does_not_refund_as_actual_zero(value):
    result = SimpleNamespace(generations=[], llm_output={"usage": {"total_tokens": value}})
    assert usage_tokens(result) is None


async def test_duplicate_callbacks_and_zero_usage_only_settle_once(ledger):
    callback = ProjectModelBudget(ledger, 1000)
    run_id = uuid4()
    await asyncio.gather(
        callback.on_chat_model_start({}, [[HumanMessage(content="message")]], run_id=run_id),
        callback.on_chat_model_start({}, [[HumanMessage(content="message")]], run_id=run_id),
    )
    assert ledger.tokens()["calls"] == 1
    response = LLMResult(generations=[], llm_output={"usage": {"total_tokens": 0}})
    await callback.on_llm_end(response, run_id=run_id)
    await callback.on_llm_end(response, run_id=run_id)
    assert ledger.tokens()["reserved_tokens"] == 0 and ledger.tokens()["calls"] == 1


async def test_unlimited_project_allows_large_provider_calls_and_records_actual_usage(ledger):
    ledger.save({"reading_token_limit": None})
    model = ObservedProvider(
        usage={"input_tokens": 1_200_000, "output_tokens": 1000, "total_tokens": 1_201_000},
        callbacks=[ProjectModelBudget(ledger, 2_000_000)],
    )
    for _ in range(2):
        assert (await model.ainvoke([HumanMessage(content="继续分析")])).content == "完成"
    assert len(model.seen) == 2
    assert ledger.tokens()["reserved_tokens"] == 2_402_000
    assert ledger.tokens()["actual_tokens"] == 2_402_000
    assert ledger.tokens()["calls"] == 2


def test_reservation_estimation_includes_tools_and_generation_limit(ledger):
    callback = ProjectModelBudget(ledger, 1_000_000, output_tokens=256)
    messages = [[HumanMessage(content="简短问题")]]
    base = callback.reservation_size(messages)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "tool",
                "description": "详情" * 2000,
                "parameters": {"type": "object"},
            },
        }
    ]
    expanded = callback.reservation_size(messages, invocation_params={"tools": tools})
    assert 256 < base < 1000
    assert expanded > base + 1000
    assert ProjectModelBudget(ledger, 1000).reservation_size(messages) == 1000
