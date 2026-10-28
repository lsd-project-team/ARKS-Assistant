"""账号只保存所选配置 ID，模型地址和凭据仍由管理员统一维护。"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ModelPreference(Base):
    __tablename__ = "model_preferences"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    profile_id: Mapped[str] = mapped_column(String(40))
