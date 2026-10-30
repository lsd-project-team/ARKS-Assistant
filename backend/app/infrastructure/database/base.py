"""数据库表结构保持不变，按业务模块组织模型。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
