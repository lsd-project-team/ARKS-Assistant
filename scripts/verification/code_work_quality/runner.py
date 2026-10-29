"""复用真实应用服务；每个场景使用一次性数据库、检查点及副本。"""

import asyncio
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.bootstrap import create_services
from app.core.config import PROJECT_ROOT, Paths
from app.infrastructure.database.registry import Base
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.projects.models import Project

from .contracts import ProviderConfig, Suite
from .evaluation import change_evidence, check, source_checks
from .safety import (
    checked_path,
    clean,
    file_hash,
    json_hash,
    overlaps,
    snapshot,
    verify_expected,
    write_json,
)

EVENTS = {
    "source_evidence",
    "answer_validation",
    "source_review",
    "source_review_context",
    "code_change_reference",
    "provider_usage",
    "knowledge_reference",
    "knowledge_search",
    "run_completion",
    "tool_start",
    "tool_end",
}


def application_version():
    root = PROJECT_ROOT / "backend/app"
    return json_hash(
        {path.relative_to(root).as_posix(): file_hash(path) for path in sorted(root.rglob("*.py"))}
    )


async def execute_case(workspace, case, config, key, before):
    with tempfile.TemporaryDirectory(prefix="cw-quality-") as temporary:
        services = create_services(Paths(Path(temporary) / "data", workspace))
        try:
            return await _execute_case(services, workspace, case, config, key, before)
        finally:
            await services.runtime.code_changes.shutdown()
            services.runtime.semantic.close()
            services.database.close()


async def _execute_case(services, workspace, case, config, key, before):
    runtime, repository = services.runtime, services.repository
    Base.metadata.create_all(services.database.engine)
    project_id = uuid4().hex
    with services.database.session.begin() as session:
        session.add(Project(id=project_id, name="一次性质量场景", source_root=str(workspace)))
    repository.project_id = project_id
    settings = config.settings(key)
    services.settings.load = lambda: settings  # 凭据只在内存，不调用 SettingsStore.save。
    runtime.code_changes.policy.save({"reading_token_limit": config.token_limit, "min_free_mb": 0})
    profile = config.verification_profile
    if profile:
        runtime.code_changes.save_profile(
            profile.name,
            profile.argv,
            profile.timeout_seconds,
            identifier=profile.id,
            executor=profile.executor.model_dump(),
            baseline_required=profile.baseline_required,
            category=profile.category,
            environment_label=profile.environment_label,
        )
    seeds = []
    store = HandoverStore(database=services.database)
    for item in case.debug_issues:
        row = store.create("debug_issue", item["title"], item["payload"], "质量场景夹具")
        seeds.append(
            {"id": row["id"], "version": row["version"], "fixture_sha256": json_hash(item)}
        )
    run = repository.create_run(
        None,
        case.question,
        [],
        {
            "use_memory": False,
            "use_knowledge": case.kind == "debug_recall",
            "use_deepwiki": False,
        },
    )
    answer, failure = "", None

    def emit(kind, payload):
        repository.event(run["id"], kind, clean(payload, key))

    try:
        async with asyncio.timeout(config.timeout_seconds):
            answer = clean(await runtime.execute(run, emit), key)
            repository.finish(run["id"], answer)
    except Exception as error:
        failure = {"type": type(error).__name__, "message": clean(str(error), key)}
        repository.set_status(run["id"], "failed", failure["message"])
    finally:
        await runtime.code_changes.shutdown()
        runtime.semantic.close()
    events, cursor = [], 0
    while True:
        page = repository.events(run["id"], cursor)
        events.extend(row for row in page if row["kind"] in EVENTS)
        if len(page) < 500:
            break
        cursor = page[-1]["sequence"]
    checks = await asyncio.to_thread(source_checks, services.workspace, answer, events, before)
    checks.append(
        check(
            "runtime_completed",
            "failed" if failure else "pass",
            failure or {"run_id": run["id"]},
        )
    )
    try:
        changes = await asyncio.to_thread(change_evidence, runtime.code_changes)
    except (OSError, ValueError) as error:
        changes = []
        checks.append(check("change_evidence", "failed", {"error": str(error)}))
    if case.kind == "change":
        checks.append(
            check(
                "isolated_edit",
                "pass" if changes and all(row["diff"]["files"] for row in changes) else "failed",
                [row["change"]["id"] for row in changes],
            )
        )
        checks.extend(row["patch_replay"] for row in changes)
        proofs = [
            proof
            for row in changes
            for proof in row["verifications"]
            if proof["purpose"] == "change"
        ]
        checks.append(
            check(
                "sandbox_verification",
                "unknown"
                if not proofs
                else "pass"
                if all(
                    row["status"] == "passed"
                    and not row["stale"]
                    and row["executor"]["kind"] == "container"
                    for row in proofs
                )
                else "failed",
                proofs,
            )
        )
    if case.kind == "debug_recall":
        references = [
            row["payload"]
            for row in events
            if row["kind"] == "knowledge_reference" and row["payload"].get("kind") == "debug_issue"
        ]
        expected = {(row["id"], row["version"]) for row in seeds}
        checks.append(
            check(
                "fixed_debug_reference",
                "pass"
                if any((row["id"], row["version"]) in expected for row in references)
                else "failed",
                {"fixtures": seeds, "observed": references},
            )
        )
    sanitized = clean(
        {
            "case_id": case.id,
            "kind": case.kind,
            "question": case.question,
            "run_id": run["id"],
            "rubric": case.rubric,
            "expected_sources": case.expected_sources,
            "answer": answer,
            "checks": checks,
            "events": events,
            "changes": changes,
            "budget": runtime.code_changes.policy.tokens(),
            "outcome": "failed" if any(row["status"] == "failed" for row in checks) else "unknown",
        },
        key,
    )
    for original, masked in zip(changes, sanitized["changes"], strict=True):
        masked["patch_redacted"] = original["patch"] != masked["patch"]
    return sanitized


