"""构建前置、升级与 HTTP 权限的真实临时文件/SQLite 验证。"""

import asyncio
import importlib.util
import json
import sys
from types import SimpleNamespace

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import PROJECT_ROOT
from app.modules.auth.middleware import install_authentication
from app.modules.auth.router import create_router as auth_router
from app.modules.auth.service import AuthService
from app.modules.code_changes import CodeChanges
from app.modules.code_changes.policy import WorkPolicy
from app.modules.code_changes.processes import VerificationTask, run_process
from app.modules.code_changes.readiness import inspect_project
from app.modules.code_changes.router import create_router
from tests.helpers.accounts import sign_in


def test_declared_legacy_environment_and_external_dependencies_are_not_build_success(tmp_path):
    (tmp_path / "local.dll").write_bytes(b"fixture")
    (tmp_path / "Legacy.csproj").write_text(
        """<Project ToolsVersion="4.0">
      <PropertyGroup><TargetFrameworkVersion>v4.8</TargetFrameworkVersion></PropertyGroup>
      <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|x64'" />
      <ItemGroup><Reference Include="Local"><HintPath>local.dll</HintPath></Reference>
      <Reference Include="Missing"><HintPath>missing.dll</HintPath></Reference>
      <Reference Include="Private"><HintPath>C:\\private\\secret.dll</HintPath></Reference>
      <ProjectReference Include="../outside.csproj" /></ItemGroup>
      <Import Project="$(MSBuildToolsPath)/Microsoft.CSharp.targets" />
    </Project>""",
        encoding="utf-8",
    )
    report = inspect_project(SimpleNamespace(root=tmp_path))
    assert report["buildable"] is None
    assert report["status"] == "blocked"
    project = report["projects"][0]
    assert project["target_frameworks"] == ["v4.8"]
    assert project["requires_windows"] is True
    assert project["configurations"] == ["Debug"]
    assert project["platforms"] == ["x64"]
    assert [item["status"] for item in project["references"]] == ["exists", "missing", "external"]
    assert project["imports"][0]["status"] == "dynamic"
    assert "C:\\private" not in json.dumps(report)
    assert "独立 Windows" in " ".join(report["requirements"])


@pytest.mark.parametrize("document", ["<broken", '<!DOCTYPE x [<!ENTITY a "x">]><Project />'])
def test_bad_project_is_reported_without_losing_good_projects(tmp_path, document):
    (tmp_path / "bad.csproj").write_text(document, encoding="utf-8")
    (tmp_path / "good.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework>'
        "</PropertyGroup></Project>",
        encoding="utf-8",
    )
    report = inspect_project(SimpleNamespace(root=tmp_path))
    assert len(report["projects"]) == 2
    assert report["projects"][1]["target_frameworks"] == ["net8.0"]
    assert not report["projects"][1]["requires_windows"]
    assert any(item["code"] == "project_parse_error" for item in report["issues"])
    assert report["buildable"] is None


def test_solution_and_attached_root_are_only_declarations(tmp_path):
    (tmp_path / "project.sln").write_text(
        "Microsoft Visual Studio Solution File, Format Version 12.00\n"
        'Project("{x}") = "Missing", "missing.csproj", "{y}"\n'
        "GlobalSection(SolutionConfigurationPlatforms) = preSolution\n"
        " Debug|Any CPU = Debug|Any CPU\nEndGlobalSection\n",
        encoding="utf-8",
    )
    report = inspect_project(
        SimpleNamespace(root=tmp_path, attached={"lib": ("私有库", tmp_path.parent)})
    )
    assert report["solutions"][0]["projects"][0]["status"] == "missing"
    assert report["solutions"][0]["configurations"] == ["Debug|Any CPU"]
    assert report["attached_sources"][0]["status"] == "not_included_in_copy"
    assert any(item["code"] == "attached_sources_not_supported" for item in report["issues"])


