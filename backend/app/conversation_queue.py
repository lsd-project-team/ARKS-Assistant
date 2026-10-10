"""等待的问题独立于原始消息，出队和创建运行必须同一事务。"""

from sqlalchemy import func, select

from app.config import dump_json
from app.models import QueuedQuestion, Run, now_iso
from app.records import record_dict


class ConversationQueue:
    def __init__(self, repository):
        self.repository = repository

    def row(self, session, item_id):
        row = session.get(QueuedQuestion, item_id)
        if not row:
            raise ValueError("此问题已开始发送或已被移除，请刷新队列")
        self.repository.catalog.row(session, row.thread_id)
        return row

    def list(self, thread_id):
        with self.repository.database.session() as session:
            thread = self.repository.catalog.row(session, thread_id)
            rows = session.scalars(
                select(QueuedQuestion)
                .where(QueuedQuestion.thread_id == thread_id)
                .order_by(QueuedQuestion.created_at, QueuedQuestion.id)
            )
            return {"paused": thread.queue_paused, "items": [record_dict(row) for row in rows]}

    def add(self, thread_id, content, selections):
        with self.repository.lock, self.repository.database.session.begin() as session:
            thread = self.repository.catalog.row(session, thread_id)
            thread.state = "active"
            count = session.scalar(
                select(func.count())
                .select_from(QueuedQuestion)
                .where(QueuedQuestion.thread_id == thread_id)
            )
            if count >= 20:
                raise ValueError("等待发送队列最多保留 20 个问题")
            row = QueuedQuestion(
                thread_id=thread_id, content=content, selections_json=dump_json(selections)
            )
            session.add(row)
            session.flush()
            return record_dict(row)

    def update(self, item_id, content, selections, version):
        with self.repository.lock, self.repository.database.session.begin() as session:
            row = self.row(session, item_id)
            if row.updated_at != version:
                raise ValueError("问题已在其他窗口更新，请重新打开后编辑")
            row.content, row.selections_json = content, dump_json(selections)
            row.updated_at = now_iso()
            session.flush()
            return record_dict(row)

    def cancel(self, item_id):
        with self.repository.lock, self.repository.database.session.begin() as session:
            session.delete(self.row(session, item_id))

    def pause(self, thread_id, paused=True):
        with self.repository.database.session.begin() as session:
            self.repository.catalog.row(
                session, thread_id, include_deleted=True
            ).queue_paused = paused

    def dispatch(self, thread_id):
        with self.repository.lock, self.repository.database.session.begin() as session:
            thread = self.repository.catalog.row(session, thread_id, include_deleted=True)
            if thread.queue_paused or thread.state != "active":
                return None
            if session.scalar(
                select(Run.id).where(
                    Run.thread_id == thread_id, Run.status.in_(["queued", "running"])
                )
            ):
                return None
            row = session.scalar(
                select(QueuedQuestion)
                .where(QueuedQuestion.thread_id == thread_id)
                .order_by(QueuedQuestion.created_at, QueuedQuestion.id)
                .limit(1)
            )
            if not row:
                return None
            item = record_dict(row)
            run = self.repository.add_run(session, thread_id, row.content, item["selections"])
            session.delete(row)
            return run
