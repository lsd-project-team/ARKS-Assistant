"""管理 API 全部由服务端校验管理员身份。"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from app.infrastructure.database.serialization import record_dict
from app.modules.admin.accounts import AccountAdministration
from app.modules.admin.models import AdminEvent
from app.modules.admin.questions import QuestionRecords
from app.modules.auth.router import identity, require_admin


class AccountInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str | None = Field(
        default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    display_name: str = Field(min_length=1, max_length=120)
    role: Literal["admin", "user"] = "user"
    enabled: bool = True
    password: str | None = Field(default=None, min_length=12, max_length=256)

    @field_validator("display_name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("姓名不能为空")
        return value.strip()


class Heartbeat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visit_id: UUID
    sequence: int = Field(ge=1, le=2147483647)
    active_ms: int = Field(ge=0, le=15000)


def create_router(auth, usage):
    router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])
    accounts = AccountAdministration(auth)
    questions = QuestionRecords(auth.database)

    @router.get("/overview")
    def overview(period: Literal["7", "30", "all"] = "7"):
        return usage.overview(period)

    @router.get("/accounts")
    def list_accounts():
        return accounts.list()

    @router.post("/accounts", status_code=201)
    def add_account(body: AccountInput, request: Request):
        return accounts.save(identity(request)["user"], body)

    @router.patch("/accounts/{identifier}")
    def edit_account(identifier: str, body: AccountInput, request: Request):
        return accounts.save(identity(request)["user"], body, identifier)

    @router.post("/accounts/{identifier}/revoke")
    def revoke(identifier: str, request: Request):
        return accounts.revoke(identity(request)["user"], identifier)

    @router.get("/questions")
    def list_questions(
        query: str = Query("", max_length=300),
        user_id: str = "",
        project_id: str = "",
        status: Literal[
            "", "queued", "running", "completed", "failed", "cancelled", "interrupted"
        ] = "",
        after: datetime | None = None,
        before: datetime | None = None,
        limit: int = Query(30, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        return questions.list(query, user_id, project_id, status, after, before, limit, offset)

    @router.get("/questions/{identifier}")
    def question_detail(
        identifier: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200)
    ):
        return questions.detail(identifier, offset, limit)

    @router.get("/events")
    def events(offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
        with auth.database.session() as session:
            return [
                record_dict(row)
                for row in session.scalars(
                    select(AdminEvent)
                    .order_by(AdminEvent.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
            ]

    return router


def usage_router(usage):
    router = APIRouter(prefix="/api/usage")

    @router.post("/heartbeat")
    def heartbeat(body: Heartbeat, request: Request):
        return usage.heartbeat(identity(request)["user"], body)

    return router
