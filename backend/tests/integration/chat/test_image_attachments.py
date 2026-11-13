"""聊天图片附件：上传、预览、消息标记与请求边界展开。"""

import pytest
from fastapi.testclient import TestClient
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.context.tokens import estimate_tokens
from app.agents.runtime.engine import AgentRuntime
from app.agents.runtime.images import ImageAttachments
from app.agents.tools.attachments import attachment_context
from app.infrastructure.providers.models import StateInspectionModel
from app.main import create_app
from app.modules.chat.image_attachments import expand_image_messages, marker
from tests.helpers.api_paths import project_api
from tests.helpers.chat_attachments import image_bytes, zip_bytes


def upload_image(client, name="截图.png", data=None):
    response = client.post(
        project_api(client, "/attachments"),
        params={"filename": name},
        content=data if data is not None else image_bytes(),
        headers={"Content-Type": "application/octet-stream"},
    )
    return response


def test_image_upload_preview_download_and_inline_endpoint(services):
    with TestClient(create_app(services[0])) as client:
        response = upload_image(client, "报错截图.PNG")
        assert response.status_code == 201, response.text
        attachment = response.json()
        assert attachment["kind"] == "image"
        assert attachment["parse_status"] == "readable"
        assert "压缩" in attachment["parse_notes"]
        prefix = project_api(client, f"/attachments/{attachment['id']}")
        page = client.get(prefix).json()
        assert "[图片]" in page["content"] and "PNG" in page["content"]
        assert client.get(prefix + "/download").content == image_bytes()
        inline = client.get(prefix + "/image")
        assert inline.status_code == 200
        assert inline.headers["content-type"] == "image/png"
        assert inline.headers["content-disposition"].startswith("inline")
        assert inline.content == image_bytes()
        assert client.delete(prefix).status_code == 200


@pytest.mark.parametrize(
    ("name", "image_format", "media_type"),
    [
        ("照片.jpg", "JPEG", "image/jpeg"),
        ("动图.gif", "GIF", "image/gif"),
        ("截图.webp", "WEBP", "image/webp"),
    ],
)
def test_common_image_formats_upload_and_inline(services, name, image_format, media_type):
    with TestClient(create_app(services[0])) as client:
        response = upload_image(client, name, image_bytes((160, 120), image_format))
        assert response.status_code == 201, response.text
        attachment = response.json()
        assert attachment["kind"] == "image"
        inline = client.get(project_api(client, f"/attachments/{attachment['id']}/image"))
        assert inline.headers["content-type"] == media_type


def test_image_upload_rejects_corrupt_and_oversized(services):
    with TestClient(create_app(services[0])) as client:
        corrupt = upload_image(client, "坏图.png", b"not-an-image")
        assert corrupt.status_code == 409
        assert "图片" in corrupt.text
        oversized = upload_image(client, "过大.png", image_bytes((9000, 20)))
        assert oversized.status_code == 409
        assert "8192" in oversized.text


def test_image_is_not_a_document_for_tools(services):
    repository = services[3]
    image = repository.attachments.upload(image_bytes(), "现场照片.png")
    document = repository.attachments.upload(b"rule " * 20, "rules.txt")
    message = {"attachments": [image, document]}
    prompt, identifiers = attachment_context(repository, [message])
    assert identifiers == [document["id"]]
    assert "图片已作为对应消息的内容直接提供" in prompt
    assert image["filename"] in prompt and document["filename"] in prompt


def test_message_marker_and_request_expansion(services):
    repository = services[3]
    image = repository.attachments.upload(image_bytes((300, 200)), "界面截图.png")
    message = {
        "id": "test-message",
        "content": "看这个报错",
        "attachments": [image],
        "selections": [],
    }
    built = AgentRuntime.input_message(None, message)
    assert isinstance(built, HumanMessage)
    assert marker(image["id"], image["filename"]) in built.content
    assert "不要调用附件读取工具获取图片内容" in built.content

    expanded = expand_image_messages([built], repository.attachments)
    blocks = expanded[0].content
    assert [block["type"] for block in blocks] == ["text", "image_url"]
    assert blocks[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert marker(image["id"], image["filename"]) in blocks[0]["text"]


def test_missing_and_non_image_attachments_are_not_sent(services):
    repository = services[3]
    text = repository.attachments.upload(b"plain text", "说明.txt")
    message = HumanMessage(content="看图片\n" + marker(text["id"], text["filename"]))
    expanded = expand_image_messages([message], repository.attachments)
    assert [block["type"] for block in expanded[0].content] == ["text", "text"]
    assert "未能发送给模型" in expanded[0].content[-1]["text"]


def test_documents_and_assistant_messages_are_untouched(services):
    repository = services[3]
    document = HumanMessage(content="普通问题")
    assistant = AIMessage(content="普通回答")
    assert expand_image_messages([document, assistant], repository.attachments) == [
        document,
        assistant,
    ]


def test_zip_skips_images_instead_of_pretending(services):
    archive = zip_bytes(
        {
            "截图/报错.png": image_bytes(),
            "说明.txt": b"plain",
        }
    )
    with TestClient(create_app(services[0])) as client:
        response = client.post(
            project_api(client, "/attachments"),
            params={"filename": "资料.zip"},
            content=archive,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 201, response.text
        attachment = response.json()
        assert "图片请单独上传" in attachment["parse_notes"]
        content = client.get(project_api(client, f"/attachments/{attachment['id']}")).json()[
            "content"
        ]
        assert "说明.txt" in content and "报错.png" not in content


def test_token_estimate_reserves_image_budget():
    text = HumanMessage(content="看截图")
    mark = marker("11111111-2222-3333-4444-555555555555", "a.png")
    with_image = HumanMessage(content="看截图\n" + mark)
    assert estimate_tokens([with_image]) - estimate_tokens([text]) >= 1024


async def test_middleware_expands_images_at_model_request_boundary(services):
    repository = services[3]
    image = repository.attachments.upload(image_bytes(), "现场照片.png")
    human = HumanMessage(content="看图\n" + marker(image["id"], image["filename"]))
    request = ModelRequest(model=StateInspectionModel(), messages=[human])
    seen = {}

    async def handler(model_request):
        seen["messages"] = model_request.messages
        return "ok"

    result = await ImageAttachments(repository.attachments).awrap_model_call(request, handler)
    assert result == "ok"
    blocks = seen["messages"][0].content
    assert [block["type"] for block in blocks] == ["text", "image_url"]
    assert blocks[1]["image_url"]["url"].startswith("data:image/png;base64,")
    # 检查点里的原始消息仍是文本标记，不保存 base64。
    assert isinstance(human.content, str)
