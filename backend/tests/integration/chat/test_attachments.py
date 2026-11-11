import json
import re
import zipfile

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from sqlalchemy import select

from app.agents.runtime.engine import AgentRuntime
from app.agents.tools.attachments import attachment_context, attachment_tools
from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.validation import validate_backup
from app.main import create_app
from app.modules.chat.models import ChatAttachment
from tests.helpers.api_paths import project_api
from tests.helpers.chat_attachments import document_bytes, zip_bytes
from tests.helpers.code_work import FILE, make_work
from tests.helpers.models import DeterministicModel


def upload(client, extension=".xlsx", value=7):
    response = client.post(
        project_api(client, "/attachments"),
        params={"filename": "新需求" + extension},
        content=document_bytes(extension, value),
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_mixed_zip_upload_preview_and_download(services):
    files = {
        "docs/需求" + extension: document_bytes(extension, value)
        for extension, value in [(".pdf", 31), (".docx", 37), (".xlsx", 41), (".csv", 43)]
    }
    data = zip_bytes(files)
    with TestClient(create_app(services[0])) as client:
        response = client.post(
            project_api(client, "/attachments"),
            params={"filename": "资料包.zip"},
            content=data,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 201, response.text
        attachment = response.json()
        assert attachment["filename"] == "资料包.zip"
        assert attachment["parse_status"] == "readable"
        assert attachment["size"] == len(data) and isinstance(attachment["characters"], int)
        prefix = project_api(client, f"/attachments/{attachment['id']}")
        preview = client.get(prefix)
        assert preview.status_code == 200
        content = preview.json()["content"]
        for path, value in zip(files, [31, 37, 41, 43], strict=True):
            assert f"[文件 {path}]" in content and f"NewValue = {value}" in content
        assert client.get(prefix + "/download").content == data


def test_upload_bind_history_queue_edit_fork_download_and_backup(services, monkeypatch):
    monkeypatch.setattr("app.modules.chat.runs.RunManager.start", lambda *args: None)
    with TestClient(create_app(services[0])) as client:
        attachment = upload(client)
        assert "content" not in attachment and attachment["characters"] > 0
        identifier = attachment["id"]
        prefix = project_api(client, f"/attachments/{identifier}")
        page = client.get(prefix, params={"limit": 10}).json()
        assert len(page["content"]) == 10 and page["next_offset"] == 10
        assert client.get(prefix + "/download").content == document_bytes(".xlsx", 7)
        run = client.post(
            project_api(client, "/threads/start"),
            json={"content": "按文档修改代码", "attachment_ids": [identifier]},
        ).json()
        base = project_api(client, f"/threads/{run['thread_id']}")
        conversation = client.get(base).json()
        assert conversation["messages"][0]["attachments"] == [attachment]
        repository = client.app.state.projects.services(conversation["workspace_id"]).repository
        repository.finish(run["id"], "已读文档")
        edited = client.post(
            base + f"/messages/{run['message_id']}/edit", json={"content": "补充修改要求"}
        )
        assert edited.status_code == 201, edited.text
        updated = repository.message(edited.json()["message_id"])
        assert updated["attachments"] == [attachment]
        repository.finish(edited.json()["id"], "补充完成")
        regenerated = repository.regenerate(edited.json()["id"])
        assert repository.message(regenerated["message_id"])["attachments"] == [attachment]
        repository.set_status(regenerated["id"], "interrupted")
        resumed = repository.resume(regenerated["id"])
        assert repository.message(resumed["message_id"])["attachments"] == [attachment]
        repository.finish(resumed["id"], "恢复完成")
        fork = client.post(base + "/fork", json={"message_id": updated["id"]}).json()
        assert client.get(project_api(client, f"/threads/{fork['id']}")).json()["messages"][-1][
            "attachments"
        ] == [attachment]
        repository.queue.pause(run["thread_id"])
        queued = client.post(
            base + "/queue", json={"content": "下一轮", "attachment_ids": [identifier]}
        ).json()["item"]
        changed = client.patch(
            project_api(client, f"/queue/{queued['id']}"),
            json={"content": "下一轮更新", "version": queued["updated_at"]},
        )
        assert changed.status_code == 200 and changed.json()["attachments"] == [attachment]
        repository.queue.pause(run["thread_id"], False)
        dispatched = repository.queue.dispatch(run["thread_id"])
        assert repository.message(dispatched["message_id"])["attachments"] == [attachment]
        assert client.delete(prefix).status_code == 409
        assert attachment["filename"] in client.get(base + "/export").text
        repository.finish(dispatched["id"], "待发完成")
        assert client.delete(base).status_code == 200
        assert client.delete(base + "/permanent").status_code == 200
        assert client.get(prefix).status_code == 200  # 分支仍引用该附件。
    backup = create_backup(services[0])
    assert validate_backup(backup)["valid"]
    with zipfile.ZipFile(backup) as archive:
        assert archive.read(f"scratch/chat-attachments/{identifier}") == document_bytes(".xlsx", 7)


def test_bad_upload_and_invalid_binding_are_atomic(services, monkeypatch):
    monkeypatch.setattr("app.modules.chat.runs.RunManager.start", lambda *args: None)
    with TestClient(create_app(services[0])) as client:
        assert (
            client.post(
                project_api(client, "/attachments?filename=old.doc"), content=b"old"
            ).status_code
            == 409
        )
        assert (
            client.post(
                project_api(client, "/attachments?filename=empty.txt"), content=b""
            ).status_code
            == 409
        )
        attachment = upload(client, ".md")
        for ids in [["missing"], [attachment["id"], attachment["id"]], [attachment["id"]] * 11]:
            response = client.post(
                project_api(client, "/threads/start"),
                json={"content": "修改", "attachment_ids": ids},
            )
            assert response.status_code in {404, 409, 422}
        assert client.get(project_api(client, "/threads")).json() == []
        assert (
            client.delete(project_api(client, f"/attachments/{attachment['id']}")).status_code
            == 200
        )
        assert (
            client.get(project_api(client, f"/attachments/{attachment['id']}")).status_code == 404
        )
        with services[1].session() as session:
            assert not list(session.scalars(select(ChatAttachment)))


class DocumentEditingModel(DeterministicModel):
    attachment_id: str
    target: int = 0
    calls_seen: list[str] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tools = [message for message in messages if isinstance(message, ToolMessage)]
        last = tools[-1] if tools else None
        args = {}
        if last is None:
            assert self.attachment_id in str(messages)
            name, args = "read_chat_attachment", {"attachment_id": self.attachment_id}
        elif last.name == "read_chat_attachment":
            result = json.loads(last.content)
            self.target = int(re.search(r"NewValue\s*=\s*(\d+)", result["content"])[1])
            name = "prepare_code_workspace"
        elif last.name == "prepare_code_workspace":
            name, args = "read_work_file", {"path": FILE}
        elif last.name == "read_work_file":
            name, args = (
                "edit_work_file",
                {
                    "path": FILE,
                    "old_text": "int Value = 1;",
                    "new_text": f"int Value = {self.target};",
                    "version": json.loads(last.content)["version"],
                },
            )
        else:
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(content=f"已按文档修改为 {self.target}，尚未执行仿真。")
                    )
                ]
            )
        self.calls_seen.append(name)
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": f"doc-{len(tools)}",
                                "name": name,
                                "args": args,
                            }
                        ],
                    )
                )
            ]
        )


