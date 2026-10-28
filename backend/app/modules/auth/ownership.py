"""个人工作区的服务端边界；管理员和无请求的本机维护保留全量访问。"""

from sqlalchemy import exists, or_, select, true

from app.modules.auth.context import can_read_review as unrestricted
from app.modules.auth.context import request_identity
from app.modules.chat.models import Message, Thread
from app.modules.projects.models import Project
from app.modules.source_analysis.models import SourceWorkspace


def current_owner():
    current = request_identity.get()
    return current["user"]["id"] if current else None


def private_workspace_id(identifier):
    owner = current_owner()
    return f"independent-{owner}" if identifier == "independent" and owner else identifier


def owner_filter(model):
    return true() if unrestricted() else model.owner_id == current_owner()


def thread_filter():
    if unrestricted():
        return true()
    # 对话移动后仍检查项目归属，不能通过独立对话或全局搜索绕过项目边界。
    return owner_filter(Thread) & or_(
        Thread.project_id.is_(None),
        exists(
            select(Project.id)
            .where(Project.id == Thread.project_id, owner_filter(Project))
            .correlate(Thread)
        ),
    )


def require_project(session, identifier, *, include_deleted=False):
    row = session.get(Project, identifier)
    if (
        not row
        or (row.state == "deleted" and not include_deleted)
        or (not unrestricted() and row.owner_id != current_owner())
    ):
        # 不向其他账号泄露资源是否存在。
        raise FileNotFoundError("项目不存在")
    return row


def require_thread(session, row):
    if not row or (not unrestricted() and row.owner_id != current_owner()):
        raise FileNotFoundError("对话不存在")
    if row.project_id:
        require_project(session, row.project_id, include_deleted=True)
    return row


def require_source(session, source_id):
    source = session.get(SourceWorkspace, source_id)
    if not source:
        raise FileNotFoundError("原始源码工作区不存在")
    if unrestricted():
        return source
    own_project = session.scalar(
        select(
            exists(
                select(Project.id).where(
                    owner_filter(Project),
                    Project.state != "deleted",
                    or_(
                        Project.source_root == source.root,
                        Project.source_folders_json.contains(f'"source_id": "{source_id}"'),
                    ),
                )
            )
        )
    )
    # 目录改绑、项目删除后，自己仍保留的问答引用继续有效。
    history = (
        session.scalar(
            select(
                exists(
                    select(Thread.id).where(
                        thread_filter(),
                        exists(
                            select(Message.id).where(
                                Message.thread_id == Thread.id,
                                or_(
                                    Message.source_workspace_id == source_id,
                                    Message.selections_json.contains(
                                        f'"source_workspace_id": "{source_id}"'
                                    ),
                                ),
                            )
                        ),
                    )
                )
            )
        )
        if not own_project
        else False
    )
    if not own_project and not history:
        raise FileNotFoundError("原始源码工作区不存在")
    return source
