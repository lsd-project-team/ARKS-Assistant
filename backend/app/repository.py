"""原始对话和可重放事件存储；图检查点不替代原始记录。"""

import json
from threading import RLock

from sqlalchemy import func, select, update

from app.config import dump_json
from app.database import Database
from app.models import Message, Run, RunEvent, Thread, now_iso

TERMINAL = {"completed", "failed", "cancelled", "interrupted"}


def record_dict(record) -> dict:
    result = {column.name: getattr(record, column.name) for column in record.__table__.columns}
    for field in ("selections_json", "payload_json"):
        if field in result:
            result[field.removesuffix("_json")] = json.loads(result.pop(field))
    return result


class Repository:
    def __init__(self, database: Database, workspace_id: str):
        self.database = database
        self.workspace_id = workspace_id
        self.lock = RLock()

    def threads(self) -> list[dict]:
        with self.database.session() as session:
            rows = session.scalars(
                select(Thread)
                .where(Thread.workspace_id == self.workspace_id)
                .order_by(Thread.updated_at.desc())
            )
            return [record_dict(row) for row in rows]

    def create_thread(self, title: str) -> dict:
        with self.database.session.begin() as session:
            row = Thread(title=title, workspace_id=self.workspace_id)
            session.add(row)
            session.flush()
            return record_dict(row)

    def thread(self, thread_id: str) -> dict:
        with self.database.session() as session:
            row = session.get(Thread, thread_id)
            if not row or row.workspace_id != self.workspace_id:
                raise FileNotFoundError("对话不存在")
            result = record_dict(row)
            messages = session.scalars(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at, Message.id)
            )
            runs = session.scalars(
                select(Run).where(Run.thread_id == thread_id).order_by(Run.created_at)
            )
            result["messages"] = [record_dict(message) for message in messages]
            result["runs"] = [record_dict(run) for run in runs]
            return result

    def rename(self, thread_id: str, title: str):
        self.thread(thread_id)
        with self.database.session.begin() as session:
            session.execute(
                update(Thread)
                .where(Thread.id == thread_id)
                .values(title=title, updated_at=now_iso())
            )

    def create_run(self, thread_id: str, content: str, selections: list[dict]) -> dict:
        self.thread(thread_id)
        with self.lock, self.database.session.begin() as session:
            active = session.scalar(
                select(Run.id).where(
                    Run.thread_id == thread_id, Run.status.in_(["queued", "running"])
                )
            )
            if active:
                raise ValueError("此对话正在回复，请先停止或等待完成")
            message = Message(
                thread_id=thread_id,
                role="user",
                content=content,
                selections_json=dump_json(selections),
            )
            session.add(message)
            session.flush()
            run = Run(thread_id=thread_id, message_id=message.id)
            session.add(run)
            session.execute(
                update(Thread).where(Thread.id == thread_id).values(updated_at=now_iso())
            )
            session.flush()
            return record_dict(run)

    def run(self, run_id: str) -> dict:
        with self.database.session() as session:
            row = session.get(Run, run_id)
            if not row:
                raise FileNotFoundError("运行不存在")
            result = record_dict(row)
        self.thread(result["thread_id"])
        return result

    def message(self, message_id: str) -> dict:
        with self.database.session() as session:
            row = session.get(Message, message_id)
            if not row:
                raise FileNotFoundError("消息不存在")
            return record_dict(row)

    def set_status(self, run_id: str, status: str, error: str = ""):
        with self.database.session.begin() as session:
            session.execute(
                update(Run)
                .where(Run.id == run_id)
                .values(status=status, error=error, updated_at=now_iso())
            )

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

    def finish(self, run_id: str, answer: str):
        with self.database.session.begin() as session:
            run = session.get(Run, run_id)
            run.status = "completed"
            run.answer = answer
            run.updated_at = now_iso()
            session.add(Message(thread_id=run.thread_id, role="assistant", content=answer))
            session.execute(
                update(Thread).where(Thread.id == run.thread_id).values(updated_at=now_iso())
            )

    def recover(self):
        with self.database.session.begin() as session:
            session.execute(
                update(Run)
                .where(Run.status.in_(["queued", "running"]))
                .values(status="interrupted", error="服务重启中断，可继续运行")
            )

    def resume(self, run_id: str):
        previous = self.run(run_id)
        if previous["status"] not in {"interrupted", "failed", "cancelled"}:
            raise ValueError("此运行不能继续")
        with self.lock, self.database.session.begin() as session:
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
            )
            session.add(row)
            session.flush()
            return record_dict(row)

    def search_history(self, thread_id: str, query: str) -> list[dict]:
        rows = self.thread(thread_id)["messages"]
        return [
            {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"][:12000],
                "selections": row["selections"],
            }
            for row in rows
            if query.casefold() in row["content"].casefold()
        ][:20]
