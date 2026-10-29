"""线程闸门确定复现启动与取消竞态，不执行外部命令或访问正式数据。"""

import asyncio
import copy
import threading
from types import SimpleNamespace

import pytest

from app.agents.tools import engineering


class GatedChanges:
    def __init__(self):
        self.lock = threading.RLock()
        self.start_entered = threading.Event()
        self.start_release = threading.Event()
        self.cancel_entered = threading.Event()
        self.cancel_release = threading.Event()
        self.cancel_release.set()
        self.wait_entered = asyncio.Event()
        self.wait_release = asyncio.Event()
        self.start_error = None
        self.cancel_error = None
        self.cancel_calls = 0
        self.current = {"status": "ready", "latest_verification": None}

    def verify(self, change_id, profile_id, purpose="change"):
        self.start_entered.set()
        if not self.start_release.wait(5):
            raise RuntimeError("测试未释放启动闸门")
        if self.start_error:
            raise self.start_error
        with self.lock:
            self.current = {
                "status": "verifying",
                "latest_verification": {
                    "id": "verification-1",
                    "status": "running",
                    "profile_id": profile_id,
                },
            }
            return copy.deepcopy(self.current)

    async def wait(self, change_id, timeout_seconds):
        self.wait_entered.set()
        await self.wait_release.wait()
        return self.get(change_id)

    def get(self, change_id):
        with self.lock:
            return copy.deepcopy(self.current)

    def cancel(self, change_id):
        self.cancel_entered.set()
        if not self.cancel_release.wait(5):
            raise RuntimeError("测试未释放取消闸门")
        if self.cancel_error:
            raise self.cancel_error
        self.cancel_calls += 1
        self.current["status"] = "failed"
        self.current["latest_verification"]["status"] = "cancelled"
        return self.get(change_id)


def verification_tool(changes):
    runtime = SimpleNamespace(
        repository=SimpleNamespace(project_id="isolated-project", creation_guard=lambda: None),
        project_lock=asyncio.Lock(),
        code_changes=changes,
    )
    return {tool.name: tool for tool in engineering.engineering_tools(runtime, "请修复代码并验证")}[
        "verify_code_change"
    ]


async def entered(event):
    assert await asyncio.wait_for(asyncio.to_thread(event.wait, 2), 3)


async def test_cancellation_during_launch_waits_then_cancels_created_verification():
    changes = GatedChanges()
    tool = verification_tool(changes)
    task = asyncio.create_task(tool.ainvoke({"change_id": "change", "profile_id": "profile"}))
    try:
        await entered(changes.start_entered)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        assert changes.cancel_calls == 0
        changes.start_release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 3)
        assert changes.cancel_calls == 1
        assert changes.current["latest_verification"]["status"] == "cancelled"
    finally:
        changes.start_release.set()
        changes.cancel_release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_repeated_cancellation_does_not_interrupt_launch_or_cancel_cleanup():
    changes = GatedChanges()
    changes.cancel_release.clear()
    task = asyncio.create_task(
        verification_tool(changes).ainvoke({"change_id": "change", "profile_id": "profile"})
    )
    try:
        await entered(changes.start_entered)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        changes.start_release.set()
        await entered(changes.cancel_entered)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        changes.cancel_release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 3)
        assert changes.cancel_calls == 1
        assert changes.current["latest_verification"]["status"] == "cancelled"
    finally:
        changes.start_release.set()
        changes.cancel_release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_cancellation_after_launch_does_not_cancel_a_newer_verification():
    changes = GatedChanges()
    changes.start_release.set()
    task = asyncio.create_task(
        verification_tool(changes).ainvoke({"change_id": "change", "profile_id": "profile"})
    )
    try:
        await asyncio.wait_for(changes.wait_entered.wait(), 3)
        with changes.lock:
            changes.current["latest_verification"]["id"] = "verification-2"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 3)
        assert changes.cancel_calls == 0
        assert changes.current["latest_verification"]["id"] == "verification-2"
    finally:
        changes.start_release.set()
        changes.wait_release.set()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("failure_phase", ["launch", "cancel"])
async def test_cancellation_does_not_hide_real_launch_or_cleanup_failures(failure_phase):
    changes = GatedChanges()
    if failure_phase == "launch":
        changes.start_error = ValueError("启动失败证据")
    else:
        changes.cancel_error = ValueError("取消失败证据")
    task = asyncio.create_task(
        verification_tool(changes).ainvoke({"change_id": "change", "profile_id": "profile"})
    )
    try:
        await entered(changes.start_entered)
        task.cancel()
        changes.start_release.set()
        result = await asyncio.wait_for(task, 3)
        assert ("启动失败证据" if failure_phase == "launch" else "取消失败证据") in result
    finally:
        changes.start_release.set()
        changes.cancel_release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_cancellation_timeout_keeps_cleanup_alive_until_late_launch_finishes(monkeypatch):
    monkeypatch.setattr(engineering, "VERIFICATION_CANCEL_TIMEOUT", 0.03)
    changes = GatedChanges()
    task = asyncio.create_task(
        verification_tool(changes).ainvoke({"change_id": "change", "profile_id": "profile"})
    )
    try:
        await entered(changes.start_entered)
        task.cancel()
        result = await asyncio.wait_for(task, 3)
        assert "后台取消清理尚未完成" in result
        assert engineering._verification_cleanups
        changes.start_release.set()
        await entered(changes.cancel_entered)
        await asyncio.gather(*list(engineering._verification_cleanups))
        assert changes.cancel_calls == 1
        assert changes.current["latest_verification"]["status"] == "cancelled"
    finally:
        changes.start_release.set()
        changes.cancel_release.set()
        if engineering._verification_cleanups:
            await asyncio.gather(*list(engineering._verification_cleanups), return_exceptions=True)
        await asyncio.gather(task, return_exceptions=True)
