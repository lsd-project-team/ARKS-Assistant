"""真实临时 Agent/回调/SQLite；仅替换供应商模型，不支付真实API费用。"""

import importlib
import json
import subprocess
import sys

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.core.config import PROJECT_ROOT
from tests.helpers.models import DeterministicModel


@pytest.fixture
def quality(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT_ROOT))
    return importlib.import_module("scripts.verification.code_work_quality.runner")


@pytest.fixture
def fixture_case(quality, tmp_path, monkeypatch):
    workspace = tmp_path / "source"
    workspace.mkdir()
    (workspace / "calc.py").write_bytes(b"answer = 1\n")
    suite = {
        "schema_version": 1,
        "id": "fixture-v1",
        "cases": [
            {
                "id": "qa",
                "kind": "source_qa",
                "question": "请解释calc.py源码当前值并附引用",
                "expected_sources": {"calc.py": quality.file_hash(workspace / "calc.py")},
                "rubric": {"truth": "人工核对当前值与引用范围，不推广为完整业务理解"},
            }
        ],
    }
    cases, config = tmp_path / "cases.json", tmp_path / "provider.json"
    quality.write_json(cases, suite)
    quality.write_json(
        config,
        {
            "model": {
                "base_url": "https://fixture.invalid/v1",
                "model": "fixture-model",
                "context_tokens": 32768,
                "output_tokens": 1024,
            },
            "key_env": "QUALITY_TEST_KEY",
            "timeout_seconds": 30,
        },
    )
    monkeypatch.setenv("QUALITY_TEST_KEY", "fixture-key-only-in-memory")
    return workspace, cases, config, tmp_path / "reports", suite


class EvidenceModel(DeterministicModel):
    mode: str = "qa"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if "独立的源码结论复核器" in str(messages[0].content):
            answer = '{"verdict":"unknown","issues":[],"reason":"语义交给人工核对"}'
            return self.result(AIMessage(content=answer))
        outputs = [message for message in messages if isinstance(message, ToolMessage)]
        values = {message.name: json.loads(message.content) for message in outputs}
        if "read_source" not in values:
            name, args = "read_source", {"path": "calc.py", "start_line": 1, "end_line": 1}
        elif self.mode == "change" and "create_code_change" not in values:
            name, args = (
                "create_code_change",
                {
                    "title": "修改常量",
                    "goal": "answer为2",
                    "acceptance_criteria": ["answer为2"],
                    "allowed_paths": ["calc.py"],
                },
            )
        elif self.mode == "change" and "read_change_file" not in values:
            name, args = (
                "read_change_file",
                {"change_id": values["create_code_change"]["id"], "path": "calc.py"},
            )
        elif self.mode == "change" and "edit_change_file" not in values:
            name, args = (
                "edit_change_file",
                {
                    "change_id": values["create_code_change"]["id"],
                    "path": "calc.py",
                    "before": "answer = 1",
                    "after": "answer = 2",
                    "version": values["read_change_file"]["version"],
                },
            )
        elif self.mode == "change" and "get_change_diff" not in values:
            name, args = "get_change_diff", {"change_id": values["create_code_change"]["id"]}
        elif self.mode == "debug" and "search_debug_issues" not in values:
            name, args = "search_debug_issues", {"query": "E907 参数解析"}
        else:
            return self.result(
                AIMessage(content="当前源码值为1；未作设备验收。[当前源码](source:calc.py#L1)")
            )
        return self.result(
            AIMessage(
                content="", tool_calls=[{"name": name, "args": args, "id": f"step-{len(outputs)}"}]
            )
        )

    @staticmethod
    def result(message):
        message.usage_metadata = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
        return ChatResult(generations=[ChatGeneration(message=message)])


def install_model(monkeypatch, model):
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_a, **_kw: type(model)(mode=model.mode),
    )


async def test_live_flag_and_source_hash_gate_run_before_model_creation(
    quality, fixture_case, monkeypatch
):
    workspace, cases, config, output, suite = fixture_case

    def forbidden(*_args, **_kwargs):
        pytest.fail("前置检查失败时不能创建模型")

    monkeypatch.setattr("app.agents.runtime.graph_builder.create_model", forbidden)
    with pytest.raises(ValueError, match="--live"):
        await quality.run_suite(cases, workspace, config, output)
    suite["cases"][0]["expected_sources"]["calc.py"] = "0" * 64
    quality.write_json(cases, suite)
    with pytest.raises(ValueError, match="源码版本不符"):
        await quality.run_suite(cases, workspace, config, output, live=True)
    assert not output.exists()


