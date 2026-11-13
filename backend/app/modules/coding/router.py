"""项目编码工作区 API：文件、检查点、命令、审批和后台任务。"""

import asyncio
from typing import Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.modules.auth.router import require_admin


class SettingsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_mode: str | None = Field(default=None, pattern="^(allowlist|confirm|full)$")
    permission: str | None = Field(
        default=None, pattern="^(read-only|workspace-write|full-access)$"
    )
    timeout_seconds: int | None = Field(default=None, ge=10, le=900)
    build_command: str | None = Field(default=None, max_length=500)
    test_command: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


class FileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=2_000_000)
    expected_hash: str = Field(default="", max_length=64)


class FileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    old: str = Field(min_length=1, max_length=100_000)
    new: str = Field(default="", max_length=100_000)
    replace_all: bool = False


class FileEdits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=500)
    edits: list[FileEdit] = Field(min_length=1, max_length=100)
    expected_hash: str = Field(min_length=1, max_length=64)


class BinaryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=500)
    content_base64: str = Field(max_length=20_000_000)
    expected_hash: str = Field(default="", max_length=64)


class CommandWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = Field(min_length=1, max_length=2000)
    cwd: str = Field(default=".", max_length=500)
    timeout: int = Field(default=120, ge=5, le=900)
    approved: bool = False


class RestoreWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commit: str = Field(min_length=7, max_length=40)
    paths: list[str] = Field(default_factory=list, max_length=200)


class RestoreRunWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str = Field(min_length=1, max_length=64)


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool
    scope: Literal["once", "session"] = "once"


def create_router(services):
    router = APIRouter()
    coding = services.runtime.coding
    repository = services.runtime.repository

    @router.get("/api/coding/settings")
    async def get_settings():
        return coding.settings()

    @router.put("/api/coding/settings")
    async def set_settings(body: SettingsWrite, request: Request):
        require_admin(request)
        return coding.save_settings(body.model_dump(exclude_none=True))

    @router.get("/api/coding/tree")
    async def tree(
        path: str = Query(default=".", max_length=500), depth: int = Query(default=2, ge=1, le=5)
    ):
        return await asyncio.to_thread(coding.list_files, path, depth)

    @router.get("/api/coding/file")
    async def file(
        path: str = Query(min_length=1, max_length=500),
        start_line: int = Query(default=1, ge=1),
        end_line: int = Query(default=400, ge=1),
    ):
        return await asyncio.to_thread(coding.read_file, path, start_line, end_line)

    @router.get("/api/coding/search")
    async def search(
        query: str = Query(min_length=1, max_length=200),
        path: str = Query(default=".", max_length=500),
        glob: str = Query(default="", max_length=100),
    ):
        return await asyncio.to_thread(coding.search_files, query, path, glob)

    @router.get("/api/coding/find")
    async def find(
        pattern: str = Query(min_length=1, max_length=200),
        path: str = Query(default=".", max_length=500),
        limit: int = Query(default=100, ge=1, le=500),
    ):
        return await asyncio.to_thread(coding.find_files, pattern, path, limit)

    @router.put("/api/coding/file")
    async def write(body: FileWrite):
        return await asyncio.to_thread(
            coding.write_file, body.path, body.content, body.expected_hash
        )

    @router.patch("/api/coding/file")
    async def edit(body: FileEdits):
        return await asyncio.to_thread(
            coding.edit_file,
            body.path,
            [row.model_dump() for row in body.edits],
            body.expected_hash,
        )

    @router.put("/api/coding/binary")
    async def write_binary(body: BinaryWrite):
        return await asyncio.to_thread(
            coding.write_binary, body.path, body.content_base64, body.expected_hash
        )

    @router.get("/api/coding/checkpoints")
    async def checkpoints(limit: int = Query(default=20, ge=1, le=200)):
        return await asyncio.to_thread(coding.checkpoints, limit)

    @router.get("/api/coding/diff")
    async def diff(
        base: str = Query(default="", max_length=40),
        head: str = Query(default="", max_length=40),
        path: str = Query(default="", max_length=500),
        commit: str = Query(default="", max_length=40),
    ):
        paths = [path] if path else None
        return await asyncio.to_thread(coding.diff, base, head, paths, commit)

    @router.post("/api/coding/restore")
    async def restore(body: RestoreWrite):
        return await asyncio.to_thread(coding.restore, body.commit, body.paths or None)

    @router.post("/api/coding/restore-run")
    async def restore_run(body: RestoreRunWrite):
        payload = await asyncio.to_thread(_coding_changes, repository, body.run_id)
        if not payload:
            raise ValueError("本轮没有可撤销的修改")
        return await asyncio.to_thread(
            coding.restore_run, payload["base"], payload["files"], payload["head"]
        )

    @router.post("/api/coding/command")
    async def command(body: CommandWrite):
        return await asyncio.to_thread(
            coding.run_command,
            body.command,
            body.cwd,
            body.timeout,
            body.approved,
            wait=False,
        )

    @router.post("/api/coding/process")
    async def start_process(body: CommandWrite):
        return await asyncio.to_thread(
            coding.start_process, body.command, body.cwd, body.approved, wait=False
        )

    @router.get("/api/coding/process/{job_id}")
    async def read_process(job_id: str, lines: int = Query(default=80, ge=1, le=1000)):
        return await asyncio.to_thread(coding.read_process, job_id, lines)

    @router.get("/api/coding/jobs")
    async def jobs(limit: int = Query(default=30, ge=1, le=100)):
        return await asyncio.to_thread(coding.list_jobs, limit)

    @router.delete("/api/coding/process/{job_id}")
    async def stop_process(job_id: str):
        return await asyncio.to_thread(coding.stop_process, job_id)

    @router.get("/api/coding/approvals")
    async def approvals(recent: bool = Query(default=False)):
        if recent:
            return {"approvals": await asyncio.to_thread(coding.recent_approvals)}
        return {"approvals": await asyncio.to_thread(coding.list_approvals)}

    @router.get("/api/coding/approvals/{approval_id}")
    async def approval(approval_id: str):
        return await asyncio.to_thread(coding.approval, approval_id)

    @router.post("/api/coding/approvals/{approval_id}")
    async def decide_approval(approval_id: str, body: ApprovalDecision):
        return await asyncio.to_thread(
            coding.decide_approval, approval_id, body.approved, body.scope
        )

    @router.get("/api/coding/audit")
    async def audit(request: Request, limit: int = Query(default=50, ge=1, le=500)):
        require_admin(request)
        return {"rows": await asyncio.to_thread(coding.list_audit, limit)}

    return router


def _coding_changes(repository, run_id):
    repository.run(run_id)
    latest = None
    cursor = 0
    while True:
        events = repository.events(run_id, cursor)
        for event in events:
            if event["kind"] == "coding_changes":
                latest = event["payload"]
        if len(events) < 500:
            break
        cursor = events[-1]["sequence"]
    return latest