@pytest.mark.parametrize(
    "extension,value,pack_in_zip",
    [
        (".xlsx", 7, False),
        (".csv", 13, False),
        (".docx", 17, False),
        (".pdf", 19, False),
        (".md", 23, False),
        (".zip", 29, False),
        (".pdf", 31, True),
        (".docx", 37, True),
        (".xlsx", 41, True),
        (".csv", 43, True),
        (".scan.pdf", 47, False),
        (".scan.pdf", 47, True),
    ],
)
async def test_document_content_drives_actual_copy_edit(
    services, tmp_path, monkeypatch, extension, value, pack_in_zip
):
    work, thread, original = make_work(services, tmp_path)
    paths, _, workspace, repository, memories, settings = services
    data = document_bytes(extension, value)
    if pack_in_zip:
        data = zip_bytes({"docs/需求" + extension: data})
    attachment = repository.attachments.upload(
        data, "需求" + (".zip" if pack_in_zip else extension)
    )
    model = DocumentEditingModel(attachment_id=attachment["id"])
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *args, **kwargs: model
    )
    run = repository.create_run(
        thread,
        "请根据附件里的新值修改现有代码",
        [],
        {"use_memory": False, "use_knowledge": False, "use_deepwiki": False},
        [attachment["id"]],
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    events = []
    answer = await runtime.execute(run, lambda kind, payload: events.append((kind, payload)))
    assert model.target == value and f"{value}" in answer
    assert model.calls_seen == [
        "read_chat_attachment",
        "prepare_code_workspace",
        "read_work_file",
        "edit_work_file",
    ]
    assert f"+ int Value = {value};" in work.diff(thread, FILE)["diff"]
    assert "Value = 1" in (original / "Main/Example.cs").read_text(encoding="utf-8")
    assert any(
        kind == "attachment_read" and payload["sha256"] == attachment["sha256"]
        for kind, payload in events
    )


async def test_attachment_tools_reject_other_conversation_ids_and_search_paginates(services):
    repository = services[3]
    first = repository.attachments.upload(b"rule " * 20, "rules.txt")
    second = repository.attachments.upload(b"private", "other.txt")
    prompt, ids = attachment_context(repository, [{"attachments": [first]}])
    assert first["id"] in prompt and second["id"] not in prompt
    tools = {
        tool.name: tool
        for tool in attachment_tools(repository.attachments, ids, lambda *args: None)
    }
    result = json.loads(
        await tools["search_chat_attachment"].ainvoke(
            {"attachment_id": first["id"], "query": "rule"}
        )
    )
    assert len(result["matches"]) == 12 and result["next_offset"]
    result = await tools["read_chat_attachment"].ainvoke({"attachment_id": second["id"]})
    assert "未绑定" in result and "private" not in result
