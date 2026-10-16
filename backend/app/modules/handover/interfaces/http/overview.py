"""交接工作台 overview 接口。"""

import asyncio

from fastapi import APIRouter

from app.modules.handover.application.records import RecordService
from app.modules.handover.domain.labels import FIELDS, KINDS, STATES, VALUES
from app.modules.handover.domain.schemas import PAYLOADS
from app.modules.handover.interfaces.http.context import HandoverHTTPContext


def register(router: APIRouter, ctx: HandoverHTTPContext):
    store = ctx.repository_factory
    projects = ctx.projects

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
        return await asyncio.to_thread(RecordService(store()).overview)
