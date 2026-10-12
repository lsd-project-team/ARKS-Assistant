"""导出项目归档；只包含此项目的业务数据，不包含密钥、全局设置或源码副本。"""

import io
import json
import zipfile

from sqlalchemy import select

from app.models import Message, ProjectMaterial, ProjectMaterialRevision, Thread
from app.records import record_dict


def export_project(projects, project_id):
    output = io.BytesIO()
    project = projects.get(project_id)
    with (
        projects.database.session() as session,
        zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive,
    ):

        def write(name, value):
            archive.writestr(name, json.dumps(value, ensure_ascii=False, indent=2))

        write("project.json", project)
        archive.writestr(
            "README.md",
            "# 项目归档\n\n包含项目信息、对话（含已归档和回收站）、资料历史版本和项目记忆。"
            "源码目录保存为关联信息，实际源码不复制；全局设置和 API 密钥不导出。\n",
        )
        for thread in session.scalars(
            select(Thread)
            .where(Thread.project_id == project_id)
            .order_by(Thread.created_at, Thread.id)
        ):
            messages = [
                record_dict(row)
                for row in session.scalars(
                    select(Message)
                    .where(Message.thread_id == thread.id)
                    .order_by(Message.created_at, Message.id)
                )
            ]
            write(f"conversations/{thread.id}.json", {**record_dict(thread), "messages": messages})
        for material in session.scalars(
            select(ProjectMaterial).where(ProjectMaterial.project_id == project_id)
        ):
            revisions = [
                record_dict(row)
                for row in session.scalars(
                    select(ProjectMaterialRevision)
                    .where(ProjectMaterialRevision.material_id == material.id)
                    .order_by(ProjectMaterialRevision.version)
                )
            ]
            write(
                f"materials/{material.id}.json", {**record_dict(material), "revisions": revisions}
            )
        memories = [
            row
            for row in projects.services(project_id).memories.list()
            if row["scope"] == "project"
        ]
        write("memories.json", memories)
    return output.getvalue()
