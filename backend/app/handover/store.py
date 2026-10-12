"""短事务、乐观版本与不可变确认快照；旧模块的数据只读。"""

import json

from sqlalchemy import select

from app.handover.models import HandoverBlob, HandoverEvent, HandoverRecord, HandoverRevision
from app.handover.rules import confirmation_gate, dependency_cycle, linked_ids, validate_links
from app.handover.schemas import validate_payload
from app.models import new_id, now_iso


def dump(value):
    return json.dumps(value, ensure_ascii=False)


def record_dict(row):
    return {
        "id": row.id,
        "project_id": row.project_id,
        "kind": row.kind,
        "title": row.title,
        "version": row.version,
        "state": row.state,
        "payload": json.loads(row.payload_json),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


class HandoverStore:
    def __init__(self, projects, project_id):
        self.projects, self.project_id = projects, project_id
        self.database = projects.database

    def guard(self, write=False):
        project = self.projects.get(self.project_id)
        if write and project["state"] != "active":
            raise ValueError("归档项目的交接记录只读，请先恢复项目")
        return project

    def _rows(self, session):
        return {
            row.id: record_dict(row)
            for row in session.scalars(
                select(HandoverRecord).where(HandoverRecord.project_id == self.project_id)
            )
        }

    def list(self):
        self.guard()
        with self.database.session() as session:
            return list(self._rows(session).values())

    def _get(self, session, identifier):
        row = session.get(HandoverRecord, identifier)
        if not row or row.project_id != self.project_id:
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
        return {
            **record_dict(row),
            "title": revision.title,
            "version": revision.version,
            "state": revision.state,
            "payload": json.loads(revision.payload_json),
            "confirmation": json.loads(revision.confirmation_json),
            "updated_at": revision.created_at,
        }

    def get(self, identifier, version=None):
        self.guard()
        with self.database.session() as session:
            row = self._get(session, identifier)
            return self._revision(session, identifier, version or row.version)

    def history(self, identifier):
        self.guard()
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
        self.guard()
        with self.database.session() as session:
            rows = session.scalars(
                select(HandoverEvent)
                .where(HandoverEvent.project_id == self.project_id)
                .order_by(HandoverEvent.id.desc())
                .limit(1000)
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
                project_id=self.project_id,
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
        with self.projects.lock, self.database.session.begin() as session:
            self.guard(True)
            identifier = new_id()
            self._validate(session, identifier, kind, value)
            row = HandoverRecord(
                id=identifier,
                project_id=self.project_id,
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
        with self.projects.lock, self.database.session.begin() as session:
            self.guard(True)
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
        with self.projects.lock, self.database.session.begin() as session:
            self.guard(True)
            row = self._get(session, identifier)
            self._version(row, body.version)
            if row.kind == "job":
                raise ValueError("请使用运行的取消或重试操作")
            if action == "confirm":
                if row.state == "confirmed":
                    raise ValueError("此版本已经确认；内容变化时请先编辑并保存新版本")
                if row.state == "archived":
                    raise ValueError("请先恢复记录")
                records = self._rows(session)
                confirmation_gate(record_dict(row), records)
                # 已过期的引用仍可阅读，但再次确认必须明确改用当前版本。
                for reference in json.loads(row.payload_json).get("evidence", []):
                    if records[reference["record_id"]]["version"] != reference["version"]:
                        raise ValueError("来源有新版本，请复核并更新引用后确认")
                row.state = "confirmed"
            elif action == "archive":
                row.state = "archived"
            elif action == "restore":
                row.state = "needs_review"
            else:
                raise ValueError("无效的确认操作")
            row.version += 1
            row.updated_at = now_iso()
            confirmation = (
                {
                    **body.model_dump(exclude={"version"}),
                    "time": row.updated_at,
                    "version": row.version,
                    "linked_versions": {
                        key: records[key]["version"]
                        for key in linked_ids(json.loads(row.payload_json))
                    },
                }
                if action == "confirm"
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
        self.guard()
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
        with self.projects.lock, self.database.session.begin() as session:
            self.guard(True)
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
                project_id=self.project_id,
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
        with self.projects.lock, self.database.session.begin() as session:
            row = self._get(session, identifier)
            if row.kind != "job":
                raise ValueError("不是 AI 作业")
            value = validate_payload("job", {**json.loads(row.payload_json), **changes})
            row.payload_json, row.version, row.updated_at = dump(value), row.version + 1, now_iso()
            self._snapshot(session, row, "job_status", "AI 作业", value["status"])
            return record_dict(row)

    def complete_job(self, identifier, candidates):
        with self.projects.lock, self.database.session.begin() as session:
            self.guard(True)
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
                    project_id=self.project_id,
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
