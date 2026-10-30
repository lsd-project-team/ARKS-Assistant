"""数据库表结构保持不变，按业务模块组织模型。"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class SourceWorkspace(Base):
    """引用保存源码根目录身份，移动对话不会把旧链接指向另一个项目。"""

    __tablename__ = "source_workspaces"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    root: Mapped[str] = mapped_column(Text)
