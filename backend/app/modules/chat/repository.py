"""原始对话和可重放事件存储；图检查点不替代原始记录。"""

from threading import RLock

from sqlalchemy import func, select, update

from app.core.config import dump_json
from app.core.identifiers import now_iso
from app.infrastructure.database.serialization import record_dict
from app.infrastructure.database.session import Database
from app.modules.admin.identity import question_actor
from app.modules.auth.ownership import current_owner
from app.modules.chat.branches import ConversationBranches
from app.modules.chat.catalog import ConversationCatalog, title_from_question
from app.modules.chat.history import ConversationHistory
from app.modules.chat.models import Message, QueuedQuestion, Run, RunEvent, Thread
from app.modules.chat.queue import ConversationQueue
from app.modules.projects.source_preferences import SourcePreferences

TERMINAL = {"completed", "failed", "cancelled", "interrupted"}


class Repository:
    def __init__(
        self, database: Database, workspace_id: str, *, project_id=None, source_workspace_id=""
    ):
        self.database = database
        self.workspace_id = workspace_id
        self.project_id = project_id
        self.source_workspace_id = (
            workspace_id if source_workspace_id == "" else source_workspace_id
        )
        self.creation_guard = lambda: None
        self.source_workspace_ids = {self.source_workspace_id}
        self.source_preferences = SourcePreferences(database, workspace_id)
        self.lock = RLock()
        self.catalog = ConversationCatalog(database, workspace_id)
        self.history = ConversationHistory(database, self.catalog)
        self.branches = ConversationBranches(self)
        self.queue = ConversationQueue(self)

    def threads(self, state="active", query="", limit=100, offset=0) -> list[dict]:
        return self.catalog.list(state, query, limit, offset)

    def create_thread(self, title: str) -> dict:
        self.creation_guard()
        with self.database.session.begin() as session:
            row = Thread(
                owner_id=current_owner(),
                title=title,
                workspace_id=self.workspace_id,
                project_id=self.project_id,
                auto_title=title == "新对话",
            )
            session.add(row)
            session.flush()
            return record_dict(row)

    def thread(self, thread_id: str, limit: int | None = None, before=None, around=None) -> dict:
        page = self.history.page(thread_id, limit, before, around) if limit else None
        with self.database.session() as session:
            row = self.catalog.row(session, thread_id)
            result = record_dict(row)
            result["editable_message_id"] = session.scalar(
                select(Message.id)
                .where(
                    Message.thread_id == thread_id, Message.role == "user", Message.context_active
                )
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(1)
            )
            if page:
                result.update(page)
                identifiers = [row["id"] for row in page["messages"]]
                latest = (
                    select(Run.id)
                    .where(Run.thread_id == thread_id)
                    .order_by(Run.created_at.desc())
                    .limit(1)
                    .scalar_subquery()
                )
                run_filter = (
                    Run.message_id.in_(identifiers)
                    | Run.response_message_id.in_(identifiers)
                    | (Run.id == latest)
                )
            else:
                messages = session.scalars(
                    select(Message)
                    .where(Message.thread_id == thread_id)
                    .order_by(Message.created_at, Message.id)
                )
                result["messages"] = [record_dict(message) for message in messages]
                run_filter = True
            runs = session.scalars(
                select(Run).where(Run.thread_id == thread_id, run_filter).order_by(Run.created_at)
            )
            result["runs"] = [record_dict(run) for run in runs]
            return result

    def rename(self, thread_id: str, title: str):
        self.catalog.get(thread_id)
        with self.database.session.begin() as session:
            session.execute(
                update(Thread)
                .where(Thread.id == thread_id)
                .values(title=title, auto_title=False, updated_at=now_iso())
            )

    def record_model(self, run_id, snapshot):
        with self.database.session.begin() as session:
            session.get(Run, run_id).model_snapshot_json = dump_json(snapshot)

    def create_run(
        self, thread_id: str | None, content: str, selections: list[dict], source_options=None
    ) -> dict:
        if thread_id:
            self.catalog.get(thread_id)
        with self.lock, self.database.session.begin() as session:
            if not thread_id:
                # 首次发送与会话创建在同一事务内，失败不会留下空会话。
                new_thread = Thread(
                    title="新对话",
                    workspace_id=self.workspace_id,
                    project_id=self.project_id,
                    owner_id=current_owner(),
                )
                session.add(new_thread)
                session.flush()
                thread_id = new_thread.id
            return self.add_run(session, thread_id, content, selections, source_options)

    @staticmethod
    def ensure_idle(session, thread_id):
        if session.scalar(
            select(Run.id).where(Run.thread_id == thread_id, Run.status.in_(["queued", "running"]))
        ):
            raise ValueError("此对话正在回复，请先停止或等待完成")

    def add_run(self, session, thread_id, content, selections, source_options=None, actor=None):
        self.creation_guard()
        self.ensure_idle(session, thread_id)
        if source_options is None:
            source_options = self.source_preferences.read(session)["source_options"]
        thread = self.catalog.row(session, thread_id)
        if (
            thread.auto_title
            and thread.title == "新对话"
            and not session.scalar(
                select(Message.id).where(Message.thread_id == thread_id).limit(1)
            )
        ):
            thread.title = title_from_question(content, selections)
        thread.state, thread.updated_at = "active", now_iso()
        message = Message(
            thread_id=thread_id,
            role="user",
            content=content,
            selections_json=dump_json(selections),
            source_options_json=dump_json(source_options or {}),
            source_workspace_id=self.source_workspace_id,
            **(actor if actor is not None else question_actor()),
        )
        session.add(message)
        session.flush()
        run = Run(thread_id=thread_id, message_id=message.id)
        session.add(run)
        session.flush()
        return record_dict(run)

    def run(self, run_id: str) -> dict:
        with self.database.session() as session:
            row = session.get(Run, run_id)
            if not row:
                raise FileNotFoundError("运行不存在")
            result = record_dict(row)
        self.catalog.get(result["thread_id"])
        return result

    def message(self, message_id: str) -> dict:
        with self.database.session() as session:
            row = session.get(Message, message_id)
            if not row:
                raise FileNotFoundError("消息不存在")
            self.catalog.row(session, row.thread_id)
            return record_dict(row)

    def set_status(self, run_id: str, status: str, error: str = "", error_code: str = ""):
        with self.database.session.begin() as session:
            values = {
                "status": status,
                "error": error,
                "error_code": error_code,
                "updated_at": now_iso(),
            }
            if status == "running":
                values["started_at"] = now_iso()
            elif status in TERMINAL:
                values.update(finished_at=now_iso(), stage=status)
            session.execute(update(Run).where(Run.id == run_id).values(**values))

    def event(self, run_id: str, kind: str, payload: dict) -> dict:
        # 序号分配与插入必须在同一把锁和事务内，重连才能可靠去重。
        with self.lock, self.database.session.begin() as session:
            sequence = (
                session.scalar(select(func.max(RunEvent.sequence)).where(RunEvent.run_id == run_id))
                or 0
            ) + 1
            event = RunEvent(
                run_id=run_id, sequence=sequence, kind=kind, payload_json=dump_json(payload)
            )
            session.add(event)
            if kind == "token":
                run = session.get(Run, run_id)
                run.answer += payload["text"]
            elif kind == "answer_replace":
                session.get(Run, run_id).answer = payload["text"]
            elif kind == "stage":
                session.get(Run, run_id).stage = payload["stage"]
            session.flush()
            return record_dict(event)

    def events(self, run_id: str, after: int = 0) -> list[dict]:
        self.run(run_id)
        with self.database.session() as session:
            rows = session.scalars(
                select(RunEvent)
                .where(RunEvent.run_id == run_id, RunEvent.sequence > after)
                .order_by(RunEvent.sequence)
                .limit(500)
            )
            return [record_dict(row) for row in rows]

    def latest_event(self, thread_id: str, kind: str) -> dict | None:
        self.catalog.get(thread_id)
        with self.database.session() as session:
            event = session.scalar(
                select(RunEvent)
                .join(Run, Run.id == RunEvent.run_id)
                .where(Run.thread_id == thread_id, RunEvent.kind == kind)
                .order_by(Run.created_at.desc(), RunEvent.sequence.desc())
                .limit(1)
            )
            return record_dict(event)["payload"] if event else None

    def run_event(self, run_id: str, kind: str) -> dict | None:
        self.run(run_id)
        with self.database.session() as session:
            event = session.scalar(
                select(RunEvent)
                .where(RunEvent.run_id == run_id, RunEvent.kind == kind)
                .order_by(RunEvent.sequence.desc())
                .limit(1)
            )
            return record_dict(event)["payload"] if event else None

    def finish(self, run_id: str, answer: str, completion=None):
        with self.database.session.begin() as session:
            run = session.get(Run, run_id)
            if run.status == "completed":
                return
            run.status = "completed"
            run.answer = answer
            run.updated_at = now_iso()
            run.finished_at, run.stage = now_iso(), (completion or {}).get("stage", "completed")
            response = Message(
                thread_id=run.thread_id,
                role="assistant",
                content=answer,
                source_workspace_id=self.source_workspace_id,
            )
            session.add(response)
            session.flush()
            run.response_message_id = response.id
            # 同一问题的恢复、重生成共用提交键，不将内部调用计为新任务。
            from app.modules.admin.tracking import record_answer_submission

            record_answer_submission(session, session.get(Message, run.message_id))
            session.execute(
                update(Thread).where(Thread.id == run.thread_id).values(updated_at=now_iso())
            )

    def recover(self):
        with self.database.session.begin() as session:
            identifiers = list(
                session.scalars(select(Run.thread_id).where(Run.status.in_(["queued", "running"])))
            )
            # 服务恰好在完成回复和出队之间退出时，待发问题也需要显式恢复。
            identifiers.extend(session.scalars(select(QueuedQuestion.thread_id)))
            session.execute(
                update(Thread).where(Thread.id.in_(identifiers)).values(queue_paused=True)
            )
            session.execute(
                update(Run)
                .where(Run.status.in_(["queued", "running"]))
                .values(
                    status="interrupted",
                    stage="interrupted",
                    finished_at=now_iso(),
                    error_code="interrupted",
                    error="服务重启中断，可继续运行",
                )
            )

    def resume(self, run_id: str):
        self.creation_guard()
        previous = self.run(run_id)
        self.ensure_source_compatible(previous["message_id"])
        if previous["status"] not in {"interrupted", "failed", "cancelled"}:
            raise ValueError("此运行不能继续")
        source = previous
        # 兼容旧版本的恢复记录：重新生成与旧回复的关联沿恢复链查找。
        while source.get("resumed_from") and not source.get("regenerated_from"):
            source = self.run(source["resumed_from"])
        with self.lock, self.database.session.begin() as session:
            latest = session.scalar(
                select(Run.id)
                .where(Run.thread_id == previous["thread_id"])
                .order_by(Run.created_at.desc())
                .limit(1)
            )
            # 检查点属于整条会话，旧运行不能在更新后的图状态上恢复。
            if latest != run_id:
                raise ValueError("只能继续当前对话最近一次运行")
            active = session.scalar(
                select(Run.id).where(
                    Run.thread_id == previous["thread_id"], Run.status.in_(["queued", "running"])
                )
            )
            if active:
                raise ValueError("此对话正在运行")
            row = Run(
                thread_id=previous["thread_id"],
                message_id=previous["message_id"],
                resumed_from=run_id,
                regenerated_from=source.get("regenerated_from"),
                reset_context=source.get("reset_context", False),
            )
            session.add(row)
            session.flush()
            return record_dict(row)

    def has_active_run(self, thread_id: str) -> bool:
        self.catalog.get(thread_id)
        with self.database.session() as session:
            return bool(
                session.scalar(
                    select(Run.id)
                    .where(Run.thread_id == thread_id, Run.status.in_(["queued", "running"]))
                    .limit(1)
                )
            )

    def active_runs(self, thread_id: str) -> list[str]:
        self.catalog.get(thread_id, include_deleted=True)
        with self.database.session() as session:
            return list(
                session.scalars(
                    select(Run.id).where(
                        Run.thread_id == thread_id, Run.status.in_(["queued", "running"])
                    )
                )
            )

    def regenerate(self, run_id: str) -> dict:
        self.creation_guard()
        previous = self.run(run_id)
        self.ensure_source_compatible(previous["message_id"])
        with self.lock, self.database.session.begin() as session:
            latest = session.scalar(
                select(Run)
                .where(Run.thread_id == previous["thread_id"])
                .order_by(Run.created_at.desc())
                .limit(1)
            )
            if not latest or latest.id != run_id or latest.status != "completed":
                raise ValueError("只能重新生成当前对话最近完成的回复")
            run = Run(
                thread_id=previous["thread_id"],
                message_id=previous["message_id"],
                regenerated_from=run_id,
            )
            session.add(run)
            session.flush()
            return record_dict(run)

    def ensure_source_compatible(self, message_id):
        message = self.message(message_id)
        source_id = message.get("source_workspace_id")
        if source_id and source_id != self.source_workspace_id:
            raise ValueError("此问题来自其他源码目录，请在当前项目重新提问；原问题和答案仍保留")
        if any(
            item.get("source_workspace_id")
            and item["source_workspace_id"] not in self.source_workspace_ids
            for item in message.get("selections", [])
        ):
            raise ValueError("原问题的源码目录已解除关联，请重新提问；历史引用仍保留")
