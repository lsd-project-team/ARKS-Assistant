"""使用 Argon2id 校验密码，随机 Cookie 凭证对应可撤销的服务端会话。"""

import json
import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from threading import RLock
from time import monotonic

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.auth.models import Account, LoginSession, public_account
from app.models import now_iso

COOKIE_NAME = "arks_session"
SESSION_HOURS = 12


def token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, database, paths):
        self.database = database
        self.initial_accounts = paths.data / "auth.initial-accounts.json"
        self.hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
        self.dummy_hash = self.hasher.hash(secrets.token_urlsafe(24))
        self.lock = RLock()
        self.failures: dict[str, tuple[float, int]] = {}

    def initialize(self):
        with self.lock, self.database.session.begin() as session:
            # 重启和恢复备份后旧会话失效，备份中的凭证不能恢复成可用登录状态。
            session.execute(delete(LoginSession))
            if session.scalar(select(Account.id).limit(1)):
                return
            credentials = []
            for username, role, name in (
                ("admin", "admin", "管理员"),
                ("user", "user", "普通用户"),
            ):
                password = secrets.token_urlsafe(24)
                session.add(
                    Account(
                        username=username,
                        display_name=name,
                        role=role,
                        password_hash=self.hasher.hash(password),
                    )
                )
                credentials.append({"username": username, "role": role, "password": password})
            # 初始密码只写入本机文件，不进入响应、日志、Git 或导出备份。
            temporary = self.initial_accounts.with_suffix(".tmp")
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(credentials, file, ensure_ascii=False, indent=2)
            temporary.chmod(0o600)
            temporary.replace(self.initial_accounts)

    def authenticate(self, username: str, password: str, address: str, previous: str = ""):
        with self.lock:
            started, count = self.failures.get(address, (monotonic(), 0))
            if monotonic() - started >= 300:
                started, count = monotonic(), 0
            if count >= 10:
                raise HTTPException(
                    429, "登录尝试过于频繁，请稍后重试", headers={"Retry-After": "300"}
                )
            with self.database.session.begin() as session:
                account = session.scalar(
                    select(Account).where(Account.username == username.casefold())
                )
                try:
                    valid = self.hasher.verify(
                        account.password_hash if account else self.dummy_hash, password
                    )
                except (VerificationError, InvalidHashError):
                    valid = False
                if not valid or not account or not account.enabled:
                    if len(self.failures) >= 2048:
                        self.failures.clear()
                    self.failures[address] = (started, count + 1)
                    raise HTTPException(401, "账号或密码不正确")
                self.failures.pop(address, None)
                if self.hasher.check_needs_rehash(account.password_hash):
                    account.password_hash = self.hasher.hash(password)
                if previous:
                    session.execute(
                        delete(LoginSession).where(LoginSession.token_hash == token_hash(previous))
                    )
                session.execute(delete(LoginSession).where(LoginSession.expires_at <= now_iso()))
                token = secrets.token_urlsafe(32)
                csrf = secrets.token_urlsafe(32)
                expires = (datetime.now(UTC) + timedelta(hours=SESSION_HOURS)).isoformat()
                session.add(
                    LoginSession(
                        token_hash=token_hash(token),
                        account_id=account.id,
                        csrf_token=csrf,
                        expires_at=expires,
                    )
                )
                return token, {"user": public_account(account), "csrf_token": csrf}

    def resolve(self, token: str):
        if not token or len(token) > 128:
            return None
        with self.database.session() as session:
            current = session.get(LoginSession, token_hash(token))
            if not current or current.expires_at <= now_iso():
                return None
            account = session.get(Account, current.account_id)
            if not account or not account.enabled:
                return None
            # 每次读取数据库中的当前角色，撤权后旧 Cookie 不能继续以管理员身份使用。
            return {"user": public_account(account), "csrf_token": current.csrf_token}

    def revoke(self, token: str):
        with self.database.session.begin() as session:
            session.execute(
                delete(LoginSession).where(LoginSession.token_hash == token_hash(token))
            )

    def change_password(self, account_id: str, current_password: str, new_password: str):
        with self.lock, self.database.session.begin() as session:
            account = session.get(Account, account_id)
            if not account or not account.enabled:
                raise HTTPException(401, "请先登录")
            try:
                valid = self.hasher.verify(account.password_hash, current_password)
            except (VerificationError, InvalidHashError):
                valid = False
            if not valid:
                raise HTTPException(400, "当前密码不正确")
            if current_password == new_password:
                raise HTTPException(400, "新密码不能与当前密码相同")
            account.password_hash = self.hasher.hash(new_password)
            # 修改自己的密码后撤销该账号的全部会话，其他账号不受影响。
            session.execute(delete(LoginSession).where(LoginSession.account_id == account.id))
