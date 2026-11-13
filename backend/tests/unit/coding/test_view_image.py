"""view_image：把项目内图片作为用户消息交给模型，检查点只保存标记。"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.agents.tools.coding import coding_tools
from app.modules.chat.image_attachments import expand_image_messages, path_marker
from tests.helpers.chat_attachments import image_bytes

PNG = image_bytes((300, 200))


def tool_graph(tool):
    """真实运行环境里工具节点在图中执行，注入的 tool_call_id 才可用。"""
    builder = StateGraph(MessagesState)
    builder.add_node("tools", ToolNode([tool]))
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    return builder.compile()


class FakeWork:
    def read_image(self, path):
        if path != "shots/app.png":
            raise FileNotFoundError(f"文件不存在：{path}")
        return {
            "path": "shots/app.png",
            "data": PNG,
            "format": "PNG",
            "width": 300,
            "height": 200,
            "frames": 1,
        }


def tools(work=None):
    return {tool.name: tool for tool in coding_tools(work or FakeWork(), "thread", lambda *a: None)}


def test_view_image_is_registered_without_exposing_tool_call_id():
    assert "view_image" in tools()
    assert "tool_call_id" not in tools()["view_image"].args


def test_view_image_marker_and_request_expansion():
    assert path_marker("shots/app.png") == (
        '<attachment-image path="shots/app.png" name="shots/app.png" />'
    )
    # 助手消息不携带图片，只有用户消息才展开。
    assistant = AIMessage(content="看图\n" + path_marker("shots/app.png"))
    assert expand_image_messages([assistant], workspace=FakeWork())[0].content == assistant.content
    human = HumanMessage(content="看图\n" + path_marker("shots/app.png"))
    blocks = expand_image_messages([human], workspace=FakeWork())[0].content
    assert [block["type"] for block in blocks] == ["text", "image_url"]
    assert blocks[1]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_view_image_returns_tool_message_and_human_image_message():
    graph = tool_graph(tools()["view_image"])
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "view_image", "args": {"path": "shots/app.png"}, "id": "call_1"}
                ],
            )
        ]
    }
    messages = (await graph.ainvoke(state))["messages"]
    tool_message = next(item for item in messages if isinstance(item, ToolMessage))
    human = next(item for item in messages if item.type == "human")
    assert tool_message.tool_call_id == "call_1"
    assert "已加载项目图片 shots/app.png" in tool_message.text
    assert path_marker("shots/app.png") in human.content
    expanded = expand_image_messages([human], workspace=FakeWork())
    assert expanded[0].content[1]["type"] == "image_url"


async def test_view_image_failure_is_reported_to_model():
    graph = tool_graph(tools()["view_image"])
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "view_image", "args": {"path": "missing.png"}, "id": "call_2"}
                ],
            )
        ]
    }
    messages = (await graph.ainvoke(state))["messages"]
    tool_message = next(item for item in messages if isinstance(item, ToolMessage))
    assert tool_message.tool_call_id == "call_2"
    assert '"ok":false' in tool_message.text and "文件不存在" in tool_message.text
    assert not any(item.type == "human" for item in messages)


def test_stale_project_image_is_reported_not_sent():
    human = HumanMessage(content="看图\n" + path_marker("shots/gone.png"))
    expanded = expand_image_messages([human], workspace=FakeWork())
    assert [block["type"] for block in expanded[0].content] == ["text", "text"]
    assert "未能发送给模型" in expanded[0].content[-1]["text"]


def test_missing_workspace_cannot_silently_drop_image():
    human = HumanMessage(content="看图\n" + path_marker("shots/app.png"))
    expanded = expand_image_messages([human])
    assert "未能发送给模型" in expanded[0].content[-1]["text"]


def test_project_image_with_quotes_in_name_still_parses():
    marker_text = path_marker('shots/a"b.png')
    assert "&quot;" in marker_text
    human = HumanMessage(content="看图\n" + marker_text)
    expanded = expand_image_messages([human], workspace=FakeWork())
    assert "未能发送给模型" in expanded[0].content[-1]["text"]
