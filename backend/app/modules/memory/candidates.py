"""从原始消息建立固定输入；删除、移动、重答和来源开关都参与资格核查。"""

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy import select

from app.core.config import dump_json
from app.modules.auth.models import Account
from app.modules.chat.branches import canonical_messages
from app.modules.chat.models import Message, QueuedQuestion, Run, RunEvent, Thread
from app.modules.memory.generation_protocol import sanitized
from app.modules.projects.models import Project


def utc_now():
    return datetime.now(UTC)


def snapshot_thread(database, identifier, policy, *, now=None, require_idle=True, secrets=()):
    now = now or utc_now()
    with database.session() as session:
        thread = session.get(Thread, identifier)
        if not thread or thread.state == "deleted":
            return None
        owner = thread.owner_id or "local"
        account = session.get(Account, owner)
        if thread.owner_id and (not account or not account.enabled):
            return None
        project = session.get(Project, thread.project_id) if thread.project_id else None
        if thread.project_id and (
            not project
            or project.state == "deleted"
            or (project.owner_id and project.owner_id != thread.owner_id)
        ):
            return None
        updated = datetime.fromisoformat(thread.updated_at).replace(tzinfo=UTC)
        if require_idle and updated < now - timedelta(days=policy.max_age_days):
            return None
        if require_idle and updated > now - timedelta(hours=policy.idle_hours):
            return None
        runs = list(session.scalars(select(Run).where(Run.thread_id == identifier)))
        if any(row.status in {"running", "queued"} for row in runs):
            return None
        if session.scalar(select(QueuedQuestion.id).where(QueuedQuestion.thread_id == identifier)):
            return None
        rows = list(
            session.scalars(
                select(Message)
                .where(Message.thread_id == identifier)
                .order_by(Message.created_at, Message.id)
            )
        )
        canonical = [row for row in canonical_messages(rows, runs) if row.context_active]
        active = {row.id: row for row in canonical}
        pairs, run_ids = {}, []
        for run in runs:
            question, answer = active.get(run.message_id), active.get(run.response_message_id)
            if run.status != "completed" or not question or not answer:
                continue
            if question.actor_id != thread.owner_id:
                continue  # 共享对话不能把其他发言人的偏好写到会话主人的记忆。
            options = json.loads(question.source_options_json)
            if not options.get("use_memory", True):
                continue
            pairs[question.id], pairs[answer.id] = question, answer
            run_ids.append(run.id)
        if len(pairs) < policy.min_completed_turns * 2:
            return None
        messages = [
            {"id": row.id, "role": row.role, "content": row.content}
            for row in canonical
            if row.id in pairs
        ]
        if sum(len(row["content"].strip()) for row in messages) < 120:
            return None
        # 实际读取的源码版本保留为历史依据，不把当时验证推广为当前实现。
        sources = []
        for event in session.scalars(
            select(RunEvent).where(RunEvent.run_id.in_(run_ids), RunEvent.kind == "source_evidence")
        ):
            row = json.loads(event.payload_json)
            source = {key: row[key] for key in ("path", "version") if key in row}
            if len(source) == 2 and source not in sources:
                sources.append(source)
        result = sanitized(
            {
                "thread_id": identifier,
                "owner_id": owner,
                "workspace_id": thread.workspace_id,
                "messages": messages,
                "sources": sources,
                "source_updated_at": thread.updated_at,
            },
            secrets,
        )
        # 标题、置顶等元数据更新不会使已提取的事实失效；正文与归属仍参与指纹。
        fingerprint_input = {
            key: value for key, value in result.items() if key != "source_updated_at"
        }
        result["fingerprint"] = sha256(dump_json(fingerprint_input).encode()).hexdigest()
        return result


def candidate_threads(database, policy, *, now=None):
    now = now or utc_now()
    with database.session() as session:
        return list(
            session.scalars(
                select(Thread.id)
                .where(
                    Thread.state != "deleted",
                    Thread.updated_at <= (now - timedelta(hours=policy.idle_hours)).isoformat(),
                    Thread.updated_at >= (now - timedelta(days=policy.max_age_days)).isoformat(),
                )
                .order_by(Thread.updated_at.desc())
            )
        )
