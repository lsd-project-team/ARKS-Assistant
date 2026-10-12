"""运行开始时固定项目指令，切换项目或编辑设置只影响后续运行。"""

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
    return (
        f"\n当前项目：{project.get('name', '独立对话')}\n"
        f"项目说明：{project.get('description', '')}\n"
        f"用户设置的项目指令（适用于此项目的对话）：\n{project.get('instructions', '')}\n"
    )
