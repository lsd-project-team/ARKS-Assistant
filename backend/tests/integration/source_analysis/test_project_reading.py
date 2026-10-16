"""真实临时文件和 SQLite 验证阅读恢复、知识失效与项目边界。"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agents.context.tokens import text_tokens
from app.core.config import Paths
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import Database
from app.modules.source_analysis.collection import SourceCollection
from app.modules.source_analysis.reading import ProjectReading
from app.modules.source_analysis.reading.models import ProjectReadingDocument, ProjectReadingJob
from app.modules.source_analysis.reading.router import create_router
from app.modules.source_analysis.reading.sources import CHUNK_TOKENS
from app.modules.source_analysis.workspace import Workspace


@pytest.fixture
def reading(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "Program.cs").write_text("class Program { static void Main() {} }\n", encoding="utf-8")
    paths = Paths(tmp_path / "state", root)
    database = Database(paths.data / "app.sqlite3")
    Base.metadata.create_all(database.engine)
    service = ProjectReading(paths, database, Workspace(root), "project-a")
    yield service
    database.close()


async def analysis(text, metadata):
    return {
        "summary": "入口 Program.Main 的当前实现",
        "entrypoints": ["Program.Main"],
        "unknowns": ["尚未进行设备验证"],
    }


async def settle(reading):
    if reading.tasks:
        await asyncio.gather(*list(reading.tasks.values()))
    await asyncio.sleep(0)


async def test_snapshot_read_analysis_and_review_are_distinct(reading):
    job = reading.create()
    assert job["status"] == "ready"
    assert job["counts"] == {
        "files": 1,
        "indexed": 1,
        "read": 0,
        "analyzed": 0,
        "reviewed": 0,
        "pending": 1,
        "failed": 0,
        "excluded": 0,
        "stale": 0,
    }
    with pytest.raises(ValueError, match="模型"):
        await reading.start(job["id"])
    calls = []

    async def inspect(text, metadata):
        calls.append((text, metadata))
        assert "class Program" in text
        assert reading.get(job["id"])["counts"]["read"] == 1
        assert reading.get(job["id"])["counts"]["analyzed"] == 0
        return await analysis(text, metadata)

    await reading.start(job["id"], inspect)
    await settle(reading)
    completed = reading.get(job["id"])
    assert completed["status"] == "completed"
    assert completed["counts"]["analyzed"] == 1
    assert completed["counts"]["reviewed"] == 0
    document = reading.documents(job["id"])[0]
    assert document["unknowns"] == ["尚未进行设备验证"]
    assert document["references"][0]["source_version"] == calls[0][1]["source_version"]
    reviewed = reading.review(job["id"], document["id"], document["version"], "approved")
    assert reviewed["status"] == "approved"
    assert reading.get(job["id"])["counts"]["reviewed"] == 1
    with pytest.raises(ValueError, match="更新"):
        reading.review(job["id"], document["id"], document["version"], "needs_changes")


async def test_pause_restart_retains_finished_chunks_and_original_source(reading):
    original = "class Long {\n" + "// 内容\n" * 3000 + "}\n"
    source = reading.workspace.root / "Long.cs"
    source.write_text(original, encoding="utf-8")
    started, wait = asyncio.Event(), asyncio.Event()
    calls = []

    async def blocking(text, metadata):
        calls.append((metadata["path"], metadata["chunk_index"]))
        if metadata["path"] == "Long.cs" and metadata["chunk_index"] == 1:
            started.set()
            await wait.wait()
        return await analysis(text, metadata)

    job = reading.create()
    await reading.start(job["id"], blocking)
    await asyncio.wait_for(started.wait(), 5)
    paused = await reading.pause(job["id"])
    assert paused["status"] == "paused"
    first = reading.documents(job["id"])
    assert len(first) == 1 and first[0]["chunk_index"] == 0
    assert reading.files(job["id"])[0]["next_chunk"] == 1
    restarted = ProjectReading(reading.paths, reading.database, reading.workspace, "project-a")
    resumed_calls = []

    async def resumed(text, metadata):
        resumed_calls.append((metadata["path"], metadata["chunk_index"]))
        return await analysis(text, metadata)

    await restarted.start(job["id"], resumed)
    await settle(restarted)
    assert restarted.get(job["id"])["status"] == "completed"
    assert ("Long.cs", 0) not in resumed_calls
    assert ("Long.cs", 1) in resumed_calls
    assert source.read_text(encoding="utf-8") == original


async def test_failed_analysis_is_retryable_and_does_not_publish_knowledge(reading):
    job = reading.create()

    async def broken(text, metadata):
        raise RuntimeError("temporary model failure")

    await reading.start(job["id"], broken)
    await settle(reading)
    failed = reading.get(job["id"])
    assert failed["status"] == "failed"
    assert failed["counts"]["read"] == 1
    assert failed["counts"]["analyzed"] == 0
    assert reading.documents(job["id"]) == []
    assert reading.prompt("Program", 2000) == ("", [])
    await reading.start(job["id"], analysis)
    await settle(reading)
    assert reading.get(job["id"])["status"] == "completed"


async def test_refresh_only_invalidates_changed_and_dependent_knowledge(reading):
    (reading.workspace.root / "Other.cs").write_text("class Other {}", encoding="utf-8")
    (reading.workspace.root / "Dependent.cs").write_text("class Dependent {}", encoding="utf-8")

    async def dependencies(text, metadata):
        result = await analysis(text, metadata)
        result["summary"] = metadata["path"]
        result["dependencies"] = ["Program.cs"] if metadata["path"] == "Dependent.cs" else []
        return result

    job = reading.create()
    await reading.start(job["id"], dependencies)
    await settle(reading)
    before = {row["path"]: row for row in reading.documents(job["id"])}
    (reading.workspace.root / "Program.cs").write_text("class Changed {}", encoding="utf-8")
    # 即使用户尚未刷新，也不能把旧源版本注入新问题。
    _, injected = reading.prompt("Program", 5000)
    assert all(row["path"] not in {"Program.cs", "Dependent.cs"} for row in injected)
    refreshed = reading.refresh(job["id"])
    assert refreshed["counts"]["stale"] == 2
    assert refreshed["counts"]["analyzed"] == 1
    current = {row["path"]: row for row in reading.documents(job["id"])}
    assert current["Other.cs"]["id"] == before["Other.cs"]["id"]
    assert current["Other.cs"]["status"] == "analyzed"
    assert current["Program.cs"]["status"] == "stale"
    assert current["Dependent.cs"]["status"] == "stale"
    await reading.start(job["id"], dependencies)
    await settle(reading)
    after = {row["path"]: row for row in reading.documents(job["id"])}
    assert after["Program.cs"]["version"] > before["Program.cs"]["version"]
    with reading.database.session() as session:
        revisions = list(
            session.scalars(
                select(ProjectReadingDocument).where(ProjectReadingDocument.job_id == job["id"])
            )
        )
    assert len(revisions) == 5


async def test_source_mutation_during_analysis_invalidates_result(reading):
    job = reading.create()

    async def mutate(text, metadata):
        (reading.workspace.root / metadata["path"]).write_text("class New {}", encoding="utf-8")
        return await analysis(text, metadata)

    await reading.start(job["id"], mutate)
    await settle(reading)
    assert reading.get(job["id"])["status"] == "partial"
    assert reading.get(job["id"])["counts"]["stale"] == 1
    assert reading.documents(job["id"]) == []


async def test_project_isolation_includes_documents_reviews_and_recovery(reading):
    job = reading.create()
    await reading.start(job["id"], analysis)
    await settle(reading)
    doc = reading.documents(job["id"])[0]
    stranger = ProjectReading(reading.paths, reading.database, reading.workspace, "project-b")
    assert stranger.list() == {"jobs": [], "latest": None}
    assert stranger.prompt("Program", 2000) == ("", [])
    operations = [
        lambda: stranger.get(job["id"]),
        lambda: stranger.documents(job["id"]),
        lambda: stranger.refresh(job["id"]),
        lambda: stranger.review(job["id"], doc["id"], doc["version"], "approved"),
    ]
    for operation in operations:
        with pytest.raises(FileNotFoundError):
            operation()
    with reading.database.session.begin() as session:
        row = session.get(ProjectReadingJob, job["id"])
        row.status = "running"
    assert stranger.recover() == 0
    assert reading.recover() == 1
    assert reading.get(job["id"])["status"] == "interrupted"


async def test_budget_pause_and_needs_changes_resume(reading):
    (reading.workspace.root / "Long.cs").write_text("// x\n" * 4000, encoding="utf-8")
    job = reading.create()
    await reading.start(job["id"], analysis, max_chunks=1)
    await settle(reading)
    assert reading.get(job["id"])["status"] == "paused"
    assert len(reading.documents(job["id"])) == 1
    await reading.start(job["id"], analysis)
    await settle(reading)
    document = reading.documents(job["id"])[0]
    reading.review(job["id"], document["id"], document["version"], "needs_changes")
    _, injected = reading.prompt("Long", 5000)
    assert document["id"] not in {row["id"] for row in injected}
    await reading.start(job["id"], analysis)
    await settle(reading)
    assert reading.get(job["id"])["status"] == "completed"


async def test_attached_roots_exclusions_and_large_long_line_chunks(reading, tmp_path):
    attached = tmp_path / "attached"
    attached.mkdir()
    (attached / "Large.cs").write_text("汉" * 710000, encoding="utf-8")
    (attached / "ignored.dll").write_bytes(b"binary")
    (attached / "bin").mkdir()
    (attached / "bin" / "generated.cs").write_text("generated", encoding="utf-8")
    collection = SourceCollection(
        reading.workspace.root, [{"source_id": "extra", "label": "附加源码", "root": attached}]
    )
    reading.workspace = collection
    job = reading.create()
    rows = reading.files(job["id"])
    assert {row["path"] for row in rows} == {
        "Program.cs",
        "@sources/extra/Large.cs",
        "@sources/extra/ignored.dll",
        "@sources/extra/bin/",
    }
    assert job["counts"]["excluded"] == 2
    assert job["counts"]["indexed"] == 2
    captured = []

    async def bounded(text, metadata):
        captured.append((text, metadata))
        assert text_tokens(text) <= CHUNK_TOKENS
        assert len(text) <= 8000
        return await analysis(text, metadata)

    await reading.start(job["id"], bounded, max_chunks=1)
    await settle(reading)
    assert captured[0][1]["path"] == "@sources/extra/Large.cs"
    assert captured[0][1]["start_line"] == captured[0][1]["end_line"] == 1
    assert reading.get(job["id"])["counts"]["read"] == 0


async def test_unread_reference_is_rejected_and_shutdown_marks_interrupted(reading):
    job = reading.create()

    async def fabricated(text, metadata):
        return {
            "summary": "unsupported",
            "references": [
                {
                    "path": "Other.cs",
                    "source_version": metadata["source_version"],
                    "start_line": 1,
                    "end_line": 1,
                }
            ],
        }

    await reading.start(job["id"], fabricated)
    await settle(reading)
    assert reading.get(job["id"])["counts"]["failed"] == 1
    assert reading.documents(job["id"]) == []
    entered = asyncio.Event()

    async def blocked(text, metadata):
        entered.set()
        await asyncio.Event().wait()

    await reading.start(job["id"], blocked)
    await asyncio.wait_for(entered.wait(), 5)
    await reading.shutdown()
    assert reading.get(job["id"])["status"] == "interrupted"


async def test_failed_model_calls_are_budgeted_and_validation_fails_before_start(reading):
    (reading.workspace.root / "Another.cs").write_text("class Another {}", encoding="utf-8")
    job = reading.create()

    class Unconfigured:
        def validate(self):
            raise ValueError("missing model configuration")

        async def __call__(self, text, metadata):
            pytest.fail("无效配置不能消耗模型请求")

    with pytest.raises(ValueError, match="configuration"):
        await reading.start(job["id"], Unconfigured())
    assert reading.get(job["id"])["status"] == "ready"
    calls = []

    async def broken(text, metadata):
        calls.append(metadata["path"])
        raise RuntimeError("failure")

    await reading.start(job["id"], broken, max_chunks=1)
    await settle(reading)
    result = reading.get(job["id"])
    assert len(calls) == 1
    assert result["status"] == "paused"
    assert result["counts"]["failed"] == 1
    assert result["counts"]["analyzed"] == 0


async def test_default_budget_pauses_after_64_attempts(reading):
    for index in range(65):
        (reading.workspace.root / f"File{index:03}.cs").write_text(
            "class Test {}", encoding="utf-8"
        )
    job = reading.create()
    await reading.start(job["id"], analysis)
    await settle(reading)
    result = reading.get(job["id"])
    assert result["status"] == "paused"
    assert result["counts"]["analyzed"] == 64
    assert result["counts"]["pending"] == 2
    await reading.start(job["id"], analysis)
    await settle(reading)
    assert reading.get(job["id"])["status"] == "completed"


async def test_transitive_dependency_changes_are_invalidated_before_and_after_refresh(reading):
    for name in ("A.cs", "B.cs", "C.cs", "Unrelated.cs"):
        (reading.workspace.root / name).write_text(f"class {name[0]} {{}}", encoding="utf-8")

    async def dependencies(text, metadata):
        return {
            "summary": metadata["path"],
            "dependencies": {"B.cs": ["A.cs"], "C.cs": ["B.cs"]}.get(metadata["path"], []),
        }

    job = reading.create()
    await reading.start(job["id"], dependencies)
    await settle(reading)
    (reading.workspace.root / "A.cs").write_text("class Changed {}", encoding="utf-8")
    assert all(
        row["path"] not in {"A.cs", "B.cs", "C.cs"} for row in reading.prompt("C.cs", 5000)[1]
    )
    result = reading.refresh(job["id"])
    assert result["counts"]["stale"] == 3
    documents = {row["path"]: row for row in reading.documents(job["id"])}
    assert documents["C.cs"]["status"] == "stale"
    assert documents["Unrelated.cs"]["status"] == "analyzed"


async def test_prompt_filters_relevance_before_io_and_caches_source_versions(reading, monkeypatch):
    (reading.workspace.root / "Long.cs").write_text("// Program\n" * 2400, encoding="utf-8")
    job = reading.create()
    await reading.start(job["id"], analysis)
    await settle(reading)
    from app.modules.source_analysis.reading import sources

    described = []
    original = sources.describe

    def record(workspace, path):
        described.append(path)
        return original(workspace, path)

    monkeypatch.setattr(sources, "describe", record)
    assert reading.prompt("nonexistent_unrelated_keyword", 5000) == ("", [])
    assert described == []
    text, documents = reading.prompt("Program", 10000)
    assert len(documents) > 2
    assert len(described) == len(set(described)) == 2
    assert text_tokens(text) <= 10000


async def test_two_service_instances_cannot_start_same_job(reading):
    job = reading.create()
    entered = asyncio.Event()

    async def blocked(text, metadata):
        entered.set()
        await asyncio.Event().wait()

    await reading.start(job["id"], blocked)
    await asyncio.wait_for(entered.wait(), 5)
    duplicate = ProjectReading(reading.paths, reading.database, reading.workspace, "project-a")
    with pytest.raises(ValueError, match="运行"):
        await duplicate.start(job["id"], analysis)
    with pytest.raises(ValueError, match="暂停"):
        await duplicate.pause(job["id"])
    assert reading.get(job["id"])["status"] == "running"
    await reading.pause(job["id"])


def test_router_contract_and_invalid_review_input(reading):
    app = FastAPI()
    app.include_router(
        create_router(
            SimpleNamespace(
                runtime=SimpleNamespace(project_reading=reading),
                runs=SimpleNamespace(edit_lock=asyncio.Lock()),
                repository=SimpleNamespace(creation_guard=lambda: None),
            )
        )
    )
    with TestClient(app) as client:
        created = client.post("/api/project-reading", json={"title": "接口阅读"})
        assert created.status_code == 200
        job = created.json()
        assert job["title"] == "接口阅读"
        assert isinstance(job["counts"]["indexed"], int)
        assert client.get("/api/project-reading").json()["latest"]["id"] == job["id"]
        assert client.get(f"/api/project-reading/{job['id']}/documents").json() == {"documents": []}
        invalid = client.post(
            f"/api/project-reading/{job['id']}/documents/fake/review",
            json={"version": 0, "decision": "invalid"},
        )
        assert invalid.status_code == 422


def test_router_mutations_share_project_lock_and_reject_archived_project(reading):
    job = reading.create()
    lock = asyncio.Lock()
    calls = []

    def archived_guard():
        calls.append(lock.locked())
        raise ValueError("项目已经归档，不能开始新的工作")

    app = FastAPI()

    @app.exception_handler(ValueError)
    async def invalid(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    app.include_router(
        create_router(
            SimpleNamespace(
                runtime=SimpleNamespace(project_reading=reading),
                runs=SimpleNamespace(edit_lock=lock),
                repository=SimpleNamespace(creation_guard=archived_guard),
            )
        )
    )
    with TestClient(app) as client:
        for suffix, body in (
            ("", {"title": "forbidden"}),
            (f"/{job['id']}/start", {}),
            (f"/{job['id']}/refresh", {}),
            (f"/{job['id']}/documents/fake/review", {"version": 1, "decision": "approved"}),
        ):
            response = client.post("/api/project-reading" + suffix, json=body)
            assert response.status_code == 409
            assert "归档" in response.json()["detail"]
        assert calls == [True, True, True, True]
        assert len(reading.list()["jobs"]) == 1
        assert reading.get(job["id"])["status"] == "ready"
        # 停止旧工作不受归档写保护阻挡。
        paused = client.post(f"/api/project-reading/{job['id']}/pause")
        assert paused.status_code == 200 and paused.json()["status"] == "paused"
