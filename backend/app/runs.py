"""运行生命周期独立于 SSE 连接，客户端断线不取消模型任务。"""

import asyncio

from app.config import SettingsStore
from app.repository import TERMINAL, Repository
from app.run_configuration import bind_configuration, model_snapshot
from app.run_feedback import error_feedback
from app.runtime import AgentRuntime


class RunManager:
    def __init__(self, repository: Repository, runtime: AgentRuntime, settings: SettingsStore):
        self.repository, self.runtime, self.settings = repository, runtime, settings
        self.tasks: dict[str, asyncio.Task] = {}
        self.capacity = asyncio.Semaphore(3)
        # 检查点纠错与新运行入队互斥，避免读完摘要后又被另一次执行覆盖。
        self.edit_lock = asyncio.Lock()
        self.closing = False

    def start(self, run: dict):
        configuration = self.settings.load()
        snapshot = model_snapshot(configuration)
        self.repository.record_model(run["id"], snapshot)
        run["model_snapshot"] = snapshot
        self.repository.event(run["id"], "stage", {"stage": "queued"})
        task = asyncio.create_task(
            self._execute_bound(run, configuration), name=f"agent:{run['id']}"
        )
        self.tasks[run["id"]] = task
        task.add_done_callback(lambda _task: self.tasks.pop(run["id"], None))

    async def _execute_bound(self, run, configuration):
        with bind_configuration(configuration):
            await self._execute(run, configuration)

    async def _execute(self, run: dict, configuration):
        def emit(kind, payload):
            return self.repository.event(run["id"], kind, payload)

        completed = False
        try:
            async with self.capacity:
                self.repository.set_status(run["id"], "running")
                emit("status", {"status": "running"})
                answer = await self.runtime.execute(run, emit)
                self.repository.finish(run["id"], answer)
                emit(
                    "done",
                    {
                        "status": "completed",
                        "answer": answer,
                        "finished_at": self.repository.run(run["id"])["finished_at"],
                    },
                )
                completed = True
        except asyncio.CancelledError:
            self.repository.set_status(run["id"], "cancelled")
            self.repository.queue.pause(run["thread_id"])
            emit("done", {"status": "cancelled"})
        except Exception as error:
            feedback = error_feedback(error, configuration.model)
            self.repository.set_status(run["id"], "failed", feedback["text"], feedback["code"])
            self.repository.queue.pause(run["thread_id"])
            emit("error", feedback)
            emit("done", {"status": "failed"})
        if completed and not self.closing:
            async with self.edit_lock:
                try:
                    next_run = self.repository.queue.dispatch(run["thread_id"])
                except FileNotFoundError:
                    # 完成事件发出后，对话可能已在另一请求中被彻底删除。
                    return
                if next_run:
                    self.start(next_run)

    async def cancel(self, run_id: str):
        run = self.repository.run(run_id)
        self.repository.queue.pause(run["thread_id"])
        task = self.tasks.get(run_id)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            # 任务可能在首次进入协程前就被取消，此时协程内的异常处理不会执行。
            if self.repository.run(run_id)["status"] in {"queued", "running"}:
                self.repository.set_status(run_id, "cancelled")
                self.repository.event(run_id, "done", {"status": "cancelled"})

    async def shutdown(self):
        self.closing = True
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
