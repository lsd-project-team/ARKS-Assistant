"""交接路由装配；地址和权限保持现有协议。"""

from fastapi import APIRouter

from app.modules.handover.interfaces.http import (
    candidates,
    debug_issues,
    materials,
    overview,
    packages,
    records,
    reviews,
)
from app.modules.handover.interfaces.http.context import HandoverHTTPContext


def create_router(projects, ai, repository_factory, parser, exporter):
    router = APIRouter(prefix="/api/handover", tags=["handover"])
    context = HandoverHTTPContext(projects, ai, repository_factory, parser, exporter)
    for module in (overview, records, debug_issues, reviews, materials, candidates, packages):
        module.register(router, context)
    return router
