"""view_image：工具只返回文本，图片由请求边界统一注入，兼容并行工具调用。"""

from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agents.runtime.images import ImageAttachments
from app.agents.tools.coding import coding_tools
from app.infrastructure.providers.models import StateInspectionModel
from app.modules.chat.image_attachments import expand_image_messages, path_marker
from tests.helpers.chat_attachments import image_bytes

PNG = image_bytes((300, 200))


class FakeWork:
    def read_image(self, path):
        if path == "missing.png" or not path.endswith(".png"):
            raise FileNotFoundError(f"文件不存在：{path}")
        return {
            "path": path,
            "data": PNG,
            "format": "PNG",
            "width": 300,
            "height": 200,
            "frames": 1,
        }


def tools(work=None):
    return {tool.name: tool for tool in coding_tools(work or FakeWork(), "thread", lambda *a: None)}


def test_view_image_is_registered():
    assert "view_image" in tools()
    assert "tool_call_id" not in tools()["view_image"].args


def test_view_image_returns_path_without_pixels():
    import asyncio

    result = asyncio.run(tools()["view_image"].ainvoke({"path": "shots/app.png"}))
    assert '"ok":true' in result.replace(" ", "")
    assert "shots/app.png" in result
    assert "base64" not in result.lower()


def test_view_image_failure_is_reported_to_model():
    import asyncio

    result = asyncio.run(tools()["view_image"].ainvoke({"path": "missing.png"}))
    assert '"ok":false' in result.replace(" ", "")
    assert "文件不存在" in result


def test_path_marker_escapes_quotes():
    marker = path_marker('shots/a"b.png')
    assert "&quot;" in marker
    expanded = expand_image_messages([HumanMessage(content=marker)], workspace=FakeWork())
    assert expanded[0].content[1]["type"] == "image_url"


async def test_middleware_injects_one_image_message_for_parallel_calls():
    request = ModelRequest(
        model=StateInspectionModel(),
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "view_image", "args": {"path": "shots/app.png"}, "id": "call_a"},
                    {"name": "view_image", "args": {"path": "shots/app.png"}, "id": "call_b"},
                ],
            ),
            ToolMessage(content="已加载", tool_call_id="call_a"),
            ToolMessage(content="已加载", tool_call_id="call_b"),
        ],
    )
    seen = {}

    async def handler(model_request):
        seen["messages"] = model_request.messages
        return "ok"

    await ImageAttachments(None, FakeWork()).awrap_model_call(request, handler)
    messages = seen["messages"]
    # 原消息保持 tool_use 后紧跟两个 tool_result，不被插入其他消息。
    assert [message.type for message in messages[:3]] == ["ai", "tool", "tool"]
    last = messages[-1]
    assert last.type == "human"
    assert [block["type"] for block in last.content] == ["text", "image_url"]
    assert last.content[1]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_middleware_keeps_all_viewed_images_once():
    request = ModelRequest(
        model=StateInspectionModel(),
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "view_image", "args": {"path": "shots/app.png"}, "id": "call_a"}
                ],
            ),
            ToolMessage(content="已加载", tool_call_id="call_a"),
            AIMessage(content="看过了"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "view_image", "args": {"path": "shots/app.png"}, "id": "call_c"}
                ],
            ),
            ToolMessage(content="又加载一次", tool_call_id="call_c"),
        ],
    )
    seen = {}

    async def handler(model_request):
        seen["messages"] = model_request.messages
        return "ok"

    await ImageAttachments(None, FakeWork()).awrap_model_call(request, handler)
    images = [
        block
        for message in seen["messages"]
        if message.type == "human" and isinstance(message.content, list)
        for block in message.content
        if block.get("type") == "image_url"
    ]
    assert len(images) == 1
