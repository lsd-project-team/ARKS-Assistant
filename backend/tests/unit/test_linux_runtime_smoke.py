"""验收脚本自身的路径/凭据/失败边界，不用替身伪造Linux运行通过。"""

import importlib
import json

import httpx
import pytest

from app.core.config import PROJECT_ROOT


@pytest.fixture
def smoke(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT_ROOT))
    return importlib.import_module("scripts.verification.linux_runtime.runner")


@pytest.mark.parametrize(
    "value", ["", "relative-folder", str(PROJECT_ROOT), str(PROJECT_ROOT.parent)]
)
def test_smoke_root_rejects_missing_relative_and_application_locations(smoke, value):
    with pytest.raises(smoke.SmokeFailure):
        smoke.prepare_root(value)


def test_smoke_root_never_adopts_existing_files_and_requires_marker(smoke, tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    preserved = existing / "original"
    preserved.write_bytes(b"preserve")
    with pytest.raises(smoke.SmokeFailure, match="not_empty"):
        smoke.prepare_root(str(existing))
    assert preserved.read_bytes() == b"preserve"
    root, token = smoke.prepare_root(str(tmp_path / "new"))
    assert smoke.write_report(root, token, {"check": True}, {"source": "a" * 64})["ok"]
    with pytest.raises(smoke.SmokeFailure, match="identity_changed"):
        smoke.write_report(root, "wrong-owner", {}, {})


def test_smoke_environment_drops_formal_paths_and_secrets(smoke, tmp_path, monkeypatch):
    monkeypatch.setenv("TRUNK_AGENT_DATA_DIR", "formal-data-must-not-be-used")
    monkeypatch.setenv("TRUNK_AGENT_WORKSPACE", "formal-source-must-not-be-used")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
    monkeypatch.setenv("HTTP_PROXY", "must-not-inherit-proxy")
    monkeypatch.setenv("PYTHONPATH", "must-not-inherit-pythonpath")
    env = smoke.environment(
        tmp_path, tmp_path / "data", tmp_path / "source", smoke.ORIGIN, "arks-smoke.example.invalid"
    )
    assert env["TRUNK_AGENT_DATA_DIR"] == str(tmp_path / "data")
    assert env["TRUNK_AGENT_WORKSPACE"] == str(tmp_path / "source")
    assert "OPENAI_API_KEY" not in env and "HTTP_PROXY" not in env
    assert "must-not-inherit" not in json.dumps(env)
    assert env["HF_HUB_OFFLINE"] == "1"
    assert env["ARKS_ALLOWED_ORIGINS"] == smoke.ORIGIN


def test_http_failure_never_uses_response_body_in_error(smoke):
    calls = []

    class Client:
        def request(self, method, url, **kwargs):
            calls.append((method, url))
            return httpx.Response(500, content=b"private-password-session-csrf")

    with pytest.raises(smoke.SmokeFailure) as error:
        smoke.request(Client(), "GET", "/only-fixture")
    assert str(error.value) == "http_unexpected_status"
    assert calls == [("GET", "/only-fixture")]


def test_main_failure_report_and_stderr_are_generic(smoke, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(smoke.sys, "platform", "linux")
    root = tmp_path / "smoke"
    monkeypatch.setenv("ARKS_LINUX_SMOKE_ROOT", str(root))

    def failed(*args):
        raise RuntimeError("private-password-session-csrf")

    monkeypatch.setattr(smoke, "execute", failed)
    assert smoke.main() == 1
    output = capsys.readouterr()
    assert output.out == "" and output.err == "linux_runtime_smoke_failed:runtime_error\n"
    assert json.loads((root / "report.json").read_text()) == {
        "ok": False,
        "checks": {},
        "hashes": {},
        "error": "runtime_error",
    }


def test_report_rejects_arbitrary_text_and_values(smoke, tmp_path):
    root, token = smoke.prepare_root(str(tmp_path / "smoke"))
    with pytest.raises(smoke.SmokeFailure, match="unsafe_report_name"):
        smoke.write_report(root, token, {"private body text": True}, {})
    with pytest.raises(smoke.SmokeFailure, match="unsafe_report_value"):
        smoke.write_report(root, token, {"check": "password"}, {})


def test_restore_wrapper_keeps_exact_explicit_mount_root(smoke, tmp_path, monkeypatch):
    module = importlib.import_module("scripts.verification.linux_runtime.persistence")
    storage = importlib.import_module("app.infrastructure.storage.restore")
    root, token = smoke.prepare_root(str(tmp_path / "smoke"))
    target, target_token = smoke.prepare_root(str(tmp_path / "separate-volume"))
    incoming = root / "backup.zip"
    calls = []

    def restore_archive(archive, destination):
        calls.append((archive, destination))
        return {"restored": True}

    monkeypatch.setattr(storage, "restore_backup", restore_archive)
    monkeypatch.setattr(module, "database_integrity", lambda data: calls.append(data))
    assert module.restore(incoming, root, token, target, target_token) == target
    assert calls == [(incoming, target), target]
    assert (target / ".arks-linux-runtime-smoke").is_file()
