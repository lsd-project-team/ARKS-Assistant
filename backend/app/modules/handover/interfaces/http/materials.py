"""交接工作台 materials 接口。"""

import asyncio

from fastapi import APIRouter, Query, Request

from app.modules.handover.application.materials import (
    capture_source,
    import_source,
    import_text,
    snapshot_file,
)
from app.modules.handover.domain.materials import MAX_UPLOAD
from app.modules.handover.interfaces.http.context import HandoverHTTPContext
from app.modules.handover.interfaces.http.responses import attachment
from app.modules.handover.interfaces.http.schemas import (
    Capture,
    MaterialCapture,
    TextSourceInput,
)
from app.modules.projects.materials import Materials


def register(router: APIRouter, ctx: HandoverHTTPContext):
    store = ctx.repository_factory
    projects = ctx.projects
    source_workspace = ctx.source_workspace

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
            ctx.parser,
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
            ctx.parser,
        )

    @router.get("/sources/{identifier}/original")
    async def original(identifier: str):
        blob = await asyncio.to_thread(store().blob, identifier)
        return attachment(blob["content"], blob["name"], blob["media_type"])

    @router.get("/sources/{identifier}/file")
    async def file(identifier: str, path: str):
        return await asyncio.to_thread(snapshot_file, store(), identifier, path, ctx.parser)

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