async def test_real_runtime_evidence_usage_and_human_review_are_separate(
    quality, fixture_case, monkeypatch
):
    workspace, cases, config, output, _ = fixture_case
    monkeypatch.setattr(
        "app.core.config.SettingsStore.save", lambda *_a, **_kw: pytest.fail("不得持久化密钥配置")
    )
    install_model(monkeypatch, EvidenceModel())
    path = await quality.run_suite(cases, workspace, config, output, live=True)
    report = json.loads(path.read_text(encoding="utf-8"))
    case = report["cases"][0]
    assert report["outcome"] == case["outcome"] == "unknown"
    assert {row["name"]: row["status"] for row in case["checks"]} == {
        "source_integrity": "pass",
        "current_citations": "pass",
        "runtime_completed": "pass",
    }
    assert any(row["kind"] == "provider_usage" for row in case["events"])
    assert case["budget"]["calls"] > 0 and case["budget"]["actual_tokens"] > 0
    assert case["run_id"] and len(report["model_fingerprint"]) == 64
    assert "fixture-key-only-in-memory" not in path.read_text(encoding="utf-8")
    assert (workspace / "calc.py").read_bytes() == b"answer = 1\n"
    second = await quality.run_suite(cases, workspace, config, output, live=True)
    assert path.parent != second.parent
    assert json.loads(second.read_text(encoding="utf-8"))["outcome"] == "unknown"
    review = importlib.import_module("scripts.verification.code_work_quality.review")
    ratings = {
        "truth": {
            "outcome": "pass",
            "rationale": "人工已核对这一教学夹具",
            "evidence": ["answer", "checks.current_citations"],
        }
    }
    saved = review.save_review(path, quality.file_hash(path), "qa", "test-reviewer", ratings)
    assert review.verify_review(path, saved) == "pass"
    # 报告正文被改一字，即使runID不变也不能复用旧评审。
    report["cases"][0]["answer"] += "changed"
    quality.write_json(path, report)
    with pytest.raises(ValueError, match="旧评审失效"):
        review.verify_review(path, saved)


async def test_missing_environment_key_never_creates_model(quality, fixture_case, monkeypatch):
    workspace, cases, config, output, _ = fixture_case
    monkeypatch.delenv("QUALITY_TEST_KEY")
    monkeypatch.setattr(
        "app.agents.runtime.graph_builder.create_model",
        lambda *_a, **_kw: pytest.fail("缺凭据不能创建模型"),
    )
    with pytest.raises(ValueError, match="环境变量"):
        await quality.run_suite(cases, workspace, config, output, live=True)
    assert not output.exists()


class FailedProvider(EvidenceModel):
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("provider rejected fixture-key-only-in-memory")


async def test_actual_provider_exception_records_failure_without_credential(
    quality, fixture_case, monkeypatch
):
    workspace, cases, config, output, _ = fixture_case
    install_model(monkeypatch, FailedProvider())
    path = await quality.run_suite(cases, workspace, config, output, live=True)
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["outcome"] == "failed"
    failure = next(
        row for row in report["cases"][0]["checks"] if row["name"] == "runtime_completed"
    )
    assert failure["status"] == "failed" and failure["evidence"]["type"] == "RuntimeError"
    assert "fixture-key-only-in-memory" not in path.read_text(encoding="utf-8")
    assert report["cases_not_run"] == []


def test_manual_review_cannot_promote_mechanical_failure_or_unknown(quality):
    review = importlib.import_module("scripts.verification.code_work_quality.review")
    ratings = {"truth": {"outcome": "pass", "rationale": "人工说明", "evidence": ["answer"]}}
    case = {
        "rubric": {"truth": "准确"},
        "checks": [{"name": "current_citations", "status": "failed"}],
    }
    assert review.reviewed_outcome(case, ratings, False) == "failed"
    case["checks"][0]["status"] = "unknown"
    assert review.reviewed_outcome(case, ratings, False) == "unknown"
    with pytest.raises(ValueError, match="逐项"):
        review.reviewed_outcome(case, {}, False)


async def test_optional_container_verification_requires_separate_flag(quality, fixture_case):
    workspace, cases, config, output, _ = fixture_case
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["verification_profile"] = {
        "name": "explicit",
        "argv": ["python", "-m", "pytest"],
        "executor": {"kind": "container", "image": "sha256:" + "a" * 64},
    }
    quality.write_json(config, payload)
    with pytest.raises(ValueError, match="--allow-verification"):
        await quality.run_suite(cases, workspace, config, output, live=True)
    payload["verification_profile"]["executor"] = {"kind": "trusted_host"}
    quality.write_json(config, payload)
    with pytest.raises(ValueError, match="沙箱"):
        await quality.run_suite(
            cases, workspace, config, output, live=True, allow_verification=True
        )


