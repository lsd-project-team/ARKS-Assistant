"""消息分页与原始历史检索；游标必须属于目标会话。"""

from sqlalchemy import exists, func, select, tuple_

from app.conversation_catalog import ConversationCatalog, snippet
from app.database import Database
from app.models import Message
from app.records import record_dict


class ConversationHistory:
    def __init__(self, database: Database, catalog: ConversationCatalog):
        self.database, self.catalog = database, catalog

    @staticmethod
    def cursor(session, thread_id: str, message_id: str):
        row = session.get(Message, message_id)
        if not row or row.thread_id != thread_id:
            raise FileNotFoundError("消息不属于当前对话")
        return row

    def page(self, thread_id: str, limit=80, before=None, around=None):
        limit = min(200, max(1, limit))
        with self.database.session() as session:
            self.catalog.row(session, thread_id)
            statement = select(Message).where(Message.thread_id == thread_id)
            order = tuple_(Message.created_at, Message.id)
            if around:
                cursor = self.cursor(session, thread_id, around)
                position = (cursor.created_at, cursor.id)
                earlier = list(
                    session.scalars(
                        statement.where(order < position)
                        .order_by(Message.created_at.desc(), Message.id.desc())
                        .limit(limit // 2)
                    )
                )
                later = list(
                    session.scalars(
                        statement.where(order >= position)
                        .order_by(Message.created_at, Message.id)
                        .limit(limit - len(earlier))
                    )
                )
                rows = [*reversed(earlier), *later]
            else:
                if before:
                    cursor = self.cursor(session, thread_id, before)
                    statement = statement.where(order < (cursor.created_at, cursor.id))
                rows = list(
                    reversed(
                        list(
                            session.scalars(
                                statement.order_by(
                                    Message.created_at.desc(), Message.id.desc()
                                ).limit(limit)
                            )
                        )
                    )
                )
            has_older = bool(
                rows
                and session.scalar(
                    select(
                        exists().where(
                            Message.thread_id == thread_id, order < (rows[0].created_at, rows[0].id)
                        )
                    )
                )
            )
            has_newer = bool(
                rows
                and session.scalar(
                    select(
                        exists().where(
                            Message.thread_id == thread_id,
                            order > (rows[-1].created_at, rows[-1].id),
                        )
                    )
                )
            )
            return {
                "messages": [record_dict(row) for row in rows],
                "has_older": has_older,
                "has_newer": has_newer,
                "before_cursor": rows[0].id if rows else None,
            }

    def search(self, thread_id: str, query: str, offset=0, limit=10):
        query = query.strip()
        if not query or len(query) > 300:
            raise ValueError("历史检索词长度必须在 1 到 300 之间")
        predicate = [Message.thread_id == thread_id, self.catalog.match(query)]
        with self.database.session() as session:
            self.catalog.row(session, thread_id)
            total = session.scalar(select(func.count(Message.id)).where(*predicate))
            rows = session.scalars(
                select(Message)
                .where(*predicate)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .offset(max(0, offset))
                .limit(min(20, max(1, limit)))
            )
            matches = []
            for row in rows:
                item = record_dict(row)
                if len(item["content"]) > 12000:
                    item["content"] = snippet(item["content"], query, 12000)
                    item["partial"] = True
                # 选区也可能很长，围绕命中返回片段，全文通过分页工具读取。
                for selection in item["selections"]:
                    content = selection.get("content", "")
                    if len(content) > 4000:
                        selection["content"] = snippet(content, query, 4000)
                        selection["partial"] = True
                matches.append(item)
            next_offset = max(0, offset) + len(matches)
            return {
                "matches": matches,
                "total": total,
                "has_more": next_offset < total,
                "next_offset": next_offset if next_offset < total else None,
            }

    def read(self, thread_id: str, message_id: str, offset=0, limit=12000):
        with self.database.session() as session:
            self.catalog.row(session, thread_id)
            item = record_dict(self.cursor(session, thread_id, message_id))
        offset, limit = max(0, offset), min(12000, max(1, limit))
        original = item["content"]
        total = max([len(original), *(len(row.get("content", "")) for row in item["selections"])])
        item["content"] = original[offset : offset + limit]
        for selection in item["selections"]:
            selection["content"] = selection["content"][offset : offset + limit]
        item.update(offset=offset, next_offset=offset + limit if offset + limit < total else None)
        return item
