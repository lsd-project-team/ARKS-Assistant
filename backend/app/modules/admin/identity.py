"""异步排队时保存提交身份，出队时不借用后台工作线程的身份。"""

from app.core.config import dump_json
from app.modules.auth.context import request_identity


def question_actor():
    current = request_identity.get()
    user = current["user"] if current else {}
    return {"actor_id": user.get("id"), "actor_json": dump_json(user)}
