"""全局项目命名空间下接入交接功能，无需改动旧项目分发器。"""

import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.handover.exports import export_package, package_references, template
from app.handover.imports import MAX_UPLOAD, capture_source, import_source, snapshot_file
from app.handover.labels import FIELDS, KINDS, STATES, VALUES
from app.handover.rules import task_blocks
from app.handover.schemas import PAYLOADS, Action, Write
from app.handover.store import HandoverStore
from app.project_materials import Materials


class Capture(BaseModel):
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


class MaterialCapture(Action):
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
    router = APIRouter(prefix="/api/projects/{project_id}/handover", tags=["handover"])

    def store(project_id):
        return HandoverStore(projects, project_id)

    @router.get("/schema")
    async def schema(project_id: str):
        store(project_id).guard()
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
    async def overview(project_id: str):
        current = store(project_id)
        rows = await asyncio.to_thread(current.list)
        records = {row["id"]: row for row in rows if row["state"] != "archived"}
        blocks = {
            row["id"]: task_blocks(row, records)
            for row in records.values()
            if row["kind"] == "task"
        }
        return {"project_id": project_id, "records": rows, "blocks": blocks}

    @router.post("/records", status_code=201)
    async def create(project_id: str, body: Write):
        if body.kind in {"source", "package", "job", "candidate"}:
            raise ValueError("请使用资料导入、交接包生成或 AI 操作")
        return await asyncio.to_thread(
            store(project_id).create, body.kind, body.title, body.payload, body.actor
        )

    @router.get("/records/{identifier}")
    async def read(
        project_id: str, identifier: str, version: int | None = Query(default=None, ge=1)
    ):
        return await asyncio.to_thread(store(project_id).get, identifier, version)

    @router.patch("/records/{identifier}")
    async def update(project_id: str, identifier: str, body: Write):
        return await asyncio.to_thread(store(project_id).update, identifier, body)

    @router.get("/records/{identifier}/history")
    async def history(project_id: str, identifier: str):
        return await asyncio.to_thread(store(project_id).history, identifier)

    @router.post("/records/{identifier}/{action}")
    async def action(project_id: str, identifier: str, action: str, body: Action):
        return await asyncio.to_thread(store(project_id).action, identifier, action, body)

    @router.get("/events")
    async def events(project_id: str):
        return await asyncio.to_thread(store(project_id).events)

    @router.post("/sources/import", status_code=201)
    async def upload(
        project_id: str,
        request: Request,
        filename: str = Query(min_length=1, max_length=250),
        actor: str = Query(min_length=1, max_length=120),
        provider: str = Query(default="", max_length=2000),
        source_version: str = Query(default="", max_length=2000),
        device: str = Query(default="", max_length=2000),
        supersedes: str = Query(default="", max_length=36),
    ):
        current = store(project_id)
        current.guard(True)
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
                "supersedes": supersedes,
            },
            actor,
        )

    @router.post("/sources/capture", status_code=201)
    async def capture(project_id: str, body: Capture):
        current = store(project_id)
        current.guard(True)
        workspace = projects.services(project_id).workspace
        metadata = body.model_dump(exclude={"actor", "path"})
        return await asyncio.to_thread(
            capture_source, current, workspace, body.path, metadata, body.actor
        )

    @router.post("/sources/material/{material_id}", status_code=201)
    async def capture_material(project_id: str, material_id: str, body: MaterialCapture):
        current = store(project_id)
        current.guard(True)
        material = Materials(projects.database, project_id).read(material_id, body.version)
        metadata = {
            "supersedes": body.supersedes,
            "provider": body.actor,
            "source_version": f"项目资料 {material_id} v{body.version}",
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
    async def original(project_id: str, identifier: str):
        blob = await asyncio.to_thread(store(project_id).blob, identifier)
        return attachment(blob["content"], blob["name"], blob["media_type"])

    @router.get("/sources/{identifier}/file")
    async def file(project_id: str, identifier: str, path: str):
        return await asyncio.to_thread(snapshot_file, store(project_id), identifier, path)

    @router.get("/sources/{identifier}/compare")
    async def compare(project_id: str, identifier: str):
        source = store(project_id).get(identifier)
        if source["kind"] != "source" or not source["payload"]["path"]:
            raise ValueError("此资料不是当前项目源码捕获")
        file = await asyncio.to_thread(
            projects.services(project_id).workspace.read, source["payload"]["path"]
        )
        return {
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
    async def start_ai(project_id: str, body: AIStart):
        return ai.start(store(project_id), body.action, body.record_ids, body.actor)

    @router.post("/ai/{identifier}/cancel")
    async def cancel_ai(project_id: str, identifier: str):
        return await ai.cancel(store(project_id), identifier)

    @router.post("/candidates/{identifier}/promote", status_code=201)
    async def promote(project_id: str, identifier: str, body: Promotion):
        return await asyncio.to_thread(
            store(project_id).promote, identifier, body, body.title, body.proposed
        )

    @router.post("/packages", status_code=201)
    async def package(project_id: str, body: PackageCreate):
        current = store(project_id)
        refs = package_references(current, body.record_ids)
        return current.create(
            "package",
            body.title,
            {"records": refs, "recipient": body.recipient, "scope": body.scope, "gaps": body.gaps},
            body.actor,
        )

    @router.get("/packages/{identifier}/export")
    async def export(
        project_id: str,
        identifier: str,
        format: str = "docx",
        version: int | None = Query(default=None, ge=1),
    ):
        if format not in {"docx", "zip"}:
            raise ValueError("导出格式必须为 docx 或 zip")
        content = await asyncio.to_thread(
            export_package, store(project_id), identifier, format == "zip", version
        )
        media = (
            "application/zip"
            if format == "zip"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        return attachment(content, f"设备软件交接包-{identifier}.{format}", media)

    @router.get("/templates/{kind}")
    async def get_template(project_id: str, kind: str, format: str = "docx"):
        store(project_id).guard()
        if kind not in {"interview", "task", "plan"}:
            raise ValueError("可用模板为访谈、工作项和接续计划")
        if format == "json":
            import json

            content = json.dumps(
                {"kind": kind, "title": KINDS[kind], "payload": PAYLOADS[kind]().model_dump()},
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            return attachment(content, KINDS[kind] + "模板.json", "application/json")
        if format != "docx":
            raise ValueError("模板格式必须为 docx 或 json")
        return attachment(
            template(kind),
            KINDS[kind] + "模板.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @router.post("/templates/import", status_code=201)
    async def import_template(project_id: str, body: Write):
        if body.kind not in {"interview", "task", "plan"}:
            raise ValueError("只支持回填访谈、工作项和接续计划模板")
        payload = {**body.payload, "origin": "human"}
        return await asyncio.to_thread(
            store(project_id).create,
            body.kind,
            body.title,
            payload,
            body.actor,
        )

    return router
