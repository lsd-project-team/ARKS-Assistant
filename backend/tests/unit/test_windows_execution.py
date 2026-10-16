import base64
import copy
import json
import os
import subprocess
import sys
import time

import pytest

from app.infrastructure.execution import sandbox_evidence_valid, windows, windows_capacity
from app.infrastructure.execution.cli import ExecutionError, options
from app.infrastructure.execution.windows_bridge import run_bridge
from app.modules.code_changes.processes import VerificationTask


def executor():
    return {
        "kind": "container",
        "platform": "windows",
        "image": "sha256:" + "a" * 64,
        "context": "win-builder",
        "owner_id": "service-owner",
    }


@pytest.mark.parametrize(
    "endpoint",
    [
        "tcp://host:2376",
        "ssh://bad;command",
        "ssh://a@-host",
        "ssh://name:password@host",
        "ssh://host/path",
        "ssh://host?command=bad",
        "ssh://host:99999",
        "ssh://a%20name@host",
        "ssh://host#fragment",
    ],
)
def test_capacity_probe_rejects_untrusted_remote_shell_endpoint(endpoint):
    with pytest.raises(ExecutionError):
        windows_capacity.probe_arguments(endpoint, "C:\\ProgramData\\docker")


@pytest.mark.parametrize(
    "root",
    [
        "\\\\server\\share",
        "/var/lib/docker",
        "C:\\..\\Windows",
        "C:\\Docker';exit 0;#",
        "C:\\Docker:stream",
        None,
    ],
)
def test_capacity_probe_rejects_nonlocal_or_injectable_root(root):
    with pytest.raises(ExecutionError):
        windows_capacity.encoded_probe(root)


def test_ssh_capacity_probe_is_fixed_encoded_readonly_code(monkeypatch):
    monkeypatch.setattr(windows_capacity.shutil, "which", lambda value: "/usr/bin/ssh")
    arguments = windows_capacity.probe_arguments(
        "ssh://builder@win.example:2222", "D:\\docker data"
    )
    assert arguments[:2] == ["/usr/bin/ssh", "-T"]
    assert "BatchMode=yes" in arguments
    assert "StrictHostKeyChecking=yes" in arguments
    assert "builder@win.example" in arguments
    assert arguments[-2] == "-EncodedCommand"
    script = base64.b64decode(arguments[-1]).decode("utf-16-le")
    assert "GetDiskFreeSpaceEx" in script
    assert "D:\\docker data" not in script
    assert "ROOT_BASE64" not in script
    assert not {"-i", "StrictHostKeyChecking=no", "UserKnownHostsFile=/dev/null"}.intersection(
        arguments
    )


@pytest.mark.parametrize(
    "change",
    [
        {"measured_at": 879},
        {"measured_at": 1031},
        {"free_bytes": True},
        {"free_bytes": 101},
        {"total_bytes": -1},
        {"probe_version": 2},
    ],
)
def test_capacity_receipt_rejects_stale_or_malformed_values(change):
    payload = {"probe_version": 1, "free_bytes": 50, "total_bytes": 100, "measured_at": 1000}
    with pytest.raises(ExecutionError):
        windows_capacity.validate_capacity({**payload, **change}, now=1000)


def test_scratch_and_node_free_limits_have_exact_boundaries():
    reserved = windows_capacity.scratch_budget({"windows_scratch_mb": 20480})
    assert reserved == 20480 * 1024 * 1024
    windows_capacity.admit_capacity({"free_bytes": reserved + 1073741824}, reserved)
    with pytest.raises(ExecutionError):
        windows_capacity.admit_capacity({"free_bytes": reserved + 1073741823}, reserved)
    with pytest.raises(ExecutionError):
        windows_capacity.scratch_budget({"windows_scratch_mb": 20479})


def test_observed_guest_capacity_cannot_exceed_declared_budget():
    report = {
        "protocol": 3,
        "phase": "prepared",
        "supervisor": "ContainerAdministrator",
        "capacity_bytes": 100,
        "available_bytes": 50,
    }
    windows.validate_ready(report, 100)
    with pytest.raises(ExecutionError, match="超过声明"):
        windows.validate_ready(report, 99)
    with pytest.raises(ExecutionError):
        windows.validate_ready({**report, "capacity_bytes": True}, 100)


def test_stop_is_confirmed_and_unknown_state_fails_closed(monkeypatch):
    states = iter([{"State": {"Running": True}}, {"State": {"Running": False}}])
    calls = []
    monkeypatch.setattr(windows, "object_result", lambda *args: [next(states)])
    monkeypatch.setattr(windows, "call", lambda *args: calls.append(args[1:]))
    windows.ensure_stopped(executor(), "container")
    assert calls == [("kill", "container")]
    monkeypatch.setattr(windows, "object_result", lambda *args: [{"State": {}}])
    with pytest.raises(ExecutionError, match="无法确认"):
        windows.ensure_stopped(executor(), "container")


