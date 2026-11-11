import json
import zipfile

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agents.tools.attachments import attachment_context, attachment_tools
from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.validation import validate_backup
from app.main import create_app
from app.modules.chat.models import ChatAttachment
from tests.helpers.api_paths import project_api
from tests.helpers.chat_attachments import document_bytes, zip_bytes


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
