"""附件按账号和项目保存；消息记录固定版本元数据，正文按需分页读取。"""

import hashlib
import json
import re
from pathlib import Path

from sqlalchemy import exists, or_, select

from app.core.identifiers import new_id
from app.modules.auth.ownership import current_owner, owner_filter, thread_filter
from app.modules.chat.attachment_parsing import MAX_ATTACHMENTS, parse_attachment
from app.modules.chat.models import ChatAttachment, Message, QueuedQuestion, Thread


def attachment_metadata(row):
    return {
        "id": row.id,
        "filename": row.filename,
        "sha256": row.sha256,
        "size": row.size,
        "parse_status": row.parse_status,
        "parse_notes": row.parse_notes,
        "characters": len(row.content),
        "created_at": row.created_at,
    }


class ChatAttachments:
    def __init__(self, repository):
        self.repository = repository
        self.root = (
            Path(repository.database.engine.url.database).parent / "scratch/chat-attachments"
        )

    def file(self, identifier):
        if not re.fullmatch(r"[a-f0-9-]{36}", identifier):
            raise FileNotFoundError("附件不存在")
        path = (self.root / identifier).resolve()
        if not path.is_relative_to(self.root.resolve()) or path.is_symlink():
            raise ValueError("附件路径无效")
        return path

    def row(self, session, identifier):
        row = session.scalar(
            select(ChatAttachment).where(
                ChatAttachment.id == identifier, owner_filter(ChatAttachment)
            )
        )
        if not row:
            raise FileNotFoundError("附件不存在")
        if row.workspace_id != self.repository.workspace_id:
            # 对话移入另一个项目后，历史附件继续随消息可读。
            linked = session.scalar(
                select(Message.id)
                .join(Thread)
                .where(
                    Thread.workspace_id == self.repository.workspace_id,
                    thread_filter(),
                    Message.attachments_json.contains(f'"id":"{row.id}"'),
                )
                .limit(1)
            )
            if not linked:
                raise FileNotFoundError("附件不属于当前项目")
        return row

    def upload(self, data, filename):
        self.repository.creation_guard()
        filename, content, status, notes = parse_attachment(data, filename)
        identifier = new_id()
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.file(identifier)
        try:
            target.write_bytes(data)
            with self.repository.database.session.begin() as session:
                row = ChatAttachment(
                    id=identifier,
                    owner_id=current_owner(),
                    workspace_id=self.repository.workspace_id,
                    filename=filename,
                    sha256=hashlib.sha256(data).hexdigest(),
                    size=len(data),
                    content=content,
                    parse_status=status,
                    parse_notes=notes,
                )
                session.add(row)
                session.flush()
                return attachment_metadata(row)
        except BaseException:
            target.unlink(missing_ok=True)
            raise

    def bind(self, session, identifiers):
        if len(identifiers) > MAX_ATTACHMENTS or len(set(identifiers)) != len(identifiers):
            raise ValueError("每条消息最多附加 10 个文件，不能重复附加同一文件")
        return [attachment_metadata(self.row(session, identifier)) for identifier in identifiers]

    def read(self, identifier, offset=0, limit=12000):
        if offset < 0 or not 1 <= limit <= 12000:
            raise ValueError("附件读取范围无效，单次最多 12000 字")
        with self.repository.database.session() as session:
            row = self.row(session, identifier)
            return {
                **attachment_metadata(row),
                "content": row.content[offset : offset + limit],
                "offset": offset,
                "next_offset": offset + limit if offset + limit < len(row.content) else None,
            }

    def download(self, identifier):
        with self.repository.database.session() as session:
            row = self.row(session, identifier)
            metadata = attachment_metadata(row)
        path = self.file(identifier)
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]
        ):
            raise ValueError("附件原文件缺失或版本不符，请恢复备份后重试")
        return path, metadata["filename"]

    def search(self, identifier, query, offset=0):
        if not query.strip() or len(query) > 200 or offset < 0:
            raise ValueError("请提供 1 到 200 字的检索词和有效起点")
        with self.repository.database.session() as session:
            row = self.row(session, identifier)
            found, cursor = [], offset
            while len(found) < 12:
                index = row.content.lower().find(query.lower(), cursor)
                if index < 0:
                    return {"matches": found, "next_offset": None}
                start = max(0, index - 150)
                found.append(
                    {"offset": start, "content": row.content[start : index + len(query) + 350]}
                )
                cursor = index + len(query)
            return {"matches": found, "next_offset": cursor if cursor < len(row.content) else None}

    @staticmethod
    def referenced(session, identifier):
        marker = f'"id":"{identifier}"'
        return session.scalar(
            select(
                or_(
                    exists().where(Message.attachments_json.contains(marker)),
                    exists().where(QueuedQuestion.attachments_json.contains(marker)),
                )
            )
        )

    def remove(self, identifier):
        with self.repository.lock, self.repository.database.session.begin() as session:
            row = self.row(session, identifier)
            if self.referenced(session, identifier):
                raise ValueError("附件已用于消息或待发问题，不能删除原文件")
            session.delete(row)
        self.file(identifier).unlink(missing_ok=True)

    def thread_ids(self, thread_id):
        with self.repository.database.session() as session:
            self.repository.catalog.row(session, thread_id, include_deleted=True)
            return {
                item["id"]
                for model in (Message, QueuedQuestion)
                for raw in session.scalars(
                    select(model.attachments_json).where(model.thread_id == thread_id)
                )
                for item in json.loads(raw)
            }

    def prune(self, identifiers):
        """永久清理后仅删除无人引用的原件，分支共用的文档继续保留。"""
        removed = []
        with self.repository.lock, self.repository.database.session.begin() as session:
            for identifier in identifiers:
                row = session.get(ChatAttachment, identifier)
                if row and not self.referenced(session, identifier):
                    session.delete(row)
                    removed.append(identifier)
        for identifier in removed:
            self.file(identifier).unlink(missing_ok=True)
