"""阅读依赖缺失的真实 SQLite 反例；分析替身只代替外部供应商。"""

import asyncio
import json

import pytest
from sqlalchemy import select

from app.modules.source_analysis.collection import SourceCollection
from app.modules.source_analysis.reading import ProjectReading
from app.modules.source_analysis.reading.models import ProjectReadingDocument
from app.modules.source_analysis.workspace import Workspace


@pytest.fixture
def reading(services):
    paths, database, workspace, *_ = services
    (workspace.root / "Program.cs").unlink()
    for name, text in {
        "A.cs": "class Helper { public static int Run() => 1; }\n",
        "B.cs": "class B { public int Call() => Helper.Run(); }\n",
        "C.cs": "class C { public int Call() => new B().Call(); }\n",
    }.items():
        (workspace.root / name).write_text(text, encoding="utf-8")
    return ProjectReading(paths, database, workspace, "dependency-project")


async def run(reading, declarations):
    async def analyzer(text, info):
        assert text == reading.workspace.resolve(info["path"]).read_bytes().decode("utf-8")
        return {"summary": info["path"], **declarations.get(info["path"], {})}

    job = reading.create()
    await reading.start(job["id"], analyzer)
    await asyncio.gather(*list(reading.tasks.values()))
    assert reading.get(job["id"])["status"] == "completed"
    return job, analyzer


def by_path(reading, job):
    return {row["path"]: row for row in reading.documents(job["id"])}


@pytest.mark.parametrize("unresolved", [["Helper.Run"], [], ["missing/Helper.cs"]])
async def test_unknown_or_omitted_dependencies_use_snapshot_and_propagate_to_dependents(
    reading, unresolved
):
    job, analyzer = await run(
        reading,
        {
            "A.cs": {"dependency_paths": ["A.cs"]},
            "B.cs": {"dependencies": unresolved},
            "C.cs": {"dependency_paths": ["B.cs"]},
        },
    )
    before = by_path(reading, job)
    assert before["B.cs"]["dependency_coverage"] == "unknown"
    assert before["B.cs"]["unresolved_dependencies"] == unresolved
    assert before["C.cs"]["dependency_coverage"] == "declared_only"
    assert {row["path"] for row in reading.prompt("C.cs", 10000)[1]} == {"A.cs", "B.cs", "C.cs"}
    (reading.workspace.root / "A.cs").write_text("class Helper { public static int Run() => 2; }\n")
    assert reading.prompt("C.cs", 10000) == ("", [])
    refreshed = reading.refresh(job["id"])
    assert refreshed["counts"]["stale"] == 3
    assert all(row["status"] == "stale" for row in reading.documents(job["id"]))
    await reading.start(job["id"], analyzer)
    await asyncio.gather(*list(reading.tasks.values()))
    after = by_path(reading, job)
    assert all(after[path]["version"] > before[path]["version"] for path in before)
    assert reading.prompt("C.cs", 10000)[1]


async def test_legacy_list_dependencies_are_not_trusted_without_saved_snapshot(reading):
    job, analyzer = await run(
        reading,
        {
            "A.cs": {"dependency_paths": ["A.cs"]},
            "B.cs": {"dependency_paths": ["A.cs"]},
            "C.cs": {"dependency_paths": ["B.cs"]},
        },
    )
    with reading.database.session.begin() as session:
        record = session.scalar(
            select(ProjectReadingDocument).where(
                ProjectReadingDocument.job_id == job["id"], ProjectReadingDocument.path == "B.cs"
            )
        )
        record.dependencies_json = json.dumps(["A.cs"])
        record.status = "approved"
    _, documents = reading.prompt("C.cs", 10000)
    assert {row["path"] for row in documents} == {"A.cs"}
    public = by_path(reading, job)["B.cs"]
    assert public["dependencies"] == ["A.cs"] and public["dependency_coverage"] == "unknown"
    reading.refresh(job["id"])
    current = by_path(reading, job)
    assert current["A.cs"]["status"] == "analyzed"
    assert current["B.cs"]["status"] == current["C.cs"]["status"] == "stale"
    await reading.start(job["id"], analyzer)
    await asyncio.gather(*list(reading.tasks.values()))
    assert by_path(reading, job)["B.cs"]["dependency_coverage"] == "declared_only"
    assert len(reading.prompt("C.cs", 10000)[1]) == 3


