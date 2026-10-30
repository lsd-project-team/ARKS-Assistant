"""按服务端项目身份导入和查询不可变采集批次。"""

import csv
import hashlib
import io
import json

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.modules.action_timing.catalog import BY_CODE
from app.modules.action_timing.models import TimingRun, TimingSample
from app.modules.action_timing.packages import read_package
from app.modules.action_timing.statistics import summarize
from app.modules.auth.ownership import current_owner, private_workspace_id, require_project


class ActionTiming:
    def __init__(self, services):
        self.database = services.database
        self.project_id = services.repository.project_id

    def scope(self, session, *, writing=False):
        if self.project_id:
            project = require_project(session, self.project_id)
            if writing and project.state != "active":
                raise ValueError("请先恢复项目，再导入耗时记录")
            return self.project_id
        return private_workspace_id("independent")

    def import_package(self, raw):
        package = read_package(raw).model_dump(mode="json")
        package["events"].sort(key=lambda event: event["event_id"])
        canonical = json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        # 唯一约束也保护并发导入；整包事件与运行在同一个事务中提交。
        try:
            with self.database.session.begin() as session:
                scope = self.scope(session, writing=True)
                existing = session.scalar(
                    select(TimingRun).where(
                        TimingRun.scope_id == scope,
                        TimingRun.source_run_id == package["manifest"]["run_id"],
                    )
                )
                if existing:
                    return self._duplicate(existing, digest)
                row = TimingRun(
                    scope_id=scope,
                    owner_id=current_owner(),
                    source_run_id=package["manifest"]["run_id"],
                    content_hash=digest,
                    file_hash=hashlib.sha256(raw).hexdigest(),
                    manifest_json=json.dumps(package["manifest"], ensure_ascii=False),
                    package_json=canonical,
                )
                session.add(row)
                session.flush()
                session.add_all(
                    TimingSample(
                        run_id=row.id,
                        event_id=event["event_id"],
                        action_code=event["action_code"],
                        kind=event["kind"],
                        status=event["status"],
                        start_ms=event["start_ms"],
                        duration_ms=(
                            event["end_ms"] - event["start_ms"]
                            if event["end_ms"] is not None
                            else None
                        ),
                        event_json=json.dumps(event, ensure_ascii=False),
                    )
                    for event in package["events"]
                )
                return {
                    "run": self._run(row),
                    "duplicate": False,
                    "imported": len(package["events"]),
                }
        except IntegrityError:
            with self.database.session() as session:
                existing = session.scalar(
                    select(TimingRun).where(
                        TimingRun.scope_id == self.scope(session),
                        TimingRun.source_run_id == package["manifest"]["run_id"],
                    )
                )
                if not existing:
                    raise
                return self._duplicate(existing, digest)

    def _duplicate(self, row, digest):
        if row.content_hash != digest:
            raise ValueError("此run_id已有不同内容，请保留原批次并核对采集包")
        return {"run": self._run(row), "duplicate": True, "imported": 0}

    @staticmethod
    def _run(row):
        manifest = json.loads(row.manifest_json)
        return {
            "id": row.id,
            "created_at": row.created_at,
            "content_hash": row.content_hash,
            **manifest,
        }

    def _require(self, session, identifier):
        row = session.get(TimingRun, identifier)
        if not row or row.scope_id != self.scope(session):
            raise FileNotFoundError("耗时批次不存在")
        return row

    def runs(self, limit, offset):
        with self.database.session() as session:
            condition = TimingRun.scope_id == self.scope(session)
            total = session.scalar(select(func.count()).select_from(TimingRun).where(condition))
            rows = session.scalars(
                select(TimingRun)
                .where(condition)
                .order_by(TimingRun.created_at.desc(), TimingRun.id)
                .offset(offset)
                .limit(limit)
            )
            return {"items": [self._run(row) for row in rows], "total": total}

    def summary(self, identifier):
        with self.database.session() as session:
            row = self._require(session, identifier)
            return {"run": self._run(row), **summarize(json.loads(row.package_json))}

    def events(self, identifier, action_code, status, kind, limit, offset):
        with self.database.session() as session:
            self._require(session, identifier)
            conditions = [TimingSample.run_id == identifier, TimingSample.kind == kind]
            if action_code:
                conditions.append(TimingSample.action_code == action_code)
            if status:
                conditions.append(TimingSample.status == status)
            total = session.scalar(
                select(func.count()).select_from(TimingSample).where(*conditions)
            )
            rows = session.scalars(
                select(TimingSample)
                .where(*conditions)
                .order_by(TimingSample.start_ms, TimingSample.id)
                .offset(offset)
                .limit(limit)
            )
            return {"items": [json.loads(row.event_json) for row in rows], "total": total}

    def detail(self, identifier, event_id):
        package = self.package(identifier)
        root = next((event for event in package["events"] if event["event_id"] == event_id), None)
        if not root or root["kind"] != "action":
            raise FileNotFoundError("动作记录不存在")
        return {
            "action": BY_CODE[root["action_code"]],
            "event": root,
            "stages": sorted(
                [event for event in package["events"] if event["parent_id"] == event_id],
                key=lambda event: event["start_ms"],
            ),
        }

    def package(self, identifier):
        with self.database.session() as session:
            return json.loads(self._require(session, identifier).package_json)

    def export_csv(self, identifier):
        result = self.summary(identifier)
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "动作",
                "分支",
                "调用数",
                "有效样本",
                "平均ms",
                "最小ms",
                "最大ms",
                "P50ms",
                "P95ms",
                "数据来源",
                "模式",
                "配方",
                "源码版本",
            ]
        )
        for row in result["rows"]:
            for branch in row["branches"] or [{"branch": "未采样", **row}]:
                # 来自文件的文本不能被Excel解释为公式。
                label = branch["branch"]
                if label.lstrip().startswith(("=", "+", "-", "@")):
                    label = "'" + label
                writer.writerow(
                    [row["name"], label]
                    + [
                        branch[key]
                        for key in (
                            "count",
                            "valid_count",
                            "mean_ms",
                            "min_ms",
                            "max_ms",
                            "p50_ms",
                            "p95_ms",
                        )
                    ]
                    + [
                        "采集器测试" if result["source_kind"] == "collector_test" else "原有空跑",
                        result["run"]["mode"],
                        self._csv_text(result["run"]["recipe_name"]),
                        self._csv_text(result["run"]["source_revision"]),
                    ]
                )
        return "\ufeff" + output.getvalue()

    @staticmethod
    def _csv_text(value):
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
