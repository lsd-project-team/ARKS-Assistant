"""通过真实运行生命周期验证命令录库与后续问答，模型返回使用可核对的固定数据。"""

import json
import time

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.tools.debug_capture import ExtractedIssue, command_text, grounded
from app.main import create_app
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from tests.helpers.accounts import sign_in
from tests.helpers.models import DeterministicModel

pytestmark = pytest.mark.authentication

ORIGINAL = "S1 取片真空报警 E901。检查发现密封圈破损。更换密封圈后连续取片20次正常，问题已解决。"
EXTRACTED = {
    "title": "取片真空报警 E901",
    "payload": {
        "problem": "S1 取片真空报警 E901",
        "investigation": "检查发现密封圈破损",
        "cause": "密封圈破损",
        "solution": "更换密封圈",
        "verification": "连续取片20次正常",
        "resolution_status": "resolved",
        "keywords": ["S1", "E901", "真空"],
    },
}


class ExtractModel:
    def __init__(self, response):
        self.response, self.calls = response, 0

    async def ainvoke(self, _messages):
        self.calls += 1
        return AIMessage(content=self.response)


def terminal(client, run):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        current = client.get(f"/api/p/independent/runs/{run['id']}").json()
        if current["status"] in {"completed", "failed", "cancelled"}:
            return current
        time.sleep(0.02)
    pytest.fail("运行未在测试期限内结束")


class HistoricalAnswer(DeterministicModel):
    @property
    def _llm_type(self):
        return "historical-test"

    def bind_tools(self, _tools, **_kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        prompt = str(messages[0].content)
        if "你只负责筛选资料" in prompt or "你负责核查历史经验回答" in prompt:
            return super()._generate(messages, stop, run_manager, **kwargs)
        assert "debug_issue_records" in prompt and "更换密封圈" in prompt
        assert '"处理状态": "记录人反馈已解决"' in prompt
        assert "resolution_status" not in prompt
        source = prompt.split('"citation": "debug-issue:')[1].split('"')[0]
        answer = f"历史 E901 记录中，更换密封圈后连续取片20次正常。[调试记录](debug-issue:{source})"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=answer))])


def test_command_persists_actual_user_and_raw_text_retry_deduplicates_then_qa_cites(
    services, monkeypatch
):
    model = ExtractModel(json.dumps(EXTRACTED, ensure_ascii=False))
    monkeypatch.setattr("app.agents.tools.debug_capture.create_model", lambda *_: model)
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_, **_kwargs: HistoricalAnswer()
    )
    with TestClient(create_app(services[0])) as client:
        user = sign_in(client, "user").json()["user"]
        response = client.post(
            "/api/p/independent/threads/start", json={"content": "/记录问题\n" + ORIGINAL}
        )
        assert response.status_code == 201, response.text
        run = response.json()
        done = terminal(client, run)
        assert done["status"] == "completed", done
        issues = DebugIssues(HandoverStore(database=client.app.state.auth.database))
        (row,) = issues.rows()
        assert row["payload"]["original_text"] == ORIGINAL
        assert row["payload"]["reported_by"] == user["display_name"]
        assert row["payload"]["source_message_id"] == run["message_id"]
        assert row["payload"]["source_thread_id"] == run["thread_id"]
        thread = client.get(f"/api/p/independent/threads/{run['thread_id']}").json()
        assert f"debug-issue:{row['id']}/1" in thread["messages"][-1]["content"]
        again = client.post(f"/api/p/independent/runs/{run['id']}/regenerate").json()
        assert terminal(client, again)["status"] == "completed"
        assert len(issues.rows()) == 1 and model.calls == 1
        # 后续问题出现后，历史命令重答追加展示，仍复用原消息的录库提交键。
        later = client.post(
            f"/api/p/independent/threads/{run['thread_id']}/runs",
            json={"content": "取片真空报警 E901，之前如何处理的？"},
        ).json()
        assert terminal(client, later)["status"] == "completed"
        historical = client.post(f"/api/p/independent/runs/{run['id']}/regenerate").json()
        assert historical["message_id"] != run["message_id"]
        assert terminal(client, historical)["status"] == "completed"
        assert len(issues.rows()) == 1 and model.calls == 1
        # 独立的新对话也从全局问题库检索，不依赖上一轮消息碰巧留在上下文里。
        followup = client.post(
            "/api/p/independent/threads/start",
            json={"content": "取片又发生真空报警 E901，之前如何处理的？"},
        ).json()
        final = terminal(client, followup)
        assert final["status"] == "completed", final.get("error")
        answer = client.get(f"/api/p/independent/threads/{followup['thread_id']}").json()[
            "messages"
        ][-1]["content"]
        assert "更换密封圈" in answer and f"debug-issue:{row['id']}/1" in answer
        context = client.get(f"/api/p/independent/runs/{followup['id']}/context").json()
        assert context["debug_issues"][0]["id"] == row["id"]


@pytest.mark.parametrize(
    "bad_reply", ["不是JSON", json.dumps({**EXTRACTED, "payload": {"problem": "不存在的事实"}})]
)
def test_failed_ai_extraction_never_claims_saved_or_creates_record(
    services, monkeypatch, bad_reply
):
    model = ExtractModel(bad_reply)
    monkeypatch.setattr("app.agents.tools.debug_capture.create_model", lambda *_: model)
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        run = client.post(
            "/api/p/independent/threads/start", json={"content": "/记录问题 " + ORIGINAL}
        ).json()
        done = terminal(client, run)
        assert done["status"] == "failed" and "尚未录入" in done["error"]
        assert model.calls == 2
        assert not DebugIssues(HandoverStore(database=client.app.state.auth.database)).rows()


@pytest.mark.parametrize(
    "content", ["/记录问题", "/记录问题 " + "字" * 30001], ids=["empty", "overlong"]
)
def test_invalid_command_body_does_not_invoke_model(services, monkeypatch, content):
    def unexpected(*_):
        pytest.fail("无效输入不应调用模型")

    monkeypatch.setattr("app.agents.tools.debug_capture.create_model", unexpected)
    with TestClient(create_app(services[0])) as client:
        sign_in(client, "user")
        response = client.post("/api/p/independent/threads/start", json={"content": content})
        if response.status_code == 422:
            assert len(content) > 30000
            return
        run = response.json()
        assert terminal(client, run)["status"] == "failed"
        assert not DebugIssues(HandoverStore(database=client.app.state.auth.database)).rows()


def test_only_explicit_leading_command_is_a_write_request():
    assert command_text(" /记录问题\n异常") == "异常"
    assert command_text("/record-issue text") == "text"
    for content in (
        "解释 /记录问题 的用法",
        "/记录问题的用法",
        "普通提问",
        "```\n/记录问题 abc\n```",
    ):
        assert command_text(content) is None


def test_capture_classifies_work_progress_but_requires_original_author_and_date_to_be_grounded():
    original = "贺强 9月1日 15:49：8月28日，来料延期，已与销售沟通。"
    value = ExtractedIssue(
        title="来料延期",
        payload={
            "record_type": "progress",
            "problem": "来料延期，已与销售沟通",
            "recorded_by": "贺强",
            "recorded_at": "9月1日 15:49",
            "occurred_on": "8月28日",
        },
    )
    assert grounded(value, original).payload.resolution_status == "recorded"
    invented = value.model_copy(deep=True)
    invented.payload.recorded_at = "2026年9月1日 15:49"
    with pytest.raises(ValueError, match="recorded_at"):
        grounded(invented, original)
