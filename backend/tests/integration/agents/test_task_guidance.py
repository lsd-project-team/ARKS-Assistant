from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agents.context.task_guidance import SOURCE_ANSWER_NOTE_ID
from app.agents.runtime.engine import AgentRuntime
from app.core.config import AppSettings, ModelSettings
from tests.helpers.models import DeterministicModel


async def test_source_rules_reach_real_graph_after_unclassified_question_selects_source_tool(
    services, monkeypatch
):
    paths, _, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(model=ModelSettings(context_tokens=16384, output_tokens=512), mcp_servers=[])
    )
    prompts = []
    reminder_ids = []

    class Model(DeterministicModel):
        def _generate(self, messages, *args, **kwargs):
            prompt = "\n".join(row.text for row in messages if isinstance(row, SystemMessage))
            prompts.append(prompt)
            reminder_ids.append([row.id for row in messages if row.id == SOURCE_ANSWER_NOTE_ID])
            if not any(isinstance(row, ToolMessage) for row in messages):
                answer = AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "lookup", "name": "find_source_files", "args": {"query": "Program"}}
                    ],
                )
            else:
                answer = AIMessage(content="已找到文件，文件名本身不能证明实现内容。")
            return ChatResult(generations=[ChatGeneration(message=answer)])

    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model", lambda *_args, **_kwargs: Model()
    )
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    options = {"use_knowledge": False, "use_memory": False, "use_deepwiki": False}
    run = repository.create_run(None, "帮我看看有什么", [], options)
    answer = await runtime.execute(run, lambda *_args: None)
    repository.finish(run["id"], answer)
    assert len(prompts) == 2
    assert "【源码核查】" not in prompts[0]
    assert prompts[1].count("【源码核查】") == 1
    assert "本地源码优先于 DeepWiki" in prompts[1]
    assert "可选回答展示协议" in prompts[1]
    assert "默认用step_flow" not in prompts[1]
    assert reminder_ids == [[], [SOURCE_ANSWER_NOTE_ID]]
    assert all(
        "系统答复组织提醒" not in row["content"]
        for row in repository.thread(run["thread_id"])["messages"]
    )

    # 下一轮普通问题使用独立规则实例，不沿用前一轮的源码工具状态。
    prompts.clear()
    reminder_ids.clear()
    run = repository.create_run(run["thread_id"], "你好", [], options)
    await runtime.execute(run, lambda *_args: None)
    assert prompts and all("【源码核查】" not in prompt for prompt in prompts)
    assert all(not ids for ids in reminder_ids)
