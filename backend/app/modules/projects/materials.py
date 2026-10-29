"""仅供旧回答和交接来源读取固定版本，不再提供项目资料管理或 AI 检索。"""

from sqlalchemy import select

from app.infrastructure.database.serialization import record_dict
from app.modules.projects.models import ProjectMaterial, ProjectMaterialRevision


class Materials:
    def __init__(self, database, project_id):
        self.database, self.project_id = database, project_id

    def read(self, material_id, version):
        with self.database.session() as session:
            row = session.get(ProjectMaterial, material_id)
            if not row or row.project_id != self.project_id:
                raise FileNotFoundError("资料不存在于此项目")
            revision = session.scalar(
                select(ProjectMaterialRevision).where(
                    ProjectMaterialRevision.material_id == material_id,
                    ProjectMaterialRevision.version == version,
                )
            )
            if not revision:
                raise FileNotFoundError("资料版本不存在")
            return {
                **record_dict(row),
                "title": revision.title,
                "content": revision.content,
                "version": revision.version,
                "revision_at": revision.created_at,
            }
