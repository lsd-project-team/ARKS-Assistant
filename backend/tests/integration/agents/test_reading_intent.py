"""真实临时阅读服务验证：询问能力不能被模型工具调用升级成付费阅读。"""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.agents.tools.engineering import engineering_tools
from app.modules.source_analysis.reading import ProjectReading


@pytest.fixture
async def reading_runtime(services):
    paths, database, workspace = services[:3]
    reading = ProjectReading(paths, database, workspace, "reading-intent-project")
    calls, guard_calls = [], []

    async def analyze(text, metadata):
        calls.append(metadata)
        return {"summary": "当前源码的入口", "unknowns": ["未进行设备验证"]}

    reading.analyzer = analyze
    runtime = SimpleNamespace(
        repository=SimpleNamespace(
            project_id="reading-intent-project", creation_guard=lambda: guard_calls.append(True)
        ),
        project_lock=asyncio.Lock(),
        code_changes=object(),
        project_reading=reading,
        reading_calls=calls,
        guard_calls=guard_calls,
    )
    yield runtime
    await reading.shutdown()


def reading_tool(runtime, request):
    return {item.name: item for item in engineering_tools(runtime, request)}[
        "start_project_reading"
    ]


async def finish(reading):
    if reading.tasks:
        await asyncio.gather(*list(reading.tasks.values()))
    await asyncio.sleep(0)


@pytest.mark.parametrize(
    "prompt",
    [
        "请解释项目阅读功能的实现原理",
        "如何开始通读项目",
        "这个方案能完成通读需求吗",
        "项目阅读功能是什么",
        "请问如何开始项目阅读？",
        "我想知道怎么继续阅读",
        "通读项目是如何实现的",
        "开始项目阅读是否需要配置模型",
        "通读整个项目能做什么",
        "通读项目需要多少费用",
        "通读项目大概要多久",
        "通读项目并不会修改代码吧",
        "通读功能的实现原理",
        "继续阅读是不是会产生费用",
        "项目阅读",
        "请解释通读项目有什么用",
        "先讨论通读项目的方案",
        "先给通读方案，不要开始",
        "不要通读项目",
        "不需要开始项目阅读",
        "只解释项目阅读，不执行",
        "继续",
        "继续\n此前已授权的请求：请解释项目阅读功能的实现原理",
        "继续\n此前已授权的请求：如何开始通读项目",
    ],
)
async def test_explanation_capability_and_negation_never_create_or_start(reading_runtime, prompt):
    reading = reading_runtime.project_reading
    tool = reading_tool(reading_runtime, prompt)
    denied = await tool.ainvoke({"title": "模型尝试创建"})
    assert "没有要求启动全项目阅读" in denied
    assert reading.list() == {"jobs": [], "latest": None}
    # 即使模型知道既有任务 ID，问句仍不能从 ready 偷偷变成 running。
    job = reading.create("已有任务")
    denied_existing = await tool.ainvoke({"job_id": job["id"]})
    assert "没有要求启动全项目阅读" in denied_existing
    assert reading.get(job["id"])["status"] == "ready"
    assert reading_runtime.reading_calls == []
    assert reading_runtime.guard_calls == []


@pytest.mark.parametrize(
    "prompt",
    [
        "通读",
        "请通读",
        "开始项目阅读",
        "继续阅读",
        "帮我通读整个项目",
        "请你把整个项目通读一遍",
        "从头阅读这个项目",
        "现在开始全量阅读项目",
        "阅读整个项目",
        "请完整阅读项目",
        "请通读项目并总结模块如何协作",
        "请先通读项目，然后告诉我入口在哪里",
        "这是当前项目。请开始项目阅读",
        "请通读项目，不要修改代码",
        "请阅读整个项目，不要写代码",
    ],
)
async def test_explicit_reading_command_starts_actual_temporary_job(reading_runtime, prompt):
    reading = reading_runtime.project_reading
    started = json.loads(await reading_tool(reading_runtime, prompt).ainvoke({}))
    assert started["status"] == "running"
    await finish(reading)
    result = reading.get(started["id"])
    assert result["status"] == "completed"
    assert result["counts"]["analyzed"] == 1
    assert len(reading_runtime.reading_calls) == 1
    assert len(reading.list()["jobs"]) == 1
    assert reading_runtime.guard_calls == [True]


@pytest.mark.parametrize(
    "prompt",
    [
        "继续阅读",
        "请继续项目阅读",
        "继续\n此前已授权的请求：请通读项目",
    ],
)
async def test_continue_resumes_latest_saved_chunks_without_duplicate_job(reading_runtime, prompt):
    reading = reading_runtime.project_reading
    root = reading.workspace.root
    (root / "Long.cs").write_text("// 当前源码\n" * 2400, encoding="utf-8")
    blocked = asyncio.Event()
    wait = asyncio.Event()

    async def gated(text, metadata):
        if metadata["path"] == "Long.cs" and metadata["chunk_index"] == 1:
            blocked.set()
            await wait.wait()
        return {"summary": "实际读取的片段"}

    reading.analyzer = gated
    initial = json.loads(await reading_tool(reading_runtime, "请通读项目").ainvoke({}))
    await asyncio.wait_for(blocked.wait(), 3)
    paused = await reading.pause(initial["id"])
    assert paused["status"] == "paused"
    first_document = reading.documents(initial["id"])[0]
    assert first_document["chunk_index"] == 0
    assert len(reading.list()["jobs"]) == 1
    resumed_calls = []

    async def resumed(text, metadata):
        resumed_calls.append(metadata)
        return {"summary": "继续读取的实际片段"}

    reading.analyzer = resumed
    resumed_job = json.loads(await reading_tool(reading_runtime, prompt).ainvoke({}))
    assert resumed_job["id"] == initial["id"]
    await finish(reading)
    assert reading.get(initial["id"])["status"] == "completed"
    assert len(reading.list()["jobs"]) == 1
    assert reading.documents(initial["id"])[0]["id"] == first_document["id"]
    assert all(row["path"] != "Long.cs" or row["chunk_index"] > 0 for row in resumed_calls)


async def test_continue_refreshes_changed_source_before_reusing_completed_job(reading_runtime):
    reading = reading_runtime.project_reading
    first = json.loads(await reading_tool(reading_runtime, "请通读项目").ainvoke({}))
    await finish(reading)
    assert reading.get(first["id"])["status"] == "completed"
    (reading.workspace.root / "Program.cs").write_text("class Revised {}", encoding="utf-8")
    resumed = json.loads(await reading_tool(reading_runtime, "继续阅读").ainvoke({}))
    assert resumed["id"] == first["id"]
    await finish(reading)
    assert len(reading_runtime.reading_calls) == 2
    assert (
        reading_runtime.reading_calls[-1]["source_version"]
        != reading_runtime.reading_calls[0]["source_version"]
    )
    latest_version = reading_runtime.reading_calls[-1]["source_version"]
    documents = reading.documents(first["id"])
    assert any(
        row["source_version"] == latest_version and row["status"] != "stale" for row in documents
    )
    assert reading.get(first["id"])["counts"]["analyzed"] == 1
