"""独立的全局交接入口；对话项目仅可作为显式选择的资料来源。"""

import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.router import identity, require_admin
from app.handover.debug_issues import DebugIssues, DebugWrite
from app.handover.exports import export_package, package_references
from app.handover.imports import (
    MAX_TEXT,
    MAX_UPLOAD,
    capture_source,
    import_source,
    import_text,
    snapshot_file,
)
from app.handover.labels import FIELDS, KINDS, STATES, VALUES
from app.handover.rules import task_blocks
from app.handover.schemas import PAYLOADS, Action, Write
from app.handover.store import HandoverStore
from app.project_materials import Materials


class Capture(BaseModel):
    source_project_id: str = Field(default="", max_length=32)
    supersedes: str = Field(default="", max_length=36)
    actor: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=2000)
    provider: str = Field(default="", max_length=2000)
    source_version: str = Field(default="", max_length=2000)
    device: str = Field(default="", max_length=2000)


class AIStart(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    action: str
    record_ids: list[str] = Field(min_length=1, max_length=20)


class TextSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=MAX_TEXT)
    actor: str = Field(min_length=1, max_length=120)
    provider: str = Field(default="", max_length=2000)
    source_version: str = Field(default="", max_length=2000)
    device: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=2000)
    supersedes: str = Field(default="", max_length=36)

    @field_validator("title", "actor")
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip():
            raise ValueError("标题和整理人不能为空")
        return value.strip()

    @field_validator("content")
    @classmethod
    def nonblank_content(cls, value):
        if not value.strip():
            raise ValueError("文本内容不能为空")
        return value


class MaterialCapture(Action):
    source_project_id: str = Field(min_length=1, max_length=32)
    supersedes: str = Field(default="", max_length=36)


class Promotion(Action):
    title: str = Field(min_length=1, max_length=200)
    proposed: dict


