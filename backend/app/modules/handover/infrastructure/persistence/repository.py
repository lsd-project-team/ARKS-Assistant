"""全局交接记录的短事务、乐观版本与不可变确认快照。"""

import json
from threading import RLock

from sqlalchemy import select

from app.core.identifiers import new_id, now_iso
from app.modules.auth.context import can_read_review
from app.modules.handover.domain.records import Record
from app.modules.handover.domain.rules import (
    confirmation_gate,
    dependency_cycle,
    linked_ids,
    validate_links,
)
from app.modules.handover.domain.schemas import validate_payload
from app.modules.handover.infrastructure.persistence.models import (
    HandoverBlob,
    HandoverEvent,
    HandoverRecord,
    HandoverRevision,
)

_standalone_lock = RLock()


def dump(value):
    return json.dumps(value, ensure_ascii=False)


def record_dict(row):
    return {
        "id": row.id,
        "scope_id": "global",
        "source_project_id": row.source_project_id,
        "kind": row.kind,
        "title": row.title,
        "version": row.version,
        "state": row.state,
        "payload": json.loads(row.payload_json),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


class HandoverStore:
    def __init__(self, projects=None, *, database=None):
        self.database = database if database is not None else projects.database
        self.lock = projects.lock if projects is not None else _standalone_lock
        self.include_review = can_read_review()

    def _rows(self, session):
        return {row.id: record_dict(row) for row in session.scalars(select(HandoverRecord))}

    def list(self):
        with self.database.session() as session:
            return list(self._rows(session).values())

    def debug_rows(self, include_archived=False):
        with self.database.session() as session:
            statement = select(HandoverRecord).where(HandoverRecord.kind == "debug_issue")
            if not include_archived:
                statement = statement.where(HandoverRecord.state != "archived")
            return [
                record_dict(row)
                for row in session.scalars(
                    statement.order_by(HandoverRecord.updated_at.desc(), HandoverRecord.id)
                )
            ]

    def pending_job_ids(self):
        with self.database.session() as session:
            return [
                row.id
                for row in session.scalars(
                    select(HandoverRecord).where(HandoverRecord.kind == "job")
                )
                if json.loads(row.payload_json)["status"] in {"queued", "running"}
            ]

    def _get(self, session, identifier):
        row = session.get(HandoverRecord, identifier)
        if not row:
            raise FileNotFoundError("交接记录不存在")
        return row

    def _revision(self, session, identifier, version):
        row = self._get(session, identifier)
        revision = session.scalar(
            select(HandoverRevision).where(
                HandoverRevision.record_id == identifier, HandoverRevision.version == version
            )
        )
        if not revision:
            raise FileNotFoundError("交接记录版本不存在")
        result = {
            **record_dict(row),
            "title": revision.title,
            "version": revision.version,
            "state": revision.state,
            "payload": json.loads(revision.payload_json),
            "confirmation": json.loads(revision.confirmation_json),
            "updated_at": revision.created_at,
        }
        if row.kind == "source":
            # 仅展示上传时填写的整理人；不借用当前登录人或后续审核人。
            result["created_by"] = (
                session.scalar(
                    select(HandoverEvent.actor)
                    .where(HandoverEvent.record_id == identifier, HandoverEvent.action == "created")
                    .order_by(HandoverEvent.id)
                    .limit(1)
                )
                or ""
            )
        return result

    def get(self, identifier, version=None):
        with self.database.session() as session:
            row = self._get(session, identifier)
            result = self._revision(session, identifier, version or row.version)
            if not self.include_review:
                result.pop("confirmation", None)
            return result

    def history(self, identifier):
        with self.database.session() as session:
            self._get(session, identifier)
            versions = session.scalars(
                select(HandoverRevision)
                .where(HandoverRevision.record_id == identifier)
                .order_by(HandoverRevision.version.desc())
            )
            return [
                {
                    "version": row.version,
                    "title": row.title,
                    "state": row.state,
                    "confirmation": json.loads(row.confirmation_json),
                    "created_at": row.created_at,
                }
                for row in versions
            ]

    def events(self):
        with self.database.session() as session:
            rows = session.scalars(
                select(HandoverEvent).order_by(HandoverEvent.id.desc()).limit(1000)
            )
            return [
                {
                    "id": row.id,
                    "record_id": row.record_id,
                    "action": row.action,
                    "actor": row.actor,
                    "detail": row.detail,
                    "version": row.version,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def _snapshot(self, session, row, action, actor, detail, confirmation=None):
        session.add(
            HandoverRevision(
                record_id=row.id,
                version=row.version,
                title=row.title,
                state=row.state,
                payload_json=row.payload_json,
                confirmation_json=dump(confirmation or {}),
            )
        )
        session.add(
            HandoverEvent(
                record_id=row.id,
                action=action,
                actor=actor,
                detail=detail,
                version=row.version,
            )
        )

    def _validate(self, session, identifier, kind, payload):
        rows = self._rows(session)
        validate_links(kind, payload, rows, lambda rid, ver: self._revision(session, rid, ver))
        if kind == "task":
            dependency_cycle(identifier, payload, rows)
        if kind == "issue" and payload["status"] == "resolved":
            confirmation_gate({"kind": kind, "payload": payload, "id": identifier}, rows)
        if kind == "candidate":
            validate_payload(payload["target_kind"], payload["proposed"])

    def create(self, kind, title, payload, actor, *, blob=None, internal=False):
        if kind in {"job", "candidate"} and not internal:
            raise ValueError("此记录只能由交接 AI 流程创建")
        value = validate_payload(kind, payload)
        with self.lock, self.database.session.begin() as session:
            identifier = new_id()
            self._validate(session, identifier, kind, value)
            row = HandoverRecord(
                id=identifier,
                kind=kind,
                title=title,
                payload_json=dump(value),
            )
            session.add(row)
            session.flush()
            if blob:
                session.add(HandoverBlob(record_id=identifier, **blob))
            self._snapshot(session, row, "created", actor, "新增交接记录")
            self._invalidate(
                session,
                identifier,
                actor,
                "新增关联证据",
                related=value
                if kind in {"verification", "issue", "constraint", "source"}
                else None,
            )
            return record_dict(row)

    @staticmethod
    def _version(row, version):
        if row.version != version:
            raise ValueError("记录已被更新。草稿已保留，请读取新版本后合并修改")

    def update(self, identifier, body, *, internal=False):
        with self.lock, self.database.session.begin() as session:
            row = self._get(session, identifier)
            self._version(row, body.version)
            if row.kind != body.kind:
                raise ValueError("不能改变记录类型")
            if row.kind in {"source", "package"}:
                raise ValueError("资料与交接包是固定快照，请创建新版本记录")
            if row.kind in {"job", "candidate"} and not internal:
                raise ValueError("运行及候选记录请通过对应操作更新")
            value = validate_payload(row.kind, body.payload)
            self._validate(session, identifier, row.kind, value)
            old = json.loads(row.payload_json)
            row.title, row.payload_json = body.title, dump(value)
            row.version += 1
            row.updated_at = now_iso()
            row.state = "needs_review" if row.state in {"confirmed", "needs_review"} else "draft"
            self._snapshot(
                session, row, "updated", body.actor, body.reason or "修改内容，保留原版本"
            )
            self._invalidate(
                session,
                identifier,
                body.actor,
                body.reason or "关联内容已更新",
                related=value if row.kind in {"verification", "issue", "constraint"} else None,
                previous=old if row.kind in {"verification", "issue", "constraint"} else None,
            )
            return record_dict(row)

    def _invalidate(self, session, identifier, actor, reason, *, related=None, previous=None):
        rows = self._rows(session)
        affected = {identifier}
        # 新增验证、问题或设备约束也需要让已确认工作和计划重新复核。
        for payload in (related, previous):
            if payload:
                if payload.get("supersedes"):
                    affected.add(payload["supersedes"])
                affected.update(payload.get("task_ids", []))
                if payload.get("task_id"):
                    affected.add(payload["task_id"])
                if payload.get("category") == "safety" and not payload.get("task_ids"):
                    affected.update(key for key, row in rows.items() if row["kind"] == "task")
                if "risk" in payload and not payload.get("task_id"):
                    affected.update(key for key, row in rows.items() if row["kind"] == "task")
        while True:
            downstream = {key for key, row in rows.items() if linked_ids(row["payload"]) & affected}
            fresh = downstream - affected
            if not fresh:
                break
            affected.update(fresh)
        for key in affected - {identifier}:
            row = self._get(session, key)
            if row.state == "confirmed":
                row.state, row.version, row.updated_at = "needs_review", row.version + 1, now_iso()
                self._snapshot(
                    session, row, "invalidated", actor, f"{reason}；影响来源 {identifier}"
                )

    def action(self, identifier, action, body):
        with self.lock, self.database.session.begin() as session:
            row = self._get(session, identifier)
            self._version(row, body.version)
            records = self._rows(session) if action == "confirm" else {}
            outcome = Record.from_mapping(record_dict(row)).review(action, records)
            row.state = outcome.state
            row.version += 1
            row.updated_at = now_iso()
            confirmation = (
                {
                    **body.model_dump(exclude={"version"}),
                    "time": row.updated_at,
                    "version": row.version,
                    "decision": action,
                    "linked_versions": dict(outcome.linked_versions),
                }
                if action in {"confirm", "reject"}
                else None
            )
            self._snapshot(session, row, action, body.actor, body.opinion, confirmation)
            if action != "confirm":
                self._invalidate(
                    session,
                    identifier,
                    body.actor,
                    body.opinion,
                    related=json.loads(row.payload_json)
                    if row.kind in {"verification", "issue", "constraint"}
                    else None,
                )
            return record_dict(row)

    def blob(self, identifier):
        with self.database.session() as session:
            self._get(session, identifier)
            row = session.get(HandoverBlob, identifier)
            if not row:
                raise FileNotFoundError("原始附件不存在")
            return {
                "name": row.name,
                "media_type": row.media_type,
                "sha256": row.sha256,
                "content": row.content,
            }

    def promote(self, identifier, body, title, proposed):
        with self.lock, self.database.session.begin() as session:
            candidate = self._get(session, identifier)
            self._version(candidate, body.version)
            value = json.loads(candidate.payload_json)
            if (
                candidate.kind != "candidate"
                or candidate.state == "archived"
                or value["promoted_id"]
            ):
                raise ValueError("此候选已合并或不可合并")
            target = value["target_kind"]
            payload = validate_payload(
                target, {**proposed, "origin": "ai", "evidence": value["evidence"]}
            )
            new_identifier = new_id()
            self._validate(session, new_identifier, target, payload)
            row = HandoverRecord(
                id=new_identifier,
                kind=target,
                title=title,
                payload_json=dump(payload),
            )
            session.add(row)
            session.flush()
            self._snapshot(
                session, row, "merged", body.actor, f"审核候选 {identifier}：{body.opinion}"
            )
            value["promoted_id"] = new_identifier
            candidate.payload_json, candidate.state = dump(value), "confirmed"
            candidate.version += 1
            candidate.updated_at = now_iso()
            self._snapshot(
                session,
                candidate,
                "promoted",
                body.actor,
                body.opinion,
                {
                    "actor": body.actor,
                    "role": body.role,
                    "opinion": body.opinion,
                    "time": now_iso(),
                },
            )
            self._invalidate(
                session,
                new_identifier,
                body.actor,
                "合并新的关联证据",
                related=payload if target in {"issue", "constraint"} else None,
            )
            return record_dict(row)

    def job_status(self, identifier, **changes):
        # 项目在运行期间归档或删除，也必须记录作业的终态，不能遗留“运行中”。
        with self.lock, self.database.session.begin() as session:
            row = self._get(session, identifier)
            if row.kind != "job":
                raise ValueError("不是 AI 作业")
            value = validate_payload("job", {**json.loads(row.payload_json), **changes})
            row.payload_json, row.version, row.updated_at = dump(value), row.version + 1, now_iso()
            self._snapshot(session, row, "job_status", "AI 作业", value["status"])
            return record_dict(row)

    def complete_job(self, identifier, candidates):
        with self.lock, self.database.session.begin() as session:
            job = self._get(session, identifier)
            if job.kind != "job" or json.loads(job.payload_json)["status"] != "running":
                raise ValueError("作业已停止，未保存候选")
            rows = []
            for title, value in candidates:
                value = validate_payload("candidate", value)
                value["promoted_id"] = ""
                proposed = validate_payload(value["target_kind"], value["proposed"])
                self._validate(session, new_id(), value["target_kind"], proposed)
                row = HandoverRecord(
                    id=new_id(),
                    kind="candidate",
                    title=title,
                    payload_json=dump(value),
                )
                session.add(row)
                rows.append(row)
            session.flush()
            for row in rows:
                self._snapshot(session, row, "created", "AI 作业", f"作业 {identifier} 候选")
            value = json.loads(job.payload_json)
            value.update(status="succeeded", result_ids=[row.id for row in rows])
            job.payload_json, job.version, job.updated_at = dump(value), job.version + 1, now_iso()
            self._snapshot(session, job, "job_status", "AI 作业", "候选已生成，待人工审核")
            return record_dict(job)
