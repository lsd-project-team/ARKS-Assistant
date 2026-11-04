"""回答反馈只追加，提交人和回答关联由服务端确定。"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, tuple_

from app.modules.admin.identity import question_actor
from app.modules.chat.models import AnswerFeedback, Message, Run


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: UUID
    category: Literal["", "incorrect", "off_topic", "incomplete", "source", "display", "other"] = ""
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("请填写反馈说明")
        return value.strip()


def submit_feedback(repository, thread_id, message_id, body):
    actor = question_actor()
    with repository.lock, repository.database.session.begin() as session:
        repository.catalog.row(session, thread_id)
        message = session.get(Message, message_id)
        if not message or message.thread_id != thread_id or message.role != "assistant":
            raise FileNotFoundError("回答不存在")
        if not message.content.strip():
            raise ValueError("此回答暂无可反馈的内容")
        identifier = str(body.submission_id)
        # 同一次提交重试复用编号，网络中断后重试不会重复落库。
        existing = session.get(AnswerFeedback, identifier)
        if existing:
            if (
                existing.actor_id != actor["actor_id"]
                or existing.message_id != message_id
                or existing.category != body.category
                or existing.content != body.content
            ):
                raise ValueError("提交编号已使用，请重新打开反馈窗口")
            return {"id": existing.id}
        run = session.scalar(select(Run).where(Run.response_message_id == message_id))
        # 分支复制的历史消息没有运行记录，按该分支的消息顺序关联原问题。
        question_id = (
            run.message_id
            if run
            else session.scalar(
                select(Message.id)
                .where(
                    Message.thread_id == thread_id,
                    Message.role == "user",
                    tuple_(Message.created_at, Message.id) < (message.created_at, message.id),
                )
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(1)
            )
        )
        session.add(
            AnswerFeedback(
                id=identifier,
                thread_id=thread_id,
                message_id=message_id,
                question_id=question_id,
                run_id=run.id if run else None,
                **actor,
                category=body.category,
                content=body.content,
            )
        )
        return {"id": identifier}