class PackageCreate(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    record_ids: list[str] = Field(min_length=1, max_length=1000)
    recipient: str = Field(default="", max_length=2000)
    scope: str = Field(default="", max_length=100000)
    gaps: str = Field(default="", max_length=100000)


def attachment(content, filename, media_type):
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


def create_router(projects, ai):
    router = APIRouter(prefix="/api/handover", tags=["handover"])

    def store():
        return HandoverStore(projects)

    def source_workspace(project_id):
        return projects.services(project_id).workspace if project_id else projects.base.workspace

    @router.get("/context")
    async def context():
        return {
            "scope_id": "global",
            "source_root": str(projects.base.workspace.root),
            "knowledge_available": projects.knowledge_available(str(projects.base.workspace.root)),
            "source_projects": [
                {"id": row["id"], "name": row["name"], "source_available": bool(row["source_root"])}
                for row in projects.list()
            ],
        }

    @router.get("/schema")
    async def schema():
        return {
            "kinds": KINDS,
            "fields": FIELDS,
            "states": STATES,
            "values": VALUES,
            "schemas": {
                kind: model.model_json_schema()
                for kind, model in PAYLOADS.items()
                if kind not in {"job", "candidate"}
            },
        }

    @router.get("")
    async def overview():
        current = store()
        rows = await asyncio.to_thread(current.list)
        records = {row["id"]: row for row in rows if row["state"] != "archived"}
        blocks = {
            row["id"]: task_blocks(row, records)
            for row in records.values()
            if row["kind"] == "task"
        }
        return {"scope_id": "global", "records": rows, "blocks": blocks}

    @router.post("/records", status_code=201)
    async def create(body: Write):
        if body.kind in {"source", "package", "job", "candidate", "debug_issue"}:
            raise ValueError("请使用资料导入、交接包生成或 AI 操作")
        return await asyncio.to_thread(
            store().create, body.kind, body.title, body.payload, body.actor
        )

    @router.get("/records/{identifier}")
    async def read(identifier: str, version: int | None = Query(default=None, ge=1)):
        return await asyncio.to_thread(store().get, identifier, version)

    @router.patch("/records/{identifier}")
    async def update(identifier: str, body: Write):
        if body.kind == "debug_issue":
            raise ValueError("请使用调试问题的编辑入口")
        return await asyncio.to_thread(store().update, identifier, body)

    @router.post("/debug-issues", status_code=201)
    async def create_debug_issue(body: DebugWrite, request: Request):
        return await asyncio.to_thread(
            DebugIssues(projects.database, projects).save, body, identity(request)["user"]
        )

    @router.patch("/debug-issues/{identifier}")
    async def update_debug_issue(identifier: str, body: DebugWrite, request: Request):
        if body.version is None:
            raise ValueError("请读取记录当前版本后再保存")
        return await asyncio.to_thread(
            DebugIssues(projects.database, projects).save,
            body,
            identity(request)["user"],
            identifier,
        )

    @router.get("/records/{identifier}/history", dependencies=[Depends(require_admin)])
    async def history(identifier: str):
        return await asyncio.to_thread(store().history, identifier)

    @router.post("/records/{identifier}/{action}")
    async def action(identifier: str, action: str, body: Action, request: Request):
        if action in {"confirm", "reject"}:
            require_admin(request)
        return await asyncio.to_thread(store().action, identifier, action, body)

    @router.get("/events", dependencies=[Depends(require_admin)])
    async def events():
        return await asyncio.to_thread(store().events)

    @router.post("/sources/import", status_code=201)
    async def upload(
        request: Request,
        filename: str = Query(min_length=1, max_length=250),
        actor: str = Query(min_length=1, max_length=120),
        provider: str = Query(default="", max_length=2000),
        source_version: str = Query(default="", max_length=2000),
        device: str = Query(default="", max_length=2000),
        notes: str = Query(default="", max_length=2000),
        supersedes: str = Query(default="", max_length=36),
    ):
        current = store()
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_UPLOAD:
                raise ValueError("附件不能超过 32 MB")
        return await asyncio.to_thread(
            import_source,
            current,
            bytes(data),
            filename,
            {
                "provider": provider,
                "source_version": source_version,
                "device": device,
                "notes": notes,
                "supersedes": supersedes,
            },
            actor,
        )

    @router.post("/sources/text", status_code=201)
    async def add_text(body: TextSourceInput):
        current = store()
        metadata = body.model_dump(exclude={"title", "content", "actor"})
        return await asyncio.to_thread(
            import_text, current, body.title, body.content, metadata, body.actor
        )

    @router.post("/sources/capture", status_code=201)
    async def capture(body: Capture):
        current = store()
        workspace = source_workspace(body.source_project_id)
        metadata = body.model_dump(exclude={"actor", "path"})
        return await asyncio.to_thread(
            capture_source, current, workspace, body.path, metadata, body.actor
        )

    @router.post("/sources/material/{material_id}", status_code=201)
    async def capture_material(material_id: str, body: MaterialCapture):
        current = store()
        projects.get(body.source_project_id)
        material = Materials(projects.database, body.source_project_id).read(
            material_id, body.version
        )
        metadata = {
            "supersedes": body.supersedes,
            "provider": body.actor,
            "source_version": f"项目资料 {material_id} v{body.version}",
            "source_project_id": body.source_project_id,
            "notes": body.opinion,
        }
        return await asyncio.to_thread(
            import_source,
            current,
            material["content"].encode("utf-8"),
            material["title"] + ".txt",
            metadata,
            body.actor,
        )

    @router.get("/sources/{identifier}/original")
    async def original(identifier: str):
        blob = await asyncio.to_thread(store().blob, identifier)
        return attachment(blob["content"], blob["name"], blob["media_type"])

    @router.get("/sources/{identifier}/file")
    async def file(identifier: str, path: str):
        return await asyncio.to_thread(snapshot_file, store(), identifier, path)

    @router.get("/sources/{identifier}/compare")
    async def compare(identifier: str, reader_project_id: str = ""):
        source = store().get(identifier)
        if source["kind"] != "source" or not source["payload"]["path"]:
            raise ValueError("此资料不是源码捕获")
        file = await asyncio.to_thread(
            source_workspace(
                source["payload"].get("source_project_id") or source["source_project_id"]
            ).read,
            source["payload"]["path"],
        )
        reader_matches = False
        if reader_project_id:
            try:
                reader = await asyncio.to_thread(
                    source_workspace(reader_project_id).read, source["payload"]["path"]
                )
                reader_matches = reader["source_workspace_id"] == file["source_workspace_id"]
            except (ValueError, FileNotFoundError):
                pass
        return {
            "reader_matches": reader_matches,
            "changed": file["version"] != source["payload"]["sha256"]
            or bool(
                source["payload"].get("source_workspace_id")
                and file["source_workspace_id"] != source["payload"]["source_workspace_id"]
            ),
            "saved_sha256": source["payload"]["sha256"],
            "current_sha256": file["version"],
            "path": file["path"],
        }

    @router.post("/ai", status_code=201)
    async def start_ai(body: AIStart):
        return ai.start(store(), body.action, body.record_ids, body.actor)

    @router.post("/ai/{identifier}/cancel")
    async def cancel_ai(identifier: str):
        return await ai.cancel(store(), identifier)

    @router.post(
        "/candidates/{identifier}/promote", status_code=201, dependencies=[Depends(require_admin)]
    )
    async def promote(identifier: str, body: Promotion):
        return await asyncio.to_thread(store().promote, identifier, body, body.title, body.proposed)

    @router.post("/packages", status_code=201)
    async def package(body: PackageCreate):
        current = store()
        refs = package_references(current, body.record_ids)
        return current.create(
            "package",
            body.title,
            {"records": refs, "recipient": body.recipient, "scope": body.scope, "gaps": body.gaps},
            body.actor,
        )

    @router.get("/packages/{identifier}/export")
    async def export(
        identifier: str,
        format: str = "docx",
        version: int | None = Query(default=None, ge=1),
    ):
        if format not in {"docx", "zip"}:
            raise ValueError("导出格式必须为 docx 或 zip")
        content = await asyncio.to_thread(
            export_package, store(), identifier, format == "zip", version
        )
        media = (
            "application/zip"
            if format == "zip"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        return attachment(content, f"设备软件交接包-{identifier}.{format}", media)

    return router
