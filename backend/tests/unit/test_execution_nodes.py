import pytest

from app.infrastructure.execution import cleanup_orphans, cli, probe_executor, runner


def executor():
    return {"kind": "container", "platform": "linux", "image": "sha256:" + "a" * 64}


@pytest.mark.parametrize(
    "replacement", [{"kind": "trusted_host"}, {"image": "python:latest"}, {"platform": "unknown"}]
)
def test_invalid_executor_is_rejected_without_docker(monkeypatch, replacement):
    monkeypatch.setattr(cli, "object_result", lambda *args: pytest.fail("must not contact daemon"))
    result = probe_executor({**executor(), **replacement})
    assert result["available"] is False
    assert result["error"]


@pytest.mark.parametrize(
    "config_update",
    [
        {"Labels": {"io.arks.executor.version": "1"}},
        {"User": "1000:1000"},
        {"Volumes": {"/socket": {}}},
        {"Entrypoint": ["/bin/sh"]},
    ],
)
def test_old_or_unsafe_image_is_rejected(monkeypatch, config_update):
    config = {
        "User": "0:0",
        "Volumes": None,
        "Labels": {"io.arks.executor.version": "2", "io.arks.executor.platform": "linux"},
        "Entrypoint": ["/usr/local/bin/python", "-I", "/opt/arks/supervisor.py"],
    }
    config.update(config_update)
    monkeypatch.setattr(
        cli,
        "object_result",
        lambda settings, action, *args: (
            {"OSType": "linux"}
            if action == "info"
            else [{"Os": "linux", "Id": executor()["image"], "Config": config}]
        ),
    )
    result = probe_executor(executor())
    assert result["available"] is False
    assert result["error"]


def test_windows_remains_fail_closed_even_with_matching_node(monkeypatch):
    monkeypatch.setattr(cli, "object_result", lambda *args: {"OSType": "windows"})
    result = probe_executor({**executor(), "platform": "windows"})
    assert result["available"] is False
    assert "监督身份" in result["error"]


def test_cleanup_checks_owner_and_active_verification_for_containers_and_volumes(monkeypatch):
    calls = []

    def labels(owner, verification):
        return {"io.arks.executor.owner": owner, "io.arks.executor.verification": verification}

    containers = {
        "old": labels("ours", "old-v"),
        "active": labels("ours", "active-v"),
        "other": labels("others", "old-v"),
    }
    volumes = {
        "old-vol": labels("ours", "old-v"),
        "active-vol": labels("ours", "active-v"),
        "other-vol": labels("others", "old-v"),
    }

    def call(settings, *args, **kwargs):
        calls.append(args)
        if args[0] == "ps":
            return b"old active other"
        if args[:2] == ("volume", "ls"):
            return b"old-vol active-vol other-vol"
        return b""

    def inspect(settings, *args):
        if args[0] == "inspect":
            return [{"Config": {"Labels": containers[args[-1]]}}]
        return [{"Labels": volumes[args[-1]]}]

    monkeypatch.setattr(runner, "call", call)
    monkeypatch.setattr(runner, "object_result", inspect)
    result = cleanup_orphans([executor()], "ours", ["active-v"])
    assert result == {"removed": 1, "volumes_removed": 1, "errors": []}
    assert ("rm", "--force", "--volumes", "old") in calls
    assert ("volume", "rm", "old-vol") in calls
    assert not any(
        "prune" in args or any("other" in str(part) for part in args)
        for args in calls
        if args[0] == "rm" or args[:2] == ("volume", "rm")
    )
