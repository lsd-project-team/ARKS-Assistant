"""复核必须收到本轮读过的相关源码，不能只凭回答中的引用裁掉调用依据。"""

import json

from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.agents.runtime.engine import AgentRuntime
from app.modules.chat.models import Run
from app.modules.projects.models import Project
from app.modules.source_analysis.evidence import SourceEvidence, SourceEvidenceGuard, source_excerpt
from app.modules.source_analysis.review import review_answer
from tests.helpers.models import DeterministicModel
from tests.helpers.reviews import CapturingReviewer


async def test_review_includes_current_caller_read_even_without_its_own_citation(services):
    workspace = services[2]
    caller = workspace.root / "Caller.cs"
    caller.write_text("class Caller {\n void Run() {\n Program.Main();\n }\n}\n", encoding="utf-8")
    evidence = SourceEvidence(workspace, lambda *_: None, required=True)
    evidence.record(source_excerpt(workspace, "Program.cs", 1, 3))
    evidence.record(source_excerpt(workspace, "Caller.cs", 1, 5))
    model = CapturingReviewer()
    answer = "Caller.cs 调用 Main，入口见[原件](source:Program.cs#L2)。"

    await review_answer(model, evidence, answer)

    (payload,) = model.requests
    blocks = {row["path"]: row for row in payload["source"]}
    assert set(blocks) == {"Program.cs", "Caller.cs"}
    assert blocks["Caller.cs"]["version"] == workspace.read("Caller.cs")["version"]
    assert blocks["Caller.cs"]["lines"][2] == {"line": 3, "text": " Program.Main();"}


async def test_changed_uncited_read_is_omitted_with_reason_instead_of_sending_new_version(services):
    workspace = services[2]
    caller = workspace.root / "Caller.cs"
    caller.write_text("class OldCaller {}\n", encoding="utf-8")
    evidence = SourceEvidence(workspace, lambda *_: None, required=True)
    evidence.record(source_excerpt(workspace, "Program.cs", 1, 3))
    evidence.record(source_excerpt(workspace, "Caller.cs", 1, 1))
    caller.write_text("class NewCaller {}\n", encoding="utf-8")
    model = CapturingReviewer()

    await review_answer(model, evidence, "Caller.cs 尚需核对，[入口](source:Program.cs#L2)。")

    (payload,) = model.requests
    assert [row["path"] for row in payload["source"]] == ["Program.cs"]
    assert payload["source_omissions"] == [{"path": "Caller.cs", "reason": "version_changed"}]


async def test_large_uncited_read_cannot_hide_required_source_or_exceed_review_input(services):
    workspace = services[2]
    (workspace.root / "Large.txt").write_text("unused = 1;" * 20000, encoding="utf-8")
    evidence = SourceEvidence(workspace, lambda *_: None, required=True)
    evidence.record(source_excerpt(workspace, "Large.txt", 1, 1))
    evidence.record(source_excerpt(workspace, "Program.cs", 1, 3))
    model = CapturingReviewer()

    await review_answer(model, evidence, "入口见[当前文件](source:Program.cs#L2)。")

    (payload,) = model.requests
    assert [row["path"] for row in payload["source"]] == ["Program.cs"]
    assert payload["source_omissions"] == [{"path": "Large.txt", "reason": "budget"}]


async def test_source_ranges_merge_without_duplicate_body_or_unread_file(services):
    workspace = services[2]
    (workspace.root / "Unread.cs").write_text("class Unread {}\n", encoding="utf-8")
    evidence = SourceEvidence(workspace, lambda *_: None, required=True)
    evidence.record(source_excerpt(workspace, "Program.cs", 1, 3))
    evidence.record(source_excerpt(workspace, "Program.cs", 2, 2))
    model = CapturingReviewer()

    await review_answer(model, evidence, "Main 在[当前文件](source:Program.cs#L2)。")

    (payload,) = model.requests
    assert len(payload["source"]) == 1
    assert [row["line"] for row in payload["source"][0]["lines"]] == [1, 2, 3]
    assert "Unread.cs" not in str(payload)


