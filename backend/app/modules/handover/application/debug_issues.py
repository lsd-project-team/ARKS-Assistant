"""调试问题用例；录入身份与原始描述由服务端维护。"""

from app.modules.handover.application.commands import Write
from app.modules.handover.application.ports import RecordRepository
from app.modules.handover.domain.images import image_metadata
from app.modules.handover.domain.schemas import DebugIssue


def actor_name(actor):
    return actor.get("display_name") or actor.get("username") or "对话录入"


class DebugIssues:
    def __init__(self, repository: RecordRepository):
        self.store = repository

    def rows(self, include_archived=False):
        return self.store.debug_rows(include_archived)

    def save(self, body, actor, identifier=None):
        payload = body.payload.model_dump()
        if identifier:
            previous = self.store.get(identifier)
            if previous["kind"] != "debug_issue":
                raise ValueError("不是调试问题记录")
            if previous["state"] == "archived":
                raise ValueError("请先恢复归档记录")
            payload = {**previous["payload"], **payload}
            return self.store.update(
                identifier,
                Write(
                    kind="debug_issue",
                    title=body.title,
                    payload=payload,
                    actor=actor_name(actor),
                    version=body.version,
                    reason="更新调试问题与处理结果",
                ),
            )
        payload.update(
            origin="human", reported_by=actor_name(actor), original_text=payload["problem"]
        )
        return self.store.create("debug_issue", body.title, payload, actor_name(actor))

    def add_image(self, identifier, version, data, filename, recorded_at, actor):
        metadata = image_metadata(data, filename, recorded_at)
        return self.store.append_debug_image(identifier, version, metadata, data, actor_name(actor))

    def captured(self, message_id):
        return next(
            (
                row
                for row in self.rows(True)
                if row["payload"].get("source_message_id") == message_id
            ),
            None,
        )

    def capture(self, title, payload, original, message, project_id):
        # 同一条消息的恢复、重试和重新生成只对应一条记录。
        with self.store.lock:
            existing = self.captured(message["id"])
            if existing:
                return existing
            actor = message.get("actor") or {}
            value = DebugIssue.model_validate(
                {
                    **payload,
                    "origin": "ai",
                    "original_text": original,
                    "reported_by": actor_name(actor),
                    "source_message_id": message["id"],
                    "source_thread_id": message["thread_id"],
                    "source_project_id": project_id or "",
                }
            ).model_dump()
            return self.store.create("debug_issue", title, value, actor_name(actor))