def test_other_service_capacity_reservation_requires_dedicated_node(monkeypatch):
    reserved = 32768 * 1024 * 1024
    monkeypatch.setattr(
        windows, "admit_windows_node", lambda *args: ({"free_bytes": reserved * 2}, reserved)
    )
    calls = []

    def call(*args):
        calls.append(args[1:])
        return b"existing-container\n"

    monkeypatch.setattr(windows, "call", call)
    monkeypatch.setattr(
        windows,
        "object_result",
        lambda *args: [
            {
                "Config": {"Labels": {"io.arks.executor.owner": "other-service"}},
                "HostConfig": {"StorageOpt": {"size": str(reserved)}},
            }
        ],
    )
    with pytest.raises(ExecutionError, match="其他服务"):
        windows.create_reserved(executor(), None, {}, {}, 90)
    assert calls == [("ps", "-aq", "--filter", "label=io.arks.executor.owner")]


def test_cancelled_bridge_does_not_start_process(tmp_path, monkeypatch):
    from app.infrastructure.execution import windows_bridge

    task = VerificationTask("project", "change", "verification")
    task.cancel.set()

    def forbidden(*args, **kwargs):
        raise AssertionError("取消后不能再启动桥接进程")

    monkeypatch.setattr(windows_bridge.subprocess, "Popen", forbidden)
    assert run_bridge(task, ["must-not-run"], tmp_path / "none.log", 1, 4096) == (
        "cancelled",
        None,
        "",
    )


def test_fake_passed_stdout_cannot_override_exec_exitcode(tmp_path):
    task = VerificationTask("project", "change", "verification")
    log = tmp_path / "exec.log"
    frames = json.dumps({"type": "output", "data": base64.b64encode(b"passed").decode()}) + "\n"
    frames += json.dumps({"type": "result", "raw_exit_code": 256}) + "\n"
    command = [sys.executable, "-c", "import sys;sys.stdout.write(" + repr(frames) + ")"]
    assert run_bridge(task, command, log, 5, 4096) == ("failed", 256, "")
    assert log.read_text().strip() == "passed"


def good_evidence():
    reserved = 32768 * 1024 * 1024
    return {
        "image_id": executor()["image"],
        "configured_image": executor()["image"],
        "configured_context": "win-builder",
        "platform": "windows",
        "protocol": 3,
        "isolated": True,
        "isolation": "hyperv",
        "proof_kind": "engine_exec_exit",
        "container_stopped": True,
        "node_id": "b" * 64,
        "admitted_at": 1000,
        "scratch_reserved_bytes": reserved,
        "observed_capacity_bytes": reserved,
        "guest_available_bytes": 1073741824,
        "raw_exit_code": 0,
        "node_capacity": {
            "probe_version": 1,
            "free_bytes": reserved * 2,
            "total_bytes": reserved * 3,
            "measured_at": 1000,
        },
    }


@pytest.mark.parametrize(
    "change",
    [
        {"protocol": 2},
        {"proof_kind": "file"},
        {"container_stopped": False},
        {"isolation": "process"},
        {"node_id": ""},
        {"configured_context": "other"},
        {"configured_image": "sha256:" + "c" * 64},
        {"image_id": "sha256:" + "c" * 64},
        {"guest_available_bytes": True},
        {"observed_capacity_bytes": 999999999999},
        {"admitted_at": 10000},
        {"raw_exit_code": 256},
        {"raw_exit_code": True},
    ],
)
def test_windows_evidence_rejects_incomplete_or_unbound_proof(change):
    evidence = good_evidence()
    assert sandbox_evidence_valid(evidence, executor())
    assert not sandbox_evidence_valid({**evidence, **change}, executor())


def test_windows_evidence_rejects_omitted_node_and_false_capacity():
    evidence = good_evidence()
    without = copy.deepcopy(evidence)
    without.pop("node_capacity")
    assert not sandbox_evidence_valid(without, executor())
    evidence["node_capacity"]["free_bytes"] = 1
    assert not sandbox_evidence_valid(evidence, executor())
    assert not sandbox_evidence_valid({"protocol": 3, "isolated": True}, executor())


def test_linux_protocol2_existing_fixed_image_proof_remains_valid():
    configuration = {**executor(), "platform": "linux"}
    evidence = {
        "protocol": 2,
        "platform": "linux",
        "image_id": configuration["image"],
        "isolated": True,
    }
    assert sandbox_evidence_valid(evidence, configuration)
    assert not sandbox_evidence_valid(evidence, {**configuration, "image": "sha256:" + "c" * 64})


@pytest.mark.skipif(os.name != "nt", reason="本子组件需Windows PowerShell，只读容量，不是容器验收")
def test_real_local_windows_disk_probe_reads_capacity_without_docker():
    root = os.environ.get("SystemRoot", "C:\\Windows")
    arguments = windows_capacity.probe_arguments("npipe:////./pipe/docker_engine", root)
    result = subprocess.run(arguments, capture_output=True, timeout=20, **options())
    assert result.returncode == 0
    receipt = windows_capacity.validate_capacity(json.loads(result.stdout.decode("utf-8-sig")))
    assert receipt["total_bytes"] >= receipt["free_bytes"] > 0
    assert abs(receipt["measured_at"] - time.time()) < 30