async def test_real_agent_isolated_edit_patch_applies_and_reverses_without_quality_pass(
    quality, fixture_case, monkeypatch
):
    workspace, cases, config, output, suite = fixture_case
    suite["cases"][0].update(
        kind="change", question="请在隔离副本修改calc.py，将answer改为2，检查差异，不改原件"
    )
    quality.write_json(cases, suite)
    install_model(monkeypatch, EvidenceModel(mode="change"))
    path = await quality.run_suite(cases, workspace, config, output, live=True)
    case = json.loads(path.read_text(encoding="utf-8"))["cases"][0]
    states = {row["name"]: row["status"] for row in case["checks"]}
    assert (
        states["source_integrity"] == states["isolated_edit"] == states["patch_replay"] == "pass"
    ), case
    assert states["sandbox_verification"] == case["outcome"] == "unknown"
    assert case["changes"][0]["diff"]["files"][0]["path"] == "calc.py"
    assert (workspace / "calc.py").read_bytes() == b"answer = 1\n"


async def test_debug_seed_stays_in_temporary_issue_store_and_actual_prompt_reference(
    quality, fixture_case, monkeypatch
):
    workspace, cases, config, output, suite = fixture_case
    suite["cases"][0].update(
        kind="debug_recall",
        question="E907参数解析历史记录是什么？读取calc.py后引用当前源码和未解决记录",
        debug_issues=[
            {
                "title": "E907 参数解析",
                "payload": {
                    "problem": "E907 参数解析异常",
                    "resolution_status": "open",
                    "investigation": "教学夹具",
                },
            }
        ],
    )
    quality.write_json(cases, suite)
    install_model(monkeypatch, EvidenceModel(mode="debug"))
    path = await quality.run_suite(cases, workspace, config, output, live=True)
    case = json.loads(path.read_text(encoding="utf-8"))["cases"][0]
    proof = next(row for row in case["checks"] if row["name"] == "fixed_debug_reference")
    assert proof["status"] == "pass", case
    assert proof["evidence"]["fixtures"][0]["version"] == 1
    assert case["outcome"] == "unknown"


@pytest.mark.parametrize("folder", ["data", "backend", "frontend", "scripts", ".git"])
def test_internal_and_formal_directories_are_rejected_before_read(quality, folder):
    with pytest.raises(ValueError, match="拒绝"):
        quality.checked_path(PROJECT_ROOT / folder, source=True)


def test_citation_version_drift_and_non_applicable_patch_are_counterexamples(quality, tmp_path):
    module = importlib.import_module("scripts.verification.code_work_quality.evaluation")
    from app.modules.source_analysis.workspace import Workspace

    root = tmp_path / "source"
    root.mkdir()
    file = root / "calc.py"
    file.write_bytes(b"answer = 1\n")
    before = {"calc.py": quality.file_hash(file)}
    events = [
        {
            "kind": "source_evidence",
            "payload": {"path": "calc.py", "version": "0" * 64, "start_line": 1, "end_line": 1},
        }
    ]
    checks = module.source_checks(Workspace(root), "[code](source:calc.py#L1)", events, before)
    assert next(row for row in checks if row["name"] == "current_citations")["status"] == "failed"
    assert module.replay_patch(root, root, "invalid patch")["status"] == "failed"
    file.write_bytes(b"external changed\n")
    checks = module.source_checks(Workspace(root), "unknown", [], before)
    assert checks[0]["status"] == "failed" and checks[0]["evidence"]["changed"] == ["calc.py"]


@pytest.mark.parametrize("field,value", [("api_key", "forbidden"), ("password", "forbidden")])
def test_config_cannot_hold_credentials(quality, field, value):
    contract = importlib.import_module("scripts.verification.code_work_quality.contracts")
    with pytest.raises(ValueError, match="API密钥"):
        contract.ProviderConfig(
            model={"model": "fixture", "base_url": "https://fixture.invalid", field: value},
            key_env="FIXTURE_KEY",
        )


def test_sample_sources_have_real_hashes_and_do_not_overwrite(quality, tmp_path):
    samples = importlib.import_module("scripts.verification.code_work_quality.samples")
    target = samples.create_sample(tmp_path / "teaching")
    suite = quality.Suite.model_validate_json((target / "cases.json").read_text(encoding="utf-8"))
    for case in suite.cases:
        quality.snapshot(target / "workspace", case)
    with pytest.raises(FileExistsError):
        samples.create_sample(target)


def test_cli_without_live_stops_before_reading_missing_config(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.verification.code_work_quality",
            "run",
            "--cases",
            str(tmp_path / "missing-cases.json"),
            "--workspace",
            str(tmp_path / "missing-source"),
            "--config",
            str(tmp_path / "missing-config.json"),
            "--output",
            str(tmp_path / "reports"),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1 and b"--live" in result.stderr
    assert not (tmp_path / "reports").exists()
