"""运行配置只在任务内保存凭据，数据库快照只包含可展示字段。"""

from contextlib import contextmanager
from contextvars import ContextVar

from app.core.config import AppSettings
from app.modules.auth.context import request_identity
from app.modules.settings.model_preferences import ModelPreferences

_current = ContextVar[AppSettings | None]("run_configuration", default=None)


def current_configuration(store, database=None):
    if config := _current.get():
        return config
    current = request_identity.get()
    if database is not None and current:
        return ModelPreferences(database, store).configuration(current["user"]["id"])
    return store.load()


@contextmanager
def bind_configuration(settings):
    token = _current.set(settings)
    try:
        yield
    finally:
        _current.reset(token)


def model_snapshot(settings):
    profile = next(
        item for item in settings.model_profiles if item.id == settings.active_profile_id
    )
    return {
        "profile_id": profile.id,
        "profile_name": profile.name,
        **profile.config.model_dump(exclude={"api_key"}),
    }
