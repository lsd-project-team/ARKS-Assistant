"""构建失败、缺失自检结果及实际进程取消不能被旧日志掩盖。"""

import asyncio
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

from app.agents.tools.code_work import code_work_tools
from app.modules.code_work.files import PROJECT
from app.modules.code_work.runner import execute
from tests.helpers.code_work import make_work


@pytest.mark.parametrize("failure", ["driver-report", "compile", "simulation-report"])
async def test_failed_or_unreported_checks_do_not_reuse_old_success(
    services, tmp_path, monkeypatch, failure
):
    service, thread, _ = make_work(services, tmp_path)
    monkeypatch.setattr(service.environment, "compiler", lambda: "fake-msbuild.exe")
    old = service.folder(thread) / "checks/0123456789/Simulation"
    old.mkdir(parents=True)
    (old / "original-simulation-checks.txt").write_text(
        "PASS: 69 original-project integration checks.", encoding="utf-8"
    )
    calls = []

    def run(arguments, cwd, log, stop, deadline):
        calls.append(arguments)
        log.write_text("build output", encoding="utf-8")
        if str(arguments[0]).endswith("VirtualMotionDrivers.Tests.exe"):
            if failure != "driver-report":
                log.write_text("PASS: 16 virtual driver checks", encoding="utf-8")
        if "/p:Configuration=Simulation" in arguments:
            if failure == "compile":
                log.write_text("Example.cs(3): error CS1002", encoding="utf-8")
                return 1
            output = Path(next(x.split("=", 1)[1] for x in arguments if x.startswith("/p:OutDir=")))
            output.mkdir(parents=True)
            (output / f"{PROJECT}.exe").write_bytes(b"fresh-build")
        return 0

    monkeypatch.setattr("app.modules.code_work.runner.execute", run)
    await service.verify(thread)
    await service.tasks[thread]
    verification = service.status(thread)["verification"]
    assert verification["status"] == "failed"
    assert verification["steps"][-1]["status"] == "failed"
    ran_simulation = any("--simulation-self-test" in arguments for arguments in calls)
    assert ran_simulation == (failure == "simulation-report")
    if failure == "compile":
        assert "CS1002" in verification["steps"][-1]["log"]


async def test_changed_harness_is_rejected_before_any_command(services, tmp_path, monkeypatch):
    service, thread, _ = make_work(services, tmp_path)
    monkeypatch.setattr(service.environment, "compiler", lambda: "fake-msbuild.exe")
    calls = []
    monkeypatch.setattr("app.modules.code_work.runner.execute", lambda *args: calls.append(args))
    (service.folder(thread) / "source" / PROJECT / "App.config").write_text("changed")
    await service.verify(thread)
    await service.tasks[thread]
    job = service.status(thread)["verification"]
    assert job["status"] == "failed" and "配置已变化" in job["error"]
    assert calls == []


async def test_agent_does_not_restart_verification_after_user_stops_it(
    services, tmp_path, monkeypatch
):
    service, thread, _ = make_work(services, tmp_path)
    monkeypatch.setattr(service.environment, "compiler", lambda: "fake-msbuild.exe")
    started = Event()

    def run(arguments, cwd, log, stop, deadline):
        started.set()
        stop.wait(3)
        raise InterruptedError("验证已停止")

    monkeypatch.setattr("app.modules.code_work.runner.execute", run)
    tool = next(
        item
        for item in code_work_tools(service, thread, lambda *_: None)
        if item.name == "verify_code_workspace"
    )
    task = asyncio.create_task(tool.ainvoke({}))
    assert await asyncio.to_thread(started.wait, 2)
    service.cancel(thread)
    first = json.loads(await task)
    assert first["verification"]["status"] == "cancelled"
    job = first["verification"]["id"]
    result = await tool.ainvoke({})
    assert "已被停止" in result
    assert service.status(thread)["verification"]["id"] == job


@pytest.mark.skipif(os.name != "nt", reason="Windows taskkill 进程树行为")
@pytest.mark.parametrize("reason", ["cancel", "timeout"])
def test_cancel_or_timeout_terminates_owned_process_tree(tmp_path, reason):
    log = tmp_path / "process.log"
    stop = Event()
    code = (
        "import subprocess,sys,time;"
        "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
        "print(child.pid,flush=True);time.sleep(30)"
    )
    deadline = time.monotonic() + (0.8 if reason == "timeout" else 10)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(execute, [sys.executable, "-c", code], tmp_path, log, stop, deadline)
        started_deadline = time.monotonic() + 5
        while not log.exists() or not log.read_bytes().strip():
            assert time.monotonic() < started_deadline, "测试子进程未启动"
            time.sleep(0.02)
        child = int(log.read_text(encoding="utf-8").strip())
        if reason == "cancel":
            stop.set()
        with pytest.raises(InterruptedError if reason == "cancel" else TimeoutError):
            future.result(timeout=5)
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {child}", "/FO", "CSV", "/NH"],
        capture_output=True,
        timeout=5,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    assert f'"{child}"'.encode() not in result.stdout
