"""运行生命周期独立于 SSE 连接，客户端断线不取消模型任务。"""

import asyncio

from app.config import SettingsStore
from app.provider import safe_error
from app.repository import TERMINAL, Repository
from app.runtime import AgentRuntime


class RunManager:
    def __init__(self, repository: Repository, runtime: AgentRuntime, settings: SettingsStore):
        self.repository, self.runtime, self.settings = repository, runtime, settings
        self.tasks: dict[str, asyncio.Task] = {}
        self.capacity = asyncio.Semaphore(3)
        # 检查点纠错与新运行入队互斥，避免读完摘要后又被另一次执行覆盖。
        self.edit_lock = asyncio.Lock()

    def start(self, run: dict):
        task = asyncio.create_task(self._execute(run), name=f"agent:{run['id']}")
        self.tasks[run["id"]] = task
        task.add_done_callback(lambda _task: self.tasks.pop(run["id"], None))

    async def _execute(self, run: dict):
        def emit(kind, payload):
            return self.repository.event(run["id"], kind, payload)

        try:
            async with self.capacity:
                self.repository.set_status(run["id"], "running")
                emit("status", {"status": "running"})
                answer = await self.runtime.execute(run, emit)
                self.repository.finish(run["id"], answer)
                emit("done", {"status": "completed", "answer": answer})
        except asyncio.CancelledError:
            self.repository.set_status(run["id"], "cancelled")
            emit("done", {"status": "cancelled"})
        except Exception as error:
            message = safe_error(error, self.settings.load().model)
            self.repository.set_status(run["id"], "failed", message)
            emit("error", {"text": message})
            emit("done", {"status": "failed"})

    async def cancel(self, run_id: str):
        self.repository.run(run_id)
        task = self.tasks.get(run_id)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            # 任务可能在首次进入协程前就被取消，此时协程内的异常处理不会执行。
            if self.repository.run(run_id)["status"] in {"queued", "running"}:
                self.repository.set_status(run_id, "cancelled")
                self.repository.event(run_id, "done", {"status": "cancelled"})

    async def shutdown(self):
        active = list(self.tasks.values())
        for task in active:
            task.cancel()
        await asyncio.gather(*active, return_exceptions=True)

    async def stream(self, run_id: str, after: int):
        cursor = after
        while True:
            events = self.repository.events(run_id, cursor)
            for event in events:
                cursor = event["sequence"]
                yield event
            if not events and self.repository.run(run_id)["status"] in TERMINAL:
                return
            await asyncio.sleep(0.2)
