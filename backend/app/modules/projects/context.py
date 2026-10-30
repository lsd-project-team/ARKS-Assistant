"""运行开始时固定项目身份，切换项目或编辑设置只影响后续运行。"""

from contextlib import contextmanager
from contextvars import ContextVar

current_project = ContextVar("current_project", default=None)


@contextmanager
def bind_project(snapshot):
    token = current_project.set(snapshot)
    try:
        yield
    finally:
        current_project.reset(token)


def project_prompt():
    project = current_project.get()
    if not project:
        return ""
    return f"\n当前项目：{project.get('name', '独立对话')}\n"
