"""数据库表结构保持不变，按业务模块组织模型。"""

import uuid
from datetime import UTC, datetime


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
