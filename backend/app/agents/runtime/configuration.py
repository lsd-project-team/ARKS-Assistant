"""运行配置只在任务内保存凭据，数据库快照只包含可展示字段。"""

from contextlib import contextmanager
from contextvars import ContextVar

from app.core.config import AppSettings

_current = ContextVar[AppSettings | None]("run_configuration", default=None)


def current_configuration(store):
    return _current.get() or store.load()


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
