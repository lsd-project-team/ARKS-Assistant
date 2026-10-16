"""账号变更及会话撤销在同一事务中完成，保留最后一个有效管理员。"""

from sqlalchemy import delete, func, select

from app.core.identifiers import now_iso
from app.modules.admin.models import AdminEvent
from app.modules.auth.models import Account, LoginSession, public_account


class AccountAdministration:
    def __init__(self, auth):
        self.auth = auth

    def list(self):
        with self.auth.database.session() as session:
            rows = session.scalars(select(Account).order_by(Account.created_at))
            return [
                {
                    **public_account(row),
                    "enabled": row.enabled,
                    "created_at": row.created_at,
                    "sessions": session.scalar(
                        select(func.count())
                        .select_from(LoginSession)
                        .where(
                            LoginSession.account_id == row.id, LoginSession.expires_at > now_iso()
                        )
                    ),
                }
                for row in rows
            ]

    def save(self, actor, body, identifier=None):
        with self.auth.lock, self.auth.database.session.begin() as session:
            row = session.get(Account, identifier) if identifier else None
            if identifier and not row:
                raise FileNotFoundError("账号不存在")
            if row and body.username is not None and body.username.casefold() != row.username:
                raise ValueError("账号名称不能修改，请编辑显示姓名")
            if not row:
                if not body.username or not body.password:
                    raise ValueError("新增账号需要账号名称和初始密码")
                if session.scalar(
                    select(Account.id).where(Account.username == body.username.casefold())
                ):
                    raise ValueError("账号名称已存在")
                row = Account(
                    username=body.username.casefold(),
                    display_name=body.display_name.strip(),
                    role=body.role,
                    enabled=body.enabled,
                    password_hash=self.auth.hasher.hash(body.password),
                )
                session.add(row)
                session.flush()
                action = "新增账号"
            else:
                if (
                    row.role == "admin"
                    and row.enabled
                    and (body.role != "admin" or not body.enabled)
                ):
                    admins = session.scalar(
                        select(func.count())
                        .select_from(Account)
                        .where(Account.role == "admin", Account.enabled.is_(True))
                    )
                    if admins <= 1:
                        raise ValueError("不能禁用或降级最后一个有效管理员")
                row.display_name, row.role, row.enabled = (
                    body.display_name.strip(),
                    body.role,
                    body.enabled,
                )
                if body.password:
                    row.password_hash = self.auth.hasher.hash(body.password)
                session.execute(delete(LoginSession).where(LoginSession.account_id == row.id))
                action = "修改账号并撤销会话"
            session.add(
                AdminEvent(
                    actor=actor["username"],
                    action=action,
                    target=row.username,
                    detail=f"角色：{row.role}；状态：{'启用' if row.enabled else '禁用'}",
                )
            )
            session.flush()
            return {**public_account(row), "enabled": row.enabled}

    def revoke(self, actor, identifier):
        with self.auth.lock, self.auth.database.session.begin() as session:
            row = session.get(Account, identifier)
            if not row:
                raise FileNotFoundError("账号不存在")
            session.execute(delete(LoginSession).where(LoginSession.account_id == identifier))
            session.add(
                AdminEvent(actor=actor["username"], action="撤销登录会话", target=row.username)
            )
        return {"ok": True}
