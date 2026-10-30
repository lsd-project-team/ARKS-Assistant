"""独立耗时项目与台账接口；复用会话和CSRF，不经过聊天项目分派。"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

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
    TimingProjectInput,
    TimingProjectUpdate,
)
from app.modules.action_timing.ledger_transfer import LedgerTransfer
from app.modules.action_timing.projects import TimingProjects


def create_router(services):
    router = APIRouter(prefix="/api/action-timing", tags=["action-timing-ledger"])
    projects = TimingProjects(services.database)

    def selected_ledger(timing_project: str | None = Query(None, min_length=1, max_length=160)):
        return ActionLedger(services, timing_project)

    selected = Annotated[ActionLedger, Depends(selected_ledger)]

    @router.get("/projects")
    def list_projects():
        return projects.listing()

    @router.post("/projects", status_code=201)
    def create_project(payload: TimingProjectInput):
        return projects.save(payload)

    @router.patch("/projects/{identifier}")
    def rename_project(identifier: str, payload: TimingProjectUpdate):
        return projects.save(payload, identifier)

    @router.get("/ledger")
    def listing(
        ledger: selected,
        category_id: str = Query("", max_length=36),
        search: str = Query("", max_length=120),
        duration_status: DurationStatus = "all",
        sort: ActionSort = "name",
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        return ledger.listing(category_id, search, duration_status, limit, offset, sort)

    @router.post("/ledger/categories", status_code=201)
    def create_category(payload: CategoryInput, ledger: selected):
        return ledger.save_category(payload)

    @router.patch("/ledger/categories/{identifier}")
    def update_category(identifier: str, payload: CategoryUpdate, ledger: selected):
        return ledger.save_category(payload, identifier)

    @router.delete("/ledger/categories/{identifier}")
    def delete_category(identifier: str, payload: CategoryDelete, ledger: selected):
        return ledger.delete_category(identifier, payload)

    @router.post("/ledger/actions", status_code=201)
    def create_action(payload: ActionInput, ledger: selected):
        return ledger.save_action(payload)

    @router.patch("/ledger/actions/{identifier}")
    def update_action(identifier: str, payload: ActionUpdate, ledger: selected):
        return ledger.save_action(payload, identifier)

    @router.delete("/ledger/actions/{identifier}")
    def delete_action(identifier: str, ledger: selected, version: int = Query(ge=1)):
        return ledger.delete_action(identifier, version)

    @router.post("/ledger/import-preview")
    async def preview(
        request: Request,
        ledger: selected,
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
            return await run_in_threadpool(
                LedgerTransfer(ledger).preview, bytes(raw), filename, mode, unit
            )
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.post("/ledger/imports")
    def import_rows(payload: ImportCommit, ledger: selected):
        return LedgerTransfer(ledger).commit(payload)

    @router.get("/ledger/export")
    def export(
        ledger: selected,
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
            LedgerTransfer(ledger).export(
                format, category_id, search, duration_status, template, sort, template_unit
            ),
            media_type=MEDIA[format],
            headers={"Content-Disposition": f'attachment; filename="{filename}.{format}"'},
        )

    return router
