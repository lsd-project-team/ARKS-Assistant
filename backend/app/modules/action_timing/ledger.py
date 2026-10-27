"""按独立耗时项目维护台账；短事务与版本号防止并发覆盖。"""

import hashlib
import json
from collections import Counter
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.identifiers import now_iso
from app.modules.action_timing.ledger_schemas import name_key
from app.modules.action_timing.models import TimingAction, TimingCategory
from app.modules.action_timing.projects import TimingProjects


class ActionLedger:
    def __init__(self, services, timing_project_id=None):
        self.database = services.database
        self.project_id = timing_project_id

    def scope(self, session, *, writing=False):
        project = (
            TimingProjects.require(session, self.project_id)
            if self.project_id
            else TimingProjects.default(session)
        )
        return project.id

    @contextmanager
    def transaction(self, *, writing=False):
        with self.database.session() as session:
            try:
                # SQLite 写锁覆盖读取版本至提交，避免校验与写入之间出现竞争。
                session.connection().exec_driver_sql(
                    "BEGIN IMMEDIATE" if writing or not self.project_id else "BEGIN"
                )
                scope = self.scope(session, writing=writing)
                yield session, scope
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise ValueError("同一分类内的动作名称或分类名称重复，请刷新后重试") from error

    @staticmethod
    def load(session, scope):
        categories = list(
            session.scalars(select(TimingCategory).where(TimingCategory.scope_id == scope))
        )
        actions = list(session.scalars(select(TimingAction).where(TimingAction.scope_id == scope)))
        return categories, actions

    @staticmethod
    def category_data(row, count=0):
        return {"id": row.id, "name": row.name, "version": row.version, "count": count}

    @staticmethod
    def action_data(row, names):
        return {
            "id": row.id,
            "name": row.name,
            "category_id": row.category_id,
            "category": names.get(row.category_id, "未分类"),
            "duration_seconds": row.duration_seconds,
            "notes": row.notes,
            "version": row.version,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def revision(categories, actions):
        state = {
            "categories": sorted((row.id, row.version, row.name) for row in categories),
            "actions": sorted((row.id, row.version) for row in actions),
        }
        return hashlib.sha256(json.dumps(state, ensure_ascii=False).encode()).hexdigest()

    def listing(
        self, category_id="", search="", duration_status="all", limit=20, offset=0, sort="name"
    ):
        with self.transaction() as (session, scope):
            categories, actions = self.load(session, scope)
            names = {row.id: row.name for row in categories}
            counts = Counter(row.category_id for row in actions)
            items = [self.action_data(row, names) for row in actions]
            items = self.filter_items(items, category_id, search, duration_status, sort)
            return {
                "items": items[offset : offset + limit] if limit is not None else items,
                "total": len(items),
                "action_count": len(actions),
                "uncategorized_count": counts[None],
                "categories": [
                    self.category_data(row, counts[row.id])
                    for row in sorted(categories, key=lambda row: (row.name_key, row.id))
                ],
                "revision": self.revision(categories, actions),
                "writable": True,
            }

    @staticmethod
    def filter_items(items, category_id, search, duration_status, sort="name"):
        needle = name_key(search)

        def order(row):
            identity = (name_key(row["category"]), name_key(row["name"]), row["id"])
            if sort == "name":
                return identity
            duration = row["duration_seconds"]
            value = 0 if duration is None else duration
            # 未填写始终排在最后，实际零值参与排序；同耗时使用稳定次序跨页展示。
            return (duration is None, -value if sort == "duration_desc" else value, *identity)

        return sorted(
            (
                row
                for row in items
                if (not category_id or (row["category_id"] or "uncategorized") == category_id)
                and (not needle or needle in name_key(row["name"]))
                and (duration_status != "filled" or row["duration_seconds"] is not None)
                and (duration_status != "missing" or row["duration_seconds"] is None)
            ),
            key=order,
        )

    @staticmethod
    def require(session, model, identifier, scope):
        row = session.get(model, identifier)
        if not row or row.scope_id != scope:
            raise FileNotFoundError("分类或动作不存在")
        return row

    @staticmethod
    def check_version(row, version):
        if row.version != version:
            raise ValueError("该记录已被修改，请刷新后重新操作")

    def save_category(self, payload, identifier=None):
        with self.transaction(writing=True) as (session, scope):
            if identifier:
                row = self.require(session, TimingCategory, identifier, scope)
                self.check_version(row, payload.version)
                row.version += 1
            else:
                row = TimingCategory(scope_id=scope)
                session.add(row)
            row.name, row.name_key = payload.name, name_key(payload.name)
            session.flush()
            return self.category_data(row)

    def delete_category(self, identifier, payload):
        with self.transaction(writing=True) as (session, scope):
            category = self.require(session, TimingCategory, identifier, scope)
            self.check_version(category, payload.version)
            if payload.target_id == identifier:
                raise ValueError("请选择其他分类或未分类")
            if payload.target_id:
                self.require(session, TimingCategory, payload.target_id, scope)
            rows = list(
                session.scalars(select(TimingAction).where(TimingAction.category_id == identifier))
            )
            for row in rows:
                row.category_id = payload.target_id
                row.version += 1
                row.updated_at = now_iso()
            # 先移动动作；目标存在同名动作时整笔回滚，保留原分类与数据。
            session.flush()
            session.delete(category)
            session.flush()
            return {"deleted": identifier, "moved": len(rows)}

    def save_action(self, payload, identifier=None):
        with self.transaction(writing=True) as (session, scope):
            if payload.category_id:
                self.require(session, TimingCategory, payload.category_id, scope)
            if identifier:
                row = self.require(session, TimingAction, identifier, scope)
                self.check_version(row, payload.version)
                row.version += 1
            else:
                row = TimingAction(scope_id=scope)
                session.add(row)
            self.assign_action(
                row, payload.name, payload.category_id, payload.duration_seconds, payload.notes
            )
            session.flush()
            category = session.get(TimingCategory, row.category_id) if row.category_id else None
            return self.action_data(row, {category.id: category.name} if category else {})

    @staticmethod
    def assign_action(row, name, category_id, duration, notes):
        row.name, row.name_key = name, name_key(name)
        row.category_id, row.duration_seconds, row.notes = category_id, duration, notes
        row.updated_at = now_iso()

    def delete_action(self, identifier, version):
        with self.transaction(writing=True) as (session, scope):
            row = self.require(session, TimingAction, identifier, scope)
            self.check_version(row, version)
            session.delete(row)
            return {"deleted": identifier}
