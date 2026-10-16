"""保护所有业务 API；页面上的隐藏状态不承担授权责任。"""

import asyncio
import secrets
import uuid
from urllib.parse import urlparse

from fastapi.responses import JSONResponse

from app.modules.auth.context import request_identity
from app.modules.auth.service import COOKIE_NAME

PUBLIC_PATHS = {"/api/health", "/api/auth/login"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def install_authentication(app, auth, usage=None):
    @app.middleware("http")
    async def authenticate_request(request, call_next):
        path = request.url.path.rstrip("/") or "/"
        origin = request.headers.get("origin")
        if origin and urlparse(origin).hostname not in {"localhost", "127.0.0.1", "::1"}:
            return JSONResponse({"detail": "仅允许本机页面访问"}, status_code=403)
        if not path.startswith("/api/") and path != "/api":
            return await call_next(request)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "不允许跨站访问"}, status_code=403)
        if path not in PUBLIC_PATHS:
            current = await asyncio.to_thread(auth.resolve, request.cookies.get(COOKIE_NAME, ""))
            if not current:
                return JSONResponse(
                    {"detail": "请先登录"}, status_code=401, headers={"Cache-Control": "no-store"}
                )
            request.state.identity = current
            expected_account = request.headers.get("x-arks-account")
            if expected_account and expected_account != current["user"]["id"]:
                return JSONResponse(
                    {"detail": "登录账号已切换，请重新载入"},
                    status_code=401,
                    headers={"Cache-Control": "no-store"},
                )
            if request.method not in SAFE_METHODS and not secrets.compare_digest(
                request.headers.get("x-arks-csrf", ""), current["csrf_token"]
            ):
                return JSONResponse({"detail": "登录校验已失效，请刷新页面"}, status_code=403)
            # 全量备份含复核记录与账号数据，普通用户不能用备份绕过页面限制。
            if path.startswith("/api/backup") and current["user"]["role"] != "admin":
                return JSONResponse({"detail": "仅管理员可访问全量备份"}, status_code=403)
            # 不能通过修改 MCP 命令或服务器配置读取初始密码，再冒充管理员。
            if (
                current["user"]["role"] != "admin"
                and request.method not in SAFE_METHODS
                and (path == "/api/settings" or path.startswith(("/api/settings/", "/api/mcp/")))
            ):
                return JSONResponse({"detail": "仅管理员可调整系统配置"}, status_code=403)
        token = request_identity.set(getattr(request.state, "identity", None))
        try:
            response = await call_next(request)
            if (
                usage
                and getattr(request.state, "identity", None)
                and 200 <= response.status_code < 300
                and request.method not in SAFE_METHODS
            ):
                await asyncio.to_thread(
                    usage.successful_request,
                    request.state.identity["user"],
                    request.method,
                    path,
                    request.headers.get("X-Arks-Submission-ID", str(uuid.uuid4()))[:128],
                )
        finally:
            request_identity.reset(token)
        response.headers["Cache-Control"] = "no-store"
        return response
