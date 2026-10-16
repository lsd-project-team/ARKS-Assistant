"""跨项目只读问答检索，保留原始消息、选区及所有回答版本。"""

import json

from sqlalchemy import exists, func, or_, select

from app.models import Message, Project, Run, RunEvent, Thread
from app.records import record_dict


class QuestionRecords:
    def __init__(self, database):
        self.database = database

    def list(
        self,
        query="",
        user_id="",
        project_id="",
        status="",
        after=None,
        before=None,
        limit=30,
        offset=0,
    ):
        with self.database.session() as session:
            statement = select(Thread)
            if project_id:
                statement = statement.where(Thread.project_id == project_id)
            questions = select(Message.id).where(
                Message.thread_id == Thread.id, Message.role == "user"
            )
            if user_id:
                questions = questions.where(
                    Message.actor_id == (None if user_id == "unknown" else user_id)
                )
            if after:
                questions = questions.where(Message.created_at >= after.isoformat())
            if before:
                questions = questions.where(Message.created_at <= before.isoformat())
            if status:
                questions = questions.where(
                    exists(select(Run.id).where(Run.message_id == Message.id, Run.status == status))
                )
            statement = statement.where(exists(questions))
            if query:
                pattern = (
                    "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
                )
                statement = statement.where(
                    or_(
                        Thread.title.ilike(pattern, escape="\\"),
                        exists(
                            select(Message.id).where(
                                Message.thread_id == Thread.id,
                                Message.content.ilike(pattern, escape="\\"),
                            )
                        ),
                    )
                )
            total = session.scalar(select(func.count()).select_from(statement.subquery()))
            rows = session.scalars(
                statement.order_by(Thread.updated_at.desc(), Thread.id).offset(offset).limit(limit)
            )
            items = []
            for row in rows:
                messages = list(
                    session.scalars(
                        select(Message).where(Message.thread_id == row.id, Message.role == "user")
                    )
                )
                latest = session.scalar(
                    select(Run)
                    .where(Run.thread_id == row.id)
                    .order_by(Run.created_at.desc())
                    .limit(1)
                )
                project = session.get(Project, row.project_id) if row.project_id else None
                names = list(
                    dict.fromkeys(
                        json.loads(m.actor_json).get("display_name") or "未记录" for m in messages
                    )
                )
                items.append(
                    {
                        "id": row.id,
                        "title": row.title,
                        "state": row.state,
                        "project_name": project.name if project else "独立对话",
                        "project_id": row.project_id,
                        "users": names,
                        "questions": len(messages),
                        "updated_at": row.updated_at,
                        "status": latest.status if latest else "未运行",
                    }
                )
            return {"items": items, "total": total, "limit": limit, "offset": offset}

    def detail(self, identifier, offset=0, limit=100):
        with self.database.session() as session:
            thread = session.get(Thread, identifier)
            if not thread:
                raise FileNotFoundError("问答记录不存在")
            messages = list(
                session.scalars(
                    select(Message)
                    .where(Message.thread_id == identifier)
                    .order_by(Message.created_at, Message.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            message_ids = [message.id for message in messages]
            runs = list(
                session.scalars(
                    select(Run)
                    .where(
                        Run.thread_id == identifier,
                        or_(
                            Run.message_id.in_(message_ids),
                            Run.response_message_id.in_(message_ids),
                        ),
                    )
                    .order_by(Run.created_at)
                )
            )
            result_runs = []
            for run in runs:
                events = session.scalars(
                    select(RunEvent)
                    .where(
                        RunEvent.run_id == run.id,
                        RunEvent.kind.in_(["provider_usage", "context_sources", "source_evidence"]),
                    )
                    .order_by(RunEvent.sequence)
                )
                result_runs.append(
                    {**record_dict(run), "evidence": [record_dict(event) for event in events]}
                )
            total = session.scalar(
                select(func.count()).select_from(Message).where(Message.thread_id == identifier)
            )
            project = session.get(Project, thread.project_id) if thread.project_id else None
            return {
                "thread": record_dict(thread),
                "project_name": project.name if project else "独立对话",
                "messages": [record_dict(row) for row in messages],
                "runs": result_runs,
                "total": total,
                "offset": offset,
                "limit": limit,
            }
