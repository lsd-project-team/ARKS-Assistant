"""耗时项目的命名与访问边界；不读取或修改聊天项目。"""

from sqlalchemy import select

from app.core.identifiers import now_iso
from app.modules.action_timing.ledger_schemas import name_key
from app.modules.action_timing.models import TimingProject
from app.modules.auth.ownership import current_owner, owner_filter, unrestricted


class TimingProjects:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def require(session, identifier):
        row = session.get(TimingProject, identifier)
        if not row or (not unrestricted() and row.owner_id != current_owner()):
            raise FileNotFoundError("耗时项目不存在")
        return row

    @staticmethod
    def default(session):
        row = session.scalar(
            select(TimingProject)
            .where(owner_filter(TimingProject))
            .order_by(TimingProject.created_at, TimingProject.id)
            .limit(1)
        )
        if row:
            return row
        # 固定账号默认ID配合调用方写事务，避免多个窗口首次打开时重复创建。
        row = TimingProject(
            id=f"timing-{current_owner() or 'local'}", owner_id=current_owner(), name="智芯2200"
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def data(row):
        return {"id": row.id, "name": row.name, "version": row.version}

    def listing(self):
        with self.database.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            default = self.default(session)
            rows = session.scalars(
                select(TimingProject)
                .where(owner_filter(TimingProject))
                .order_by(TimingProject.created_at, TimingProject.id)
            )
            result = {
                "projects": [self.data(row) for row in rows],
                "default_project_id": default.id,
            }
            session.commit()
            return result

    def save(self, payload, identifier=None):
        with self.database.session() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = self.require(session, identifier) if identifier else None
            if row and row.version != payload.version:
                raise ValueError("耗时项目已被修改，请刷新后重新操作")
            owner = row.owner_id if row else current_owner()
            others = session.scalars(select(TimingProject).where(TimingProject.owner_id == owner))
            if any(
                other.id != identifier and name_key(other.name) == name_key(payload.name)
                for other in others
            ):
                raise ValueError("已有同名耗时项目")
            if row:
                row.name = payload.name
                row.version += 1
                row.updated_at = now_iso()
            else:
                row = TimingProject(owner_id=owner, name=payload.name)
                session.add(row)
            session.flush()
            result = self.data(row)
            session.commit()
            return result
