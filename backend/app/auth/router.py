"""认证 API 只返回当前身份和 CSRF 令牌，不返回密码或 Cookie 凭证。"""

import asyncio

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.auth.service import COOKIE_NAME


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=6, max_length=256)
    confirm_password: str = Field(min_length=6, max_length=256)


def identity(request: Request) -> dict:
    current = getattr(request.state, "identity", None)
    if not current:
        raise HTTPException(401, "请先登录")
    return current


def require_admin(request: Request):
    current = identity(request)
    if current["user"]["role"] != "admin":
        raise HTTPException(403, "当前功能仅管理员可用")
    return current


def create_router(auth, projects=None) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/login")
    async def login(body: Credentials, request: Request, response: Response):
        token, current = await asyncio.to_thread(
            auth.authenticate,
            body.username,
            body.password,
            request.client.host if request.client else "unknown",
            request.cookies.get(COOKIE_NAME, ""),
        )
        if projects:
            await asyncio.to_thread(projects.account_defaults.ensure, current["user"])
        response.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return current

    @router.get("/session")
    async def session(request: Request, response: Response):
        response.headers["Cache-Control"] = "no-store"
        return identity(request)

    @router.post("/logout", status_code=204)
    async def logout(request: Request, response: Response):
        await asyncio.to_thread(auth.revoke, request.cookies.get(COOKIE_NAME, ""))
        response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict")

    @router.post("/password", status_code=204)
    async def password(body: PasswordChange, request: Request, response: Response):
        if body.new_password != body.confirm_password:
            raise HTTPException(400, "两次新密码不一致")
        # 账号只能取自服务端会话，不能由表单指定其他用户。
        await asyncio.to_thread(
            auth.change_password,
            identity(request)["user"]["id"],
            body.current_password,
            body.new_password,
        )
        response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict")

    return router