def test_readiness_upgrade_preserves_old_rows_and_marks_old_executor_as_host(tmp_path):
    path = PROJECT_ROOT / "backend/migrations/versions/0020_code_work_readiness.py"
    spec = importlib.util.spec_from_file_location("readiness_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.sqlite3').as_posix()}")
    try:
        with engine.begin() as connection:
            for table in migration.COLUMNS:
                connection.execute(text(f"CREATE TABLE {table} (id TEXT PRIMARY KEY, body TEXT)"))
                connection.execute(text(f"INSERT INTO {table} VALUES ('old','原记录')"))
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                migration.upgrade()
            assert connection.execute(text("SELECT body FROM code_changes")).scalar() == "原记录"
            executor = connection.execute(
                text("SELECT executor_json FROM code_verifications")
            ).scalar()
            assert json.loads(executor)["kind"] == "trusted_host"
            assert connection.execute(text("SELECT review_json FROM code_changes")).scalar() == "{}"
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
            assert connection.execute(text("SELECT body FROM code_changes")).scalar() == "原记录"
    finally:
        engine.dispose()


def test_trusted_host_log_flood_is_failed_and_bounded(tmp_path):
    task = VerificationTask("project", "change", "verification")
    log = tmp_path / "verification.log"
    status, code, error = run_process(
        task,
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('x'*100000); sys.stdout.flush()",
        ],
        tmp_path,
        log,
        5,
        max_log_bytes=1024,
    )
    assert status == "failed"
    assert "日志" in error
    assert log.stat().st_size <= 1024
    assert task.process.poll() is not None


def test_container_transfer_limits_reserve_peak_space_and_parallel_capacity(services):
    paths, database, *_ = services
    policy = WorkPolicy(paths, database, "quota-project")
    scope = paths.scratch / "quota-project"
    scope.mkdir()
    mib = 1024 * 1024
    policy.save(
        {"max_storage_mb": 200, "min_free_mb": 0, "max_log_mb": 1, "max_active_verifications": 2}
    )
    (scope / "existing").write_bytes(b"x" * mib)
    limits = policy.limits(scope)
    assert 2 * (3 * limits["max_output_bytes"] + 65 * mib) + mib <= 200 * mib
    policy.save({"max_storage_mb": 100, "min_free_mb": 0, "max_log_mb": 100})
    with pytest.raises(ValueError, match="临时空间不足"):
        policy.limits(scope)


