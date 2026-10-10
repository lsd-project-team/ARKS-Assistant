"""会话列表与生命周期；回收站保存完整档案，彻底删除才清理数据。"""

from __future__ import annotations

import re

from sqlalchemy import delete, exists, func, or_, select

from app.database import Database
from app.models import Message, Run, Thread, now_iso
from app.records import record_dict


def title_from_question(content: str, selections: list[dict]) -> str:
    title = re.sub(r"\s+", " ", content).strip()[:48]
    if selections and len(title) < 20:
        name = selections[0]["path"].replace("\\", "/").rsplit("/", 1)[-1]
        title = f"{name} · {title}"
    return title or "源码问答"


def snippet(content: str, query: str, width: int = 160) -> str:
    index = content.casefold().find(query.casefold())
    start = max(0, index - 45) if index >= 0 else 0
    end = start + width
    return ("…" if start else "") + content[start:end] + ("…" if end < len(content) else "")


class ConversationCatalog:
    def __init__(self, database: Database, workspace_id: str):
        self.database, self.workspace_id = database, workspace_id

    def row(self, session, thread_id: str, *, include_deleted=False):
        row = session.get(Thread, thread_id)
        if not row or row.workspace_id != self.workspace_id:
            raise FileNotFoundError("对话不存在")
        if row.state == "deleted" and not include_deleted:
            raise FileNotFoundError("对话已移入回收站，可以恢复后继续")
        return row

    def get(self, thread_id: str, *, include_deleted=False) -> dict:
        with self.database.session() as session:
            return record_dict(self.row(session, thread_id, include_deleted=include_deleted))

    @staticmethod
    def match(query: str):
        return or_(
            Message.content.icontains(query, autoescape=True),
            Message.selections_json.icontains(query, autoescape=True),
        )

    def list(self, state="active", query="", limit=100, offset=0) -> list[dict]:
        if state not in {"active", "archived", "deleted"}:
            raise ValueError("无效的会话列表类型")
        query = query.strip()[:300]
        predicate = [Thread.workspace_id == self.workspace_id, Thread.state == state]
        if query:
            predicate.append(
                or_(
                    Thread.title.icontains(query, autoescape=True),
                    exists(
                        select(Message.id).where(Message.thread_id == Thread.id, self.match(query))
                    ),
                )
            )
        latest_status = (
            select(Run.status)
            .where(Run.thread_id == Thread.id)
            .order_by(Run.created_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        latest_finished = (
            select(func.max(Run.updated_at))
            .where(Run.thread_id == Thread.id, Run.status == "completed")
            .scalar_subquery()
        )
        count = (
            select(func.count(Message.id)).where(Message.thread_id == Thread.id).scalar_subquery()
        )
        statement = (
            select(Thread, latest_status, latest_finished, count)
            .where(*predicate)
            .order_by(Thread.pinned_order.is_(None), Thread.pinned_order, Thread.updated_at.desc())
            .offset(max(0, offset))
            .limit(min(200, max(1, limit)))
        )
        with self.database.session() as session:
            results = []
            for row, status, finished, message_count in session.execute(statement):
                item = {
                    **record_dict(row),
                    "latest_status": status,
                    "message_count": message_count,
                    "has_unread": bool(
                        finished and (not row.last_read_at or finished > row.last_read_at)
                    ),
                }
                if query:
                    hit = session.scalar(
                        select(Message)
                        .where(Message.thread_id == row.id, self.match(query))
                        .order_by(Message.created_at.desc())
                        .limit(1)
                    )
                    item["matched_message_id"] = hit.id if hit else None
                    selections = record_dict(hit)["selections"] if hit else []
                    selection_text = "\n".join(
                        f"{selection.get('path', '')}\n{selection.get('content', '')}"
                        for selection in selections
                    )
                    item["snippet"] = snippet(
                        hit.content
                        if hit and query.casefold() in hit.content.casefold()
                        else selection_text
                        if hit
                        else row.title,
                        query,
                    )
                results.append(item)
            return results

    def change(self, thread_id: str, state: str) -> dict:
        if state not in {"active", "archived", "deleted"}:
            raise ValueError("无效的会话状态")
        with self.database.session.begin() as session:
            row = self.row(session, thread_id, include_deleted=True)
            row.state = state
            row.deleted_at = now_iso() if state == "deleted" else None
            row.updated_at = now_iso()
            return record_dict(row)

    def pin(self, thread_id: str, pinned: bool) -> dict:
        with self.database.session.begin() as session:
            row = self.row(session, thread_id)
            if pinned and row.pinned_order is not None:
                return record_dict(row)
            maximum = session.scalar(
                select(func.max(Thread.pinned_order)).where(
                    Thread.workspace_id == self.workspace_id
                )
            )
            row.pinned_order = (maximum or 0) + 1 if pinned else None
            return record_dict(row)

    def reorder(self, ids: list[str]):
        if len(ids) != len(set(ids)):
            raise ValueError("置顶会话不能重复")
        with self.database.session.begin() as session:
            rows = list(
                session.scalars(
                    select(Thread).where(
                        Thread.workspace_id == self.workspace_id,
                        Thread.state == "active",
                        Thread.pinned_order.is_not(None),
                    )
                )
            )
            if {row.id for row in rows} != set(ids):
                raise ValueError("置顶列表已变化，请刷新后重试")
            order = {identifier: index for index, identifier in enumerate(ids)}
            for row in rows:
                row.pinned_order = order[row.id]

    def mark_read(self, thread_id: str):
        with self.database.session.begin() as session:
            self.row(session, thread_id).last_read_at = now_iso()

    def move_pin(self, thread_id: str, direction: int):
        with self.database.session.begin() as session:
            target = self.row(session, thread_id)
            rows = list(
                session.scalars(
                    select(Thread)
                    .where(
                        Thread.workspace_id == self.workspace_id,
                        Thread.state == "active",
                        Thread.pinned_order.is_not(None),
                    )
                    .order_by(Thread.pinned_order, Thread.updated_at.desc())
                )
            )
            if target not in rows:
                raise ValueError("请先置顶此对话")
            index = rows.index(target)
            other = index + direction
            if 0 <= other < len(rows):
                rows[index], rows[other] = rows[other], rows[index]
            for order, row in enumerate(rows):
                row.pinned_order = order

    def purge(self, thread_id: str):
        with self.database.session.begin() as session:
            row = self.row(session, thread_id, include_deleted=True)
            if row.state != "deleted":
                raise ValueError("请先将对话移入回收站")
            # 先删除运行，再删除其用户消息，避免外键反向引用阻止清理。
            session.execute(delete(Run).where(Run.thread_id == thread_id))
            session.execute(delete(Message).where(Message.thread_id == thread_id))
            session.delete(row)
