"""末条回复共用版本组，历史重答追加独立请求并固定原问题上下文。"""

from sqlalchemy import select

from app.core.config import dump_json
from app.core.identifiers import now_iso
from app.infrastructure.database.serialization import record_dict
from app.modules.chat.models import Message, Run, RunEvent

CONTEXT_EVENT = "regeneration_context"


def record_context(session, run_id, context):
    if context:
        session.add(
            RunEvent(run_id=run_id, sequence=1, kind=CONTEXT_EVENT, payload_json=dump_json(context))
        )


def regenerate(repository, run_id):
    repository.creation_guard()
    previous = repository.run(run_id)
    repository.ensure_source_compatible(previous["message_id"])
    if previous["status"] != "completed" or not previous["response_message_id"]:
        raise ValueError("只能重新生成已完成的回复")
    with repository.lock, repository.database.session.begin() as session:
        thread = repository.catalog.row(session, previous["thread_id"])
        repository.ensure_idle(session, thread.id)
        latest = session.scalar(
            select(Run).where(Run.thread_id == thread.id).order_by(Run.created_at.desc()).limit(1)
        )
        if latest.message_id == previous["message_id"]:
            # 从旧版本点击重生成时，沿用该组最新检查点；项目切换已使其失效时重新建立。
            inherited_event = session.scalar(
                select(RunEvent).where(RunEvent.run_id == latest.id, RunEvent.kind == CONTEXT_EVENT)
            )
            inherited = record_dict(inherited_event)["payload"] if inherited_event else None
            row = Run(
                thread_id=thread.id, message_id=previous["message_id"], regenerated_from=run_id
            )
            session.add(row)
            session.flush()
            if latest.status != "completed" or (
                inherited and inherited.get("conversation_generation") != thread.context_generation
            ):
                # 失败或停止的旧检查点可能还有未完成工具调用，重新生成应使用干净上下文。
                question = session.get(Message, row.message_id)
                context = fresh_context(session, thread, question, "replace", question.id)
            elif inherited:
                context = {**inherited, "mode": "replace", "instruction_id": f"regenerate:{row.id}"}
                # 重答组的新版本也会使后续普通会话中的旧答案/摘要失效。
                thread.context_generation += 1
                context["conversation_generation"] = thread.context_generation
            else:
                context = None
        else:
            row, context = append_request(repository, session, thread, previous)
        thread.updated_at = now_iso()
        record_context(session, row.id, context)
        session.flush()
        return record_dict(row)


def append_request(repository, session, thread, previous):
    original = session.get(Message, previous["message_id"])
    snapshot = record_dict(original)
    created = repository.add_run(
        session, thread.id, original.content, snapshot["selections"], snapshot["source_options"]
    )
    row = session.get(Run, created["id"])
    row.regenerated_from = previous["id"]
    question = session.get(Message, row.message_id)
    origin = (
        session.get(Message, original.origin_message_id) if original.origin_message_id else None
    )
    question.origin_message_id = (
        origin.id if origin and origin.thread_id == thread.id else original.id
    )
    question.source_workspace_id = original.source_workspace_id
    return row, fresh_context(session, thread, question, "append", question.id)


def fresh_context(session, thread, question, mode, instruction_id):
    origin = (
        session.get(Message, question.origin_message_id) if question.origin_message_id else None
    )
    before = origin.id if origin and origin.thread_id == thread.id else question.id
    # 单独一代保存本次原题重答；再下一代留给后续普通对话，避免覆盖或删掉原来的问答。
    thread.context_generation += 2
    return {
        "mode": mode,
        "generation": thread.context_generation - 1,
        "conversation_generation": thread.context_generation,
        "before_message_id": before,
        "instruction_id": instruction_id,
    }


def mark_reanswered_questions(session, thread_id, messages, runs):
    questions = {row["message_id"] for row in runs if row.get("regenerated_from")}
    origins = {
        row["origin_message_id"]
        for row in messages
        if row["id"] in questions and row.get("origin_message_id")
    }
    if not origins:
        return
    local_origins = set(
        session.scalars(
            select(Message.id).where(Message.thread_id == thread_id, Message.id.in_(origins))
        )
    )
    for row in messages:
        if (
            row["role"] == "user"
            and row["id"] in questions
            and row.get("origin_message_id") in local_origins
        ):
            row["reanswered_from"] = row["origin_message_id"]


def previous_run_event(repository, run, kind):
    cursor = run.get("resumed_from") or run.get("regenerated_from")
    if not cursor:
        return repository.latest_event(run["thread_id"], kind)
    visited = set()
    while cursor and cursor not in visited:
        visited.add(cursor)
        event = repository.run_event(cursor, kind)
        if event is not None:
            return event
        previous = repository.run(cursor)
        cursor = previous.get("resumed_from") or previous.get("regenerated_from")
    # 旧记录可能没保存本轮计划，只能回查它当时以前的事件，不能借用后续问题的计划。
    with repository.database.session() as session:
        event = session.scalar(
            select(RunEvent)
            .join(Run, Run.id == RunEvent.run_id)
            .where(
                Run.thread_id == run["thread_id"],
                Run.created_at <= previous["created_at"],
                RunEvent.kind == kind,
            )
            .order_by(Run.created_at.desc(), RunEvent.sequence.desc())
            .limit(1)
        )
        return record_dict(event)["payload"] if event else None
