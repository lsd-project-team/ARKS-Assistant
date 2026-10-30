"""固定版本原图存取；新增图片与记录修订在同一个事务内提交。"""

import json

from app.core.identifiers import now_iso
from app.modules.handover.domain.records import assert_version
from app.modules.handover.domain.schemas import validate_payload
from app.modules.handover.infrastructure.persistence.models import HandoverDebugImage


class DebugImageStorage:
    def append_debug_image(self, identifier, version, metadata, data, actor):
        with self.lock, self.database.session.begin() as session:
            row = self._get(session, identifier)
            assert_version(row.version, version)
            if row.kind != "debug_issue" or row.state == "archived":
                raise ValueError("只能为未归档的问题与经验记录添加原图")
            payload = json.loads(row.payload_json)
            images = payload.setdefault("images", [])
            if len(images) >= 100:
                raise ValueError("每条记录最多保存 100 处原图")
            reference = {key: metadata[key] for key in ("id", "name", "recorded_at")}
            # 相同图片只存一份字节，但每次添加都保留独立的位置及原记录时间。
            if not session.get(HandoverDebugImage, (identifier, metadata["id"])):
                session.add(
                    HandoverDebugImage(
                        record_id=identifier,
                        id=metadata["id"],
                        media_type=metadata["media_type"],
                        content=data,
                    )
                )
            images.append(reference)
            row.payload_json = json.dumps(validate_payload(row.kind, payload), ensure_ascii=False)
            row.version += 1
            row.updated_at = now_iso()
            if row.state == "confirmed":
                row.state = "needs_review"
            self._snapshot(session, row, "updated", actor, f"添加原图：{metadata['name']}")
            self._invalidate(session, identifier, actor, "关联原图已更新")
            # 复用同一事务的固定版本投影，避免另开会话读取尚未提交的内容。
            session.flush()
            result = self._revision(session, identifier, row.version)
            result.pop("confirmation", None)
            return result

    def debug_image(self, identifier, version, index):
        with self.database.session() as session:
            row = self._revision(session, identifier, version)
            images = row["payload"].get("images", [])
            if row["kind"] != "debug_issue" or index < 0 or index >= len(images):
                raise FileNotFoundError("该记录版本中没有这张原图")
            image = session.get(HandoverDebugImage, (identifier, images[index]["id"]))
            if not image:
                raise FileNotFoundError("原图不存在")
            return {"content": image.content, "media_type": image.media_type}
