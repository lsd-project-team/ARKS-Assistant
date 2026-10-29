"""聊天共用的项目模型日额度；原子预留和结算独立于代码修改功能。"""

import json
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert

from app.core.identifiers import new_id, now_iso
from app.infrastructure.database.legacy_code_work import (
    ModelBudgetPolicy,
    ModelBudgetReservation,
    ModelBudgetUsage,
)


class ModelLimit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token_limit: int | None = Field(default=500000, ge=1000, le=100_000_000)


class ModelLedger:
    def __init__(self, database, project_id):
        self.database, self.project = database, project_id

    @property
    def project_id(self):
        return str(self.project() if callable(self.project) else self.project)

    def get(self):
        with self.database.session() as session:
            row = session.get(ModelBudgetPolicy, self.project_id)
            payload = json.loads(row.payload_json) if row else {}
        # 旧键只用于兼容既有额度，旧磁盘/执行策略不再参与任何运行。
        return ModelLimit(
            token_limit=payload.get("token_limit", payload.get("reading_token_limit", 500000))
        )

    def save(self, payload):
        limit = ModelLimit.model_validate(payload)
        with self.database.session.begin() as session:
            row = session.get(ModelBudgetPolicy, self.project_id)
            if row is None:
                row = ModelBudgetPolicy(project_id=self.project_id)
                session.add(row)
            row.payload_json, row.updated_at = limit.model_dump_json(), now_iso()
        return limit.model_dump()

    @staticmethod
    def day():
        # 项目日额度统一按UTC结算，前端说明口径，避免迁移服务器后时区改变重置边界。
        return datetime.now(UTC).date().isoformat()

    def tokens(self):
        day, project = self.day(), self.project_id
        with self.database.session() as session:
            row = session.get(ModelBudgetUsage, (project, day))
            return {
                "day": day,
                "reserved_tokens": row.reserved_tokens if row else 0,
                "actual_tokens": row.actual_tokens if row else 0,
                "calls": row.calls if row else 0,
            }

    def reserve(self, maximum):
        if type(maximum) is not int or maximum <= 0:
            raise ValueError("模型额度预留必须是正整数")
        limit, day, identifier = self.get().token_limit, self.day(), new_id()
        project = self.project_id
        with self.database.session.begin() as session:
            session.execute(
                insert(ModelBudgetUsage)
                .values(project_id=project, day=day, reserved_tokens=0, actual_tokens=0, calls=0)
                .on_conflict_do_nothing()
            )
            claim = update(ModelBudgetUsage).where(
                ModelBudgetUsage.project_id == project,
                ModelBudgetUsage.day == day,
            )
            # 无上限仅跳过额度拦截；用量仍原子累计，保留结算和跨项目边界。
            if limit is not None:
                claim = claim.where(ModelBudgetUsage.reserved_tokens + maximum <= limit)
            claimed = session.execute(
                claim.values(
                    reserved_tokens=ModelBudgetUsage.reserved_tokens + maximum,
                    calls=ModelBudgetUsage.calls + 1,
                )
            )
            if claimed.rowcount != 1:
                raise ValueError("本项目当日模型Token预算不足；进度已保留，请提高额度或次日继续")
            session.add(
                ModelBudgetReservation(
                    id=identifier, project_id=project, day=day, reserved_tokens=maximum
                )
            )
        return {"id": identifier, "day": day, "maximum": maximum, "project_id": project}

    def settle(self, reservation, actual_tokens):
        if actual_tokens is None:
            return  # 供应商未给用量或调用异常时保留预留，不能把未知费用当成零。
        if type(actual_tokens) is not int or actual_tokens < 0:
            raise ValueError("供应商用量必须是非负整数")
        project = self.project_id
        with self.database.session.begin() as session:
            receipt = session.get(ModelBudgetReservation, reservation["id"])
            if receipt is None or receipt.project_id != project:
                raise ValueError("模型额度预留不属于当前项目")
            claimed = session.execute(
                update(ModelBudgetReservation)
                .where(
                    ModelBudgetReservation.id == receipt.id,
                    ModelBudgetReservation.actual_tokens.is_(None),
                )
                .values(actual_tokens=actual_tokens)
            )
            if claimed.rowcount != 1:
                return  # 重复回调只结算一次，不能重复退款绕过日额度。
            session.execute(
                update(ModelBudgetUsage)
                .where(
                    ModelBudgetUsage.project_id == project,
                    ModelBudgetUsage.day == receipt.day,
                )
                .values(
                    reserved_tokens=ModelBudgetUsage.reserved_tokens
                    - receipt.reserved_tokens
                    + actual_tokens,
                    actual_tokens=ModelBudgetUsage.actual_tokens + actual_tokens,
                )
            )