async def test_explicit_path_cycles_terminate_and_only_known_dependents_invalidate(reading):
    job, _ = await run(
        reading,
        {
            "A.cs": {"dependency_paths": ["./B.cs"]},
            "B.cs": {"dependency_paths": ["A.cs"]},
            "C.cs": {"dependency_paths": ["C.cs"]},
        },
    )
    assert len(reading.prompt("C.cs", 10000)[1]) == 3
    (reading.workspace.root / "A.cs").write_text("class Changed {}\n")
    assert {row["path"] for row in reading.prompt("C.cs", 10000)[1]} == {"C.cs"}
    assert reading.refresh(job["id"])["counts"]["stale"] == 2
    assert by_path(reading, job)["C.cs"]["status"] == "analyzed"


async def test_unknown_guard_detects_added_and_deleted_sources_before_refresh(reading):
    job, _ = await run(reading, {})
    added = reading.workspace.root / "New.cs"
    added.write_text("class New {}\n")
    assert reading.prompt("C.cs", 10000) == ("", [])
    added.unlink()
    assert reading.prompt("C.cs", 10000)[1]
    (reading.workspace.root / "A.cs").unlink()
    assert reading.prompt("C.cs", 10000) == ("", [])
    assert reading.refresh(job["id"])["counts"]["analyzed"] == 0


async def test_attached_source_prefix_is_bound_and_cross_root_change_invalidates(reading, tmp_path):
    extra = tmp_path / "dependency-root"
    extra.mkdir()
    (extra / "Helper.cs").write_text("class ExtraHelper {}\n")
    source_id = Workspace(extra).id
    relative = f"@sources/{source_id}/Helper.cs"
    reading.workspace = SourceCollection(
        reading.workspace.root, [{"source_id": source_id, "root": str(extra), "label": "依赖"}]
    )
    job, _ = await run(
        reading,
        {
            "A.cs": {"dependency_paths": [relative]},
            "B.cs": {"dependency_paths": ["A.cs"]},
            "C.cs": {"dependency_paths": ["B.cs"]},
            relative: {"dependency_paths": [relative]},
        },
    )
    assert by_path(reading, job)["A.cs"]["dependency_paths"] == [relative]
    (extra / "Helper.cs").write_text("class ChangedExtraHelper {}\n")
    assert reading.prompt("C.cs", 15000) == ("", [])
    assert reading.refresh(job["id"])["counts"]["stale"] == 4


async def test_module_name_dependency_tracks_new_members_instead_of_freezing_old_files(reading):
    module = reading.workspace.root / "src"
    module.mkdir()
    (module / "Helper.cs").write_text("class ModuleHelper {}\n")
    job, _ = await run(
        reading,
        {
            "A.cs": {"dependency_paths": ["A.cs"]},
            "B.cs": {"dependencies": ["src"]},
            "C.cs": {"dependency_paths": ["B.cs"]},
            "src/Helper.cs": {"dependency_paths": ["src/Helper.cs"]},
        },
    )
    (module / "Added.cs").write_text("class AddedHelper {}\n")
    assert all(row["path"] not in {"B.cs", "C.cs"} for row in reading.prompt("C.cs", 15000)[1])
    assert by_path(reading, job)["B.cs"]["unresolved_dependencies"] == ["src"]
    reading.refresh(job["id"])
    documents = by_path(reading, job)
    assert documents["B.cs"]["status"] == documents["C.cs"]["status"] == "stale"
    assert documents["A.cs"]["status"] == "analyzed"
