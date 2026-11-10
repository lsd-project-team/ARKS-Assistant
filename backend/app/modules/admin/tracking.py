"""按真实访问、前台活动和成功提交采集，重复心跳和请求不重复统计。"""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from threading import RLock

from fastapi import HTTPException
from sqlalchemy import func, select

from app.modules.admin.models import (
    AdminEvent,
    BusinessSubmission,
    CollectionState,
    UsageActivity,
    UsageVisit,
)
from app.modules.chat.models import Message, Thread
from app.modules.handover.domain.schemas import PAYLOADS
from app.modules.handover.infrastructure.persistence.models import HandoverRecord
from app.modules.memory.models import MemoryRecord
from app.modules.projects.models import Project


def submission(session, user, key, category):
    if user.get("role") != "user":
        return
    identifier = hashlib.sha256(f"{user['id']}:{key}".encode()).hexdigest()
    if not session.get(BusinessSubmission, identifier):
        session.add(BusinessSubmission(id=identifier, account_id=user["id"], category=category))


def record_answer_submission(session, message):
    user = json.loads(message.actor_json)
    submission(session, user, f"answer:{message.id}", "AI 问答")


def business_category(method, path):
    """白名单只包含保存业务数据的动作；读取、探测、排队和配置不计任务。"""
    path = re.sub(r"^/api/p/[^/]+/", "/api/", path)
    if method not in {"POST", "PATCH", "PUT", "DELETE"}:
        return None
    if path.startswith("/api/handover/"):
        if path.startswith("/api/handover/ai"):
            return None
        if path.endswith(("/export", "/cancel")):
            return None
        return "交接业务"
    if path == "/api/projects" or re.fullmatch(r"/api/projects/[^/]+", path):
        return "项目管理"
    if path.startswith("/api/memories") and not path.endswith(("/review", "/history")):
        return "知识维护"
    return None


class UsageTracking:
    def __init__(self, database):
        self.database = database
        self.lock = RLock()

    def initialize(self):
        with self.database.session.begin() as session:
            if not session.get(CollectionState, "default"):
                session.add(CollectionState(id="default"))

    def heartbeat(self, user, body, now=None):
        if user["role"] != "user":
            return {"collected": False}
        now = now or datetime.now(UTC)
        stamp = now.isoformat()
        visit_id = str(body.visit_id)
        with self.lock, self.database.session.begin() as session:
            visit = session.get(UsageVisit, visit_id)
            if visit and visit.account_id != user["id"]:
                raise HTTPException(409, "访问身份已变化，请刷新页面")
            if not visit:
                # 首个心跳只登记访问，不能倒推页面打开前的使用时长。
                session.add(
                    UsageVisit(
                        id=visit_id,
                        account_id=user["id"],
                        sequence=body.sequence,
                        started_at=stamp,
                        last_seen=stamp,
                    )
                )
                return {"collected": True}
            if body.sequence <= visit.sequence:
                return {"collected": True}
            elapsed = max(
                0, int((now - datetime.fromisoformat(visit.last_seen)).total_seconds() * 1000)
            )
            active_ms = min(body.active_ms, elapsed, 15000)
            # 同一用户多窗口的重叠时间只计一次。
            latest = session.scalar(
                select(UsageActivity)
                .where(UsageActivity.account_id == user["id"])
                .order_by(UsageActivity.created_at.desc())
                .limit(1)
            )
            if latest:
                gap = max(
                    0, int((now - datetime.fromisoformat(latest.created_at)).total_seconds() * 1000)
                )
                active_ms = min(active_ms, gap)
            visit.sequence, visit.last_seen = body.sequence, stamp
            if active_ms > 0:
                session.add(
                    UsageActivity(
                        account_id=user["id"],
                        visit_id=visit.id,
                        active_ms=active_ms,
                        created_at=stamp,
                    )
                )
            return {"collected": True}

    def successful_request(self, user, method, path, request_id):
        category = business_category(method, path)
        relative = re.sub(r"^/api/p/[^/]+/", "/api/", path)
        configuration = relative == "/api/settings" or category in {"项目管理", "知识维护"}
        if (
            user["role"] == "admin"
            and method in {"POST", "PUT", "PATCH", "DELETE"}
            and configuration
        ):
            key = hashlib.sha256(f"admin:{user['id']}:{path}:{request_id}".encode()).hexdigest()
            with self.lock, self.database.session.begin() as session:
                if not session.get(AdminEvent, key):
                    session.add(
                        AdminEvent(
                            id=key,
                            actor=user["username"],
                            action="维护系统配置与知识",
                            target=relative,
                            detail="配置已保存；不记录密钥或配置正文",
                        )
                    )
        if not category or user["role"] != "user":
            return
        with self.lock, self.database.session.begin() as session:
            submission(session, user, f"{method}:{path}:{request_id}", category)

    def overview(self, period):
        now = datetime.now(UTC)
        with self.database.session() as session:
            collected = session.get(CollectionState, "default").started_at
            start = (
                max(collected, (now - timedelta(days=int(period))).isoformat())
                if period != "all"
                else collected
            )

            def count(model, *where):
                return session.scalar(select(func.count()).select_from(model).where(*where)) or 0

            activity = UsageActivity.created_at >= start
            visits = UsageVisit.started_at >= start
            commits = BusinessSubmission.created_at >= start
            stock = {
                "项目": count(Project, Project.state != "deleted"),
                "长期记忆": count(MemoryRecord),
                "问答消息": session.scalar(
                    select(func.count())
                    .select_from(Message)
                    .join(Thread, Message.thread_id == Thread.id)
                    .where(Thread.state != "deleted")
                )
                or 0,
                "交接记录": count(HandoverRecord, HandoverRecord.kind.in_(PAYLOADS)),
            }
            daily = {}

            def day(stamp):
                return (datetime.fromisoformat(stamp) + timedelta(hours=8)).strftime("%Y-%m-%d")

            first = day(start)
            cursor = datetime.fromisoformat(first)
            last = day(now.isoformat())
            while cursor.strftime("%Y-%m-%d") <= last:
                key = cursor.strftime("%Y-%m-%d")
                daily[key] = {"date": key, "visits": 0, "tasks": 0, "active_ms": 0}
                cursor += timedelta(days=1)
            # 在数据库聚合，不把整个采集历史加载到内存中。
            for stamp, condition, field, amount in (
                (UsageVisit.started_at, visits, "visits", func.count()),
                (BusinessSubmission.created_at, commits, "tasks", func.count()),
                (
                    UsageActivity.created_at,
                    activity,
                    "active_ms",
                    func.sum(UsageActivity.active_ms),
                ),
            ):
                bucket = func.date(stamp, "+8 hours")
                for date, value in session.execute(
                    select(bucket, amount).where(condition).group_by(bucket)
                ):
                    if date in daily:
                        daily[date][field] = value or 0
            active_ids = (
                select(UsageActivity.account_id)
                .where(activity)
                .union(select(BusinessSubmission.account_id).where(commits))
                .subquery()
            )
            return {
                "period": period,
                "collected_since": collected,
                "range_start": start,
                "as_of": now.isoformat(),
                "active_users": session.scalar(select(func.count()).select_from(active_ids)),
                "visits": count(UsageVisit, visits),
                "active_ms": session.scalar(
                    select(func.sum(UsageActivity.active_ms)).where(activity)
                )
                or 0,
                "tasks": count(BusinessSubmission, commits),
                "data_total": sum(stock.values()),
                "data_breakdown": stock,
                "daily": list(daily.values()),
            }
