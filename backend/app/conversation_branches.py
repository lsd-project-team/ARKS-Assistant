"""分支与问题编辑保留档案，通过有效消息重建模型上下文。"""

from sqlalchemy import select, tuple_

from app.models import Message, Run, Thread, now_iso
from app.records import record_dict


def canonical_messages(rows, runs):
    replaced = {row.replaces_id for row in rows if row.replaces_id}
    excluded_answers = {run.response_message_id for run in runs if run.message_id in replaced}
    # 重新生成的多个回复只把截至该处的最后一个版本带入新上下文。
    answers = {}
    response_to_question = {run.response_message_id: run.message_id for run in runs}
    for row in rows:
        question = response_to_question.get(row.id)
        if question:
            answers[question] = row.id
    return [
        row
        for row in rows
        if row.id not in replaced
        and row.id not in excluded_answers
        and (row.id not in response_to_question or answers[response_to_question[row.id]] == row.id)
    ]


class ConversationBranches:
    def __init__(self, repository):
        self.repository = repository

    def context(self, thread_id, before=None):
        with self.repository.database.session() as session:
            self.repository.catalog.row(session, thread_id)
            statement = select(Message).where(Message.thread_id == thread_id)
            if before:
                cursor = self.repository.history.cursor(session, thread_id, before)
                statement = statement.where(
                    tuple_(Message.created_at, Message.id) < (cursor.created_at, cursor.id)
                )
            rows = list(session.scalars(statement.order_by(Message.created_at, Message.id)))
            runs = list(session.scalars(select(Run).where(Run.thread_id == thread_id)))
            return [
                record_dict(row) for row in canonical_messages(rows, runs) if row.context_active
            ]

    def fork(self, thread_id, message_id):
        self.repository.creation_guard()
        with self.repository.lock, self.repository.database.session.begin() as session:
            parent = self.repository.catalog.row(session, thread_id)
            cursor = self.repository.history.cursor(session, thread_id, message_id)
            rows = list(
                session.scalars(
                    select(Message)
                    .where(
                        Message.thread_id == thread_id,
                        tuple_(Message.created_at, Message.id) <= (cursor.created_at, cursor.id),
                    )
                    .order_by(Message.created_at, Message.id)
                )
            )
            runs = list(session.scalars(select(Run).where(Run.thread_id == thread_id)))
            branch = Thread(
                owner_id=parent.owner_id,
                title=f"{parent.title[:108]} · 分支",
                workspace_id=parent.workspace_id,
                project_id=parent.project_id,
                auto_title=False,
                origin_thread_id=thread_id,
                origin_message_id=message_id,
            )
            session.add(branch)
            session.flush()
            for row in canonical_messages(rows, runs):
                session.add(
                    Message(
                        thread_id=branch.id,
                        role=row.role,
                        content=row.content,
                        selections_json=row.selections_json,
                        source_options_json=row.source_options_json,
                        created_at=row.created_at,
                        origin_message_id=row.id,
                        source_workspace_id=row.source_workspace_id,
                        actor_id=row.actor_id,
                        actor_json=row.actor_json,
                    )
                )
            session.flush()
            return record_dict(branch)

    def edit_latest(self, thread_id, message_id, content, selections, source_options=None):
        with self.repository.lock, self.repository.database.session.begin() as session:
            self.repository.catalog.row(session, thread_id)
            latest = session.scalar(
                select(Message)
                .where(Message.thread_id == thread_id, Message.role == "user")
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(1)
            )
            if not latest or latest.id != message_id:
                raise ValueError("只能编辑当前对话最近一次用户问题")
            self.repository.ensure_idle(session, thread_id)
            for row in session.scalars(
                select(Message).where(
                    Message.thread_id == thread_id,
                    tuple_(Message.created_at, Message.id) >= (latest.created_at, latest.id),
                )
            ):
                row.context_active = False
            options = (
                source_options
                if source_options is not None
                else record_dict(latest)["source_options"]
            )
            run = self.repository.add_run(session, thread_id, content, selections, options)
            session.get(Message, run["message_id"]).replaces_id = message_id
            session.get(Run, run["id"]).reset_context = True
            session.get(Thread, thread_id).updated_at = now_iso()
            session.flush()
            return record_dict(session.get(Run, run["id"]))
