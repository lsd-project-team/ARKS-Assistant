import asyncio

from app.config import AppSettings, ModelSettings
from app.runtime import AgentRuntime
from tests.test_compaction import DeterministicModel


async def test_restart_after_graph_completion_resumes_without_duplicate(services, monkeypatch):
    paths, _, workspace, repository, memories, settings = services
    settings.save(AppSettings(model=ModelSettings()))
    monkeypatch.setattr("app.runtime.create_model", lambda *_args, **_kwargs: DeterministicModel())
    runtime = AgentRuntime(paths, settings, workspace, repository, memories)
    thread = repository.create_thread("恢复")
    run = repository.create_run(thread["id"], "稳定的问题", [])
    await runtime.execute(run, lambda *_event: None)
    # 模拟图已完成但业务事务未提交就被强制关闭，恢复时不再次请求模型。
    repository.recover()
    resumed = repository.resume(run["id"])
    monkeypatch.setattr(
        "tests.test_compaction.DeterministicModel._generate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("重复调用")),
    )
    answer = await runtime.execute(resumed, lambda *_event: None)
    repository.finish(resumed["id"], answer)
    assert len(repository.thread(thread["id"])["messages"]) == 2


async def test_event_replay_does_not_cancel_task(services):
    from app.runs import RunManager

    release = asyncio.Event()

    class PausedRuntime:
        async def execute(self, _run, emit):
            emit("token", {"text": "第一段"})
            await release.wait()
            emit("token", {"text": "第二段"})
            return "第一段第二段"

    repository, settings = services[3], services[5]
    manager = RunManager(repository, PausedRuntime(), settings)
    thread = repository.create_thread("重连")
    run = repository.create_run(thread["id"], "问题", [])
    manager.start(run)
    connection = manager.stream(run["id"], 0)
    first = await anext(connection)
    await connection.aclose()
    assert not manager.tasks[run["id"]].done()
    release.set()
    await manager.tasks[run["id"]]
    replayed = [event async for event in manager.stream(run["id"], first["sequence"])]
    assert [row["payload"]["text"] for row in replayed if row["kind"] == "token"] == [
        "第一段",
        "第二段",
    ]
