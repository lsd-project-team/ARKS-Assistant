"""资料列表与详情只补充文件元信息，不加载附件正文。"""

from sqlalchemy import select

from app.modules.handover.domain.materials import original_media_type
from app.modules.handover.infrastructure.persistence.models import HandoverBlob, HandoverEvent


def attach_material_files(session, rows):
    materials = {row["id"]: row for row in rows if row["kind"] in {"source", "interview"}}
    if not materials:
        return rows
    for row in materials.values():
        row["created_by"] = ""
        row["original_file"] = None
    for identifier, actor in session.execute(
        select(HandoverEvent.record_id, HandoverEvent.actor)
        .where(HandoverEvent.record_id.in_(materials), HandoverEvent.action == "created")
        .order_by(HandoverEvent.id.desc())
    ):
        materials[identifier]["created_by"] = actor
    for identifier, filename in session.execute(
        select(HandoverBlob.record_id, HandoverBlob.name).where(
            HandoverBlob.record_id.in_(materials)
        )
    ):
        materials[identifier]["original_file"] = {
            "name": filename,
            "previewable": original_media_type(filename) is not None,
        }
    return rows