@pytest.fixture
def api(services):
    paths, database, workspace, repository, *_ = services
    changes = CodeChanges(paths, database, workspace, "test-project")
    auth = AuthService(database, paths)
    auth.initialize()
    app = FastAPI()
    app.state.auth = auth
    install_authentication(app, auth)
    app.include_router(auth_router(auth))
    app.include_router(
        create_router(
            SimpleNamespace(
                runtime=SimpleNamespace(code_changes=changes),
                repository=repository,
                runs=SimpleNamespace(edit_lock=asyncio.Lock()),
            )
        )
    )

    @app.exception_handler(ValueError)
    async def invalid(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    with TestClient(app) as client:
        yield client, changes
    asyncio.run(changes.shutdown())


@pytest.mark.authentication
def test_readiness_policy_executor_requirements_and_review_guards_over_http(api):
    client, changes = api
    assert client.get("/api/code-changes/readiness").status_code == 401
    sign_in(client, "user")
    report = client.get("/api/code-changes/readiness")
    assert report.status_code == 200
    assert report.json()["project"]["buildable"] is None
    policy = client.get("/api/code-changes/policy").json()
    assert client.put("/api/code-changes/policy", json=policy).status_code == 403
    assert client.post("/api/code-changes/cleanup", json={"dry_run": False}).status_code == 403
    created = client.post(
        "/api/code-changes",
        json={
            "title": "范围限制",
            "goal": "保留用户验收",
            "acceptance_criteria": ["入口可编译"],
            "constraints": "保持原有接口",
            "allowed_paths": ["Program.cs"],
        },
    ).json()
    identifier = created["id"]
    assert created["acceptance_criteria"] == ["入口可编译"]
    assert created["constraints"] == "保持原有接口"
    assert created["allowed_paths"] == ["Program.cs"]
    assert client.get(f"/api/code-changes/{identifier}/verifications").json() == {
        "verifications": []
    }
    assert (
        client.post(
            f"/api/code-changes/{identifier}/review",
            json={
                "change_version": created["change_version"],
                "requirements_version": created["requirements_version"],
                "notes": "没有验证不能审核",
            },
        ).status_code
        == 409
    )
    assert client.post(f"/api/code-changes/{identifier}/delivery").status_code == 409
    assert (
        client.post(
            "/api/code-changes",
            json={
                "title": "越界",
                "goal": "拒绝",
                "allowed_paths": ["../outside"],
            },
        ).status_code
        == 422
    )
    sign_in(client, "admin")
    base = {"name": "显式命令", "argv": [sys.executable, "-c", "print('ok')"]}
    assert client.post("/api/code-changes/profiles", json=base).status_code == 422
    assert (
        client.post(
            "/api/code-changes/profiles",
            json={
                **base,
                "executor": {
                    "kind": "container",
                    "image": "python:latest",
                },
            },
        ).status_code
        == 422
    )
    configured = client.post(
        "/api/code-changes/profiles",
        json={
            **base,
            "executor": {"kind": "trusted_host"},
            "baseline_required": True,
            "category": "test",
            "environment_label": "实际临时Python",
        },
    )
    assert configured.status_code == 200, configured.text
    profile = configured.json()
    assert profile["baseline_required"] and profile["category"] == "test"
    assert profile["executor"]["kind"] == "trusted_host"
    started = client.post(
        f"/api/code-changes/{identifier}/verify",
        json={
            "profile_id": profile["id"],
            "purpose": "baseline",
        },
    )
    assert started.status_code == 200, started.text
    completed = asyncio.run(changes.wait(identifier, 10))
    assert completed["latest_verification"]["purpose"] == "baseline"
    assert completed["latest_verification"]["status"] == "passed"
    assert completed["status"] == "ready"
    saved = client.put("/api/code-changes/policy", json={**policy, "max_log_mb": 2})
    assert saved.status_code == 200 and saved.json()["max_log_mb"] == 2
    assert client.post("/api/code-changes/cleanup", json={"dry_run": True}).json()["removed"] == 0


def test_review_http_binds_the_displayed_requirements_and_requires_explicit_hash(api):
    client, changes = api
    sign_in(client, "user")
    changes.policy.save({"min_free_mb": 0, "require_sandbox_delivery": False})
    change = client.post(
        "/api/code-changes",
        json={
            "title": "审核需求身份",
            "goal": "只审核已查看的验收",
            "acceptance_criteria": ["入口为 Start"],
        },
    ).json()
    url = f"/api/code-changes/{change['id']}"
    for invalid in ({}, {"requirements_version": ""}, {"requirements_version": "g" * 64}):
        result = client.post(
            f"{url}/review", json={"change_version": change["change_version"], **invalid}
        )
        assert result.status_code == 422, result.text
    source = changes.read_file(change["id"], "Program.cs")
    changes.edit_file(
        change["id"],
        "Program.cs",
        "Main",
        "Start",
        source["version"],
        expected_requirements=source["requirements_version"],
    )
    profile = changes.save_profile(
        "真实临时 Python",
        [sys.executable, "-c", "print('verified')"],
        5,
        executor={"kind": "trusted_host"},
        baseline_required=False,
    )
    changes.verify(change["id"], profile["id"])
    displayed = asyncio.run(changes.wait(change["id"], 10))
    assert displayed["status"] == "passed"
    updated = client.put(
        f"{url}/requirements",
        json={
            **{
                key: displayed[key]
                for key in (
                    "title",
                    "goal",
                    "constraints",
                    "allowed_paths",
                    "change_version",
                    "requirements_version",
                )
            },
            "acceptance_criteria": ["入口为 Start 且接口不变"],
        },
    )
    assert updated.status_code == 200, updated.text
    changes.verify(change["id"], profile["id"])
    current = asyncio.run(changes.wait(change["id"], 10))
    assert current["status"] == "passed"
    assert current["change_version"] == displayed["change_version"]
    old_review = client.post(
        f"{url}/review",
        json={key: displayed[key] for key in ("change_version", "requirements_version")},
    )
    assert old_review.status_code == 409, old_review.text
    assert "需求约定已变化" in old_review.json()["detail"]
    assert client.get(url).json()["review"] is None
    assert client.post(f"{url}/delivery").status_code == 409
    current_review = client.post(
        f"{url}/review",
        json={key: current[key] for key in ("change_version", "requirements_version")},
    )
    assert current_review.status_code == 200, current_review.text
    assert (
        current_review.json()["review"]["requirements_version"] == current["requirements_version"]
    )
    assert client.post(f"{url}/delivery").status_code == 200
