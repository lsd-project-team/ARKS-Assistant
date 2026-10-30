"""本机管理员命令；管理界面未设计前用交互式输入维护账号，不暴露公开注册。"""

import sys
from pathlib import Path

_SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_SCRIPT_ROOT / "backend"), str(_SCRIPT_ROOT)]

import argparse
import getpass
import re

from alembic import command
from alembic.config import Config
from app.core.config import PROJECT_ROOT, Paths
from app.infrastructure.database.session import Database
from app.modules.auth.models import Account, LoginSession, public_account
from app.modules.auth.service import AuthService
from sqlalchemy import delete, select


def new_password():
    password = getpass.getpass("新密码（至少 12 个字符）：")
    if len(password) < 12 or len(password) > 256:
        raise ValueError("密码长度应为 12–256 个字符")
    if getpass.getpass("再次输入新密码：") != password:
        raise ValueError("两次密码不一致")
    return password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["list", "add", "password", "role", "disable", "enable"]
    )
    parser.add_argument("username", nargs="?")
    parser.add_argument("--role", choices=["admin", "user"])
    parser.add_argument("--name")
    args = parser.parse_args()
    paths = Paths()
    database = Database(paths.data / "app.sqlite3")
    auth = AuthService(database, paths)
    migration = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
    migration.attributes["connection"] = database.engine
    command.upgrade(migration, "head")
    try:
        with database.session.begin() as session:
            if args.action == "list":
                for account in session.scalars(
                    select(Account).order_by(Account.username)
                ):
                    print({**public_account(account), "enabled": account.enabled})
                return
            if not args.username or not re.fullmatch(
                r"[A-Za-z0-9_.-]{1,64}", args.username
            ):
                raise ValueError("请提供有效账号名称")
            account = session.scalar(
                select(Account).where(Account.username == args.username.casefold())
            )
            if args.action == "add":
                if account:
                    raise ValueError("账号已存在")
                if not args.role:
                    raise ValueError("新增账号需要指定 --role admin 或 user")
                session.add(
                    Account(
                        username=args.username.casefold(),
                        display_name=args.name or args.username,
                        role=args.role,
                        password_hash=auth.hasher.hash(new_password()),
                    )
                )
                print("账号已创建")
                return
            if not account:
                raise ValueError("账号不存在")
            if args.action == "role" and not args.role:
                raise ValueError("修改角色需要指定 --role admin 或 user")
            removing_admin = args.action == "disable" or (
                args.action == "role" and args.role == "user"
            )
            admins = list(
                session.scalars(
                    select(Account).where(
                        Account.role == "admin", Account.enabled.is_(True)
                    )
                )
            )
            if (
                removing_admin
                and account.enabled
                and account.role == "admin"
                and len(admins) == 1
            ):
                raise ValueError("不能禁用或降级最后一个有效管理员")
            if args.action == "password":
                account.password_hash = auth.hasher.hash(new_password())
            elif args.action == "role":
                account.role = args.role
            else:
                account.enabled = args.action == "enable"
            session.execute(
                delete(LoginSession).where(LoginSession.account_id == account.id)
            )
            print("账号已更新，原有会话已撤销")
    finally:
        database.close()


if __name__ == "__main__":
    main()