async def run_suite(
    cases_path, workspace, config_path, output, *, live=False, allow_verification=False
):
    if not live:
        raise ValueError("必须显式指定--live；真实Agent会消耗供应商API与项目Token额度")
    workspace = checked_path(workspace, source=True)
    cases_path, config_path, output = map(checked_path, (cases_path, config_path, output))
    if any(overlaps(path, workspace) for path in (cases_path, config_path, output)):
        raise ValueError("场景、配置和报告必须在源码目录之外")
    suite = Suite.model_validate_json(cases_path.read_text(encoding="utf-8"))
    config = ProviderConfig.model_validate_json(config_path.read_text(encoding="utf-8"))
    if config.verification_profile and not allow_verification:
        raise ValueError("配置了沙箱命令，须显式指定--allow-verification")
    before, source_fingerprint = snapshot(workspace, suite.cases[0])
    for case in suite.cases[1:]:
        verify_expected(workspace, case, before)
    key = os.environ.get(config.key_env, "")
    if not key:
        raise ValueError("指定环境变量未提供API密钥；未请求供应商")
    destination = output / uuid4().hex
    destination.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": 1,
        "report_id": destination.name,
        "suite_id": suite.id,
        "created_at": datetime.now(UTC).isoformat(),
        "suite_sha256": file_hash(cases_path),
        "application_sha256": application_version(),
        "source_fingerprint": source_fingerprint,
        "sources": before,
        "configuration": config.public(),
        "model_fingerprint": json_hash(config.public()),
        "execution": "live_requested",
        "requested_cases": [case.id for case in suite.cases],
        "cases_not_run": [case.id for case in suite.cases],
        "cases": [],
        "outcome": "unknown",
    }
    path = destination / "report.json"
    write_json(path, clean(report, key))
    for case in suite.cases:
        # 场景初始化失败也留下明确失败；已经写出的前一场证据不能被后续异常覆盖。
        try:
            result = await execute_case(workspace, case, config, key, before)
        except Exception as error:
            result = {
                "case_id": case.id,
                "kind": case.kind,
                "run_id": None,
                "rubric": case.rubric,
                "expected_sources": case.expected_sources,
                "outcome": "failed",
                "checks": [
                    check(
                        "case_error",
                        "failed",
                        {"type": type(error).__name__, "message": str(error)},
                    )
                ],
            }
        report["cases"].append(result)
        report["cases_not_run"].remove(case.id)
        report["outcome"] = (
            "failed" if any(row["outcome"] == "failed" for row in report["cases"]) else "unknown"
        )
        write_json(path, clean(report, key))
        if any(
            row["name"] == "source_integrity" and row["status"] == "failed"
            for row in result["checks"]
        ):
            break  # 外部源码已变，保留失败证据，不继续花费或自动恢复原件。
    return path
