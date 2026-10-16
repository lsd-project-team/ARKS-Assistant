"""运行生命周期独立于 SSE 连接，客户端断线不取消模型任务。"""

import asyncio

from app.agents.analysis.policy import configured_analysis
from app.agents.runtime.configuration import bind_configuration, model_snapshot
from app.agents.runtime.engine import AgentRuntime
from app.agents.runtime.feedback import error_feedback
from app.core.config import SettingsStore, dump_json
from app.modules.auth.context import request_identity
from app.modules.chat.models import Run
from app.modules.chat.repository import TERMINAL, Repository
from app.modules.projects.context import bind_project


class RunManager:
    def __init__(self, repository: Repository, runtime: AgentRuntime, settings: SettingsStore):
        self.repository, self.runtime, self.settings = repository, runtime, settings
        self.tasks: dict[str, asyncio.Task] = {}
        self.capacity = asyncio.Semaphore(3)
        # 检查点纠错与新运行入队互斥，避免读完摘要后又被另一次执行覆盖。
        self.edit_lock = asyncio.Lock()
        self.closing = False
        self.project_snapshot = lambda: {}

    def start(self, run: dict):
        project = self.project_snapshot()
        message = self.repository.message(run["message_id"])
        current = request_identity.get()
        actor = (
            current["user"]
            if current and (run.get("resumed_from") or run.get("regenerated_from"))
            else message.get("actor", {})
        )
        # 排队出队可能发生在另一个人的任务中，不能继承那个后台任务的个人记忆。
        project = {
            **project,
            "_execution_user": actor if actor.get("id") else None,
        }
        with self.repository.database.session.begin() as session:
            session.get(Run, run["id"]).project_snapshot_json = dump_json(project)
        run["project_snapshot"] = project
        configuration = self.settings.load()
        if project:
            configuration = configuration.model_copy(
                update={"deepwiki_repo": project.get("deepwiki_repo", "")}
            )
        configuration, _policy = configured_analysis(
            configuration,
            self.repository.message(run["message_id"])["content"],
            self.repository.latest_event(run["thread_id"], "analysis_plan"),
        )
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
        actor = run.get("project_snapshot", {}).get("_execution_user")
        token = request_identity.set({"user": actor} if actor else None)
        try:
            with bind_configuration(configuration), bind_project(run.get("project_snapshot", {})):
                await self._execute(run, configuration)
        finally:
            request_identity.reset(token)

    async def _execute(self, run: dict, configuration):
        def emit(kind, payload):
            return self.repository.event(run["id"], kind, payload)

        completed = False
        try:
            async with self.capacity:
                self.repository.set_status(run["id"], "running")
                emit("status", {"status": "running"})
                answer = await self.runtime.execute(run, emit)
                completion = self.repository.run_event(run["id"], "run_completion")
                self.repository.finish(run["id"], answer, completion)
                emit(
                    "done",
                    {
                        "status": "completed",
                        "answer": answer,
                        "finished_at": self.repository.run(run["id"])["finished_at"],
                        "stage": (completion or {}).get("stage", "completed"),
                        "completion": completion,
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
