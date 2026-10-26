"""用户台账接口；复用现有会话、CSRF及项目路由。"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.modules.action_timing.ledger import ActionLedger
from app.modules.action_timing.ledger_files import MEDIA
from app.modules.action_timing.ledger_schemas import (
    MAX_FILE_BYTES,
    ActionInput,
    ActionSort,
    ActionUpdate,
    CategoryDelete,
    CategoryInput,
    CategoryUpdate,
    DuplicateMode,
    DurationStatus,
    ImportCommit,
    ImportUnit,
)
from app.modules.action_timing.ledger_transfer import LedgerTransfer


def create_router(services):
    router = APIRouter(prefix="/ledger")
    ledger = ActionLedger(services)
    transfer = LedgerTransfer(ledger)

    @router.get("")
    def listing(
        category_id: str = Query("", max_length=36),
        search: str = Query("", max_length=120),
        duration_status: DurationStatus = "all",
        sort: ActionSort = "name",
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        return ledger.listing(category_id, search, duration_status, limit, offset, sort)

    @router.post("/categories", status_code=201)
    def create_category(payload: CategoryInput):
        return ledger.save_category(payload)

    @router.patch("/categories/{identifier}")
    def update_category(identifier: str, payload: CategoryUpdate):
        return ledger.save_category(payload, identifier)

    @router.delete("/categories/{identifier}")
    def delete_category(identifier: str, payload: CategoryDelete):
        return ledger.delete_category(identifier, payload)

    @router.post("/actions", status_code=201)
    def create_action(payload: ActionInput):
        return ledger.save_action(payload)

    @router.patch("/actions/{identifier}")
    def update_action(identifier: str, payload: ActionUpdate):
        return ledger.save_action(payload, identifier)

    @router.delete("/actions/{identifier}")
    def delete_action(identifier: str, version: int = Query(ge=1)):
        return ledger.delete_action(identifier, version)

    @router.post("/import-preview")
    async def preview(
        request: Request,
        filename: str = Query(max_length=255),
        mode: DuplicateMode = "skip",
        unit: ImportUnit = "auto",
    ):
        with ledger.transaction() as (_session, _scope):
            pass
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_FILE_BYTES:
                raise HTTPException(413, "文件超过5MiB，请分批导入")
            raw.extend(chunk)
        # 文件解析与数据库工作交给线程，不阻塞其余用户请求。
        from starlette.concurrency import run_in_threadpool

        try:
            return await run_in_threadpool(transfer.preview, bytes(raw), filename, mode, unit)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.post("/imports")
    def import_rows(payload: ImportCommit):
        return transfer.commit(payload)

    @router.get("/export")
    def export(
        format: Literal["csv", "xlsx"] = "xlsx",
        category_id: str = Query("", max_length=36),
        search: str = Query("", max_length=120),
        duration_status: DurationStatus = "all",
        sort: ActionSort = "name",
        template: bool = False,
        template_unit: Literal["s", "ms"] = "s",
    ):
        filename = "action-timing-template" if template else "action-timing"
        return Response(
            transfer.export(
                format, category_id, search, duration_status, template, sort, template_unit
            ),
            media_type=MEDIA[format],
            headers={"Content-Disposition": f'attachment; filename="{filename}.{format}"'},
        )

    return router
