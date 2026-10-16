"""请求上下文跟随 to_thread，导出的固定版本也使用当前账号的可见范围。"""

from contextvars import ContextVar

request_identity: ContextVar[dict | None] = ContextVar("request_identity", default=None)


def can_read_review() -> bool:
    current = request_identity.get()
    # 无 HTTP 请求的本机迁移、备份和内部服务保持原有业务行为。
    return current is None or current["user"]["role"] == "admin"