async def test_verified_empty_file_is_provided_without_inventing_a_source_line(services):
    workspace = services[2]
    (workspace.root / "Empty.cs").write_bytes(b"")
    evidence = SourceEvidence(workspace, lambda *_: None, required=True)
    evidence.record(source_excerpt(workspace, "Empty.cs"))
    model = CapturingReviewer()

    await review_answer(model, evidence, "Empty.cs当前为空，没有源码行号可引用。")

    (payload,) = model.requests
    (block,) = payload["source"]
    assert block["path"] == "Empty.cs" and block["empty_file"] and block["lines"] == []


async def test_source_changed_during_review_cannot_keep_a_passed_review_or_stale_link(services):
    workspace = services[2]
    events = []
    evidence = SourceEvidence(workspace, lambda *event: events.append(event), required=True)
    evidence.record(source_excerpt(workspace, "Program.cs", 1, 3))

    class ChangedReviewer(CapturingReviewer):
        async def ainvoke(self, messages, **options):
            (workspace.root / "Program.cs").write_text("class Changed {}\n", encoding="utf-8")
            return await super().ainvoke(messages, **options)

    async def handler(_request):
        return ModelResponse(result=[AIMessage(content="入口见[原件](source:Program.cs#L2)。")])

    response = await SourceEvidenceGuard(evidence, ChangedReviewer()).awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[]),
        handler,
    )

    reviews = [row for kind, row in events if kind == "source_review"]
    assert reviews[-1]["verdict"] == "unknown"
    assert (
        "已变化" in response.result[0].text
        and "source:Program.cs#L2" not in response.result[0].text
    )
    assert "引用未核对" in response.result[0].text


async def test_resumed_run_restores_only_the_change_reference_and_reloads_current_archive(
    services,
    monkeypatch,
):
    paths, database, workspace, repository, memory, settings = services
    repository.project_id = "resume-review-project"
    with database.session.begin() as session:
        session.add(
            Project(
                id=repository.project_id,
                name="恢复复核测试",
                source_root=str(workspace.root),
            )
        )
    runtime = AgentRuntime(paths, settings, workspace, repository, memory)
    created = runtime.code_changes.create("已有副本", "尚未执行命令")
    previous = repository.create_run(None, "核对 Program.cs", [])
    source = source_excerpt(workspace, "Program.cs", 1, 3)
    repository.event(
        previous["id"],
        "source_evidence",
        {
            "path": source["path"],
            "version": source["version"],
            "start_line": 1,
            "end_line": 3,
            "reason": "read_source",
        },
    )
    repository.event(previous["id"], "code_change_reference", {"id": created["id"]})
    repository.set_status(previous["id"], "interrupted")

    class ResumeModel(DeterministicModel):
        reviewed: list = Field(default_factory=list)

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if "独立的源码结论复核器" in messages[0].text:
                self.reviewed.append(json.loads(messages[-1].text))
                content = '{"verdict":"passed","issues":[]}'
            else:
                content = "已有副本未执行命令；入口见[当前文件](source:Program.cs#L2)。"
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    model = ResumeModel()
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_a, **options: DeterministicModel() if options.get("summary") else model,
    )
    current = repository.create_run(
        previous["thread_id"],
        "核对 Program.cs 和已有副本",
        [],
        {
            "use_memory": False,
            "use_knowledge": False,
            "use_deepwiki": False,
        },
    )
    with database.session.begin() as session:
        session.get(Run, current["id"]).resumed_from = previous["id"]
    try:
        await runtime.execute(
            repository.run(current["id"]),
            lambda kind, payload: repository.event(current["id"], kind, payload),
        )
        (payload,) = model.reviewed
        assert payload["user_request"] == "核对 Program.cs 和已有副本"
        assert [row["id"] for row in payload["code_work"]["changes"]] == [created["id"]]
        assert payload["code_work"]["changes"][0]["verifications"] == []
        assert payload["code_work"]["changes"][0]["request_binding"] is None
        contexts = [
            row["payload"]
            for row in repository.events(current["id"], 0)
            if row["kind"] == "source_review_context"
        ]
        assert contexts[-1]["changes"][0]["id"] == created["id"]
    finally:
        await runtime.code_changes.shutdown()
        runtime.semantic.close()
