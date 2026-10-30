from app.agents.runtime.engine import AgentRuntime


def test_historical_selection_reaches_model_with_version_and_warning(services):
    paths, _, workspace, repository, memories, settings = services
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    selection = {
        "path": "Program.cs",
        "start_line": 1,
        "end_line": 2,
        "version": "a" * 64,
        "content": "历史源码",
        "stale": True,
    }
    message = runtime.input_message(
        {"id": "question", "content": "解释代码", "selections": [selection]}
    )
    assert "stale=true" in message.text and "历史快照" in message.text
    assert "当前行号前必须重新读取核对" in message.text
    assert selection["version"] in message.text
    selection["stale"] = False
    current = runtime.input_message(
        {"id": "current", "content": "解释代码", "selections": [selection]}
    )
    assert "stale=false" in current.text and "注意：" not in current.text
