"""交接记录用例；HTTP 层只接收请求与返回用例结果。"""

from app.modules.handover.application.ports import RecordRepository
from app.modules.handover.domain.rules import task_blocks


class RecordService:
    def __init__(self, repository: RecordRepository):
        self.repository = repository

    def overview(self):
        # 停用的提取候选与作业仅保留历史快照，不再作为工作台内容返回。
        rows = [row for row in self.repository.list() if row["kind"] not in {"candidate", "job"}]
        records = {row["id"]: row for row in rows if row["state"] != "archived"}
        blocks = {
            row["id"]: task_blocks(row, records)
            for row in records.values()
            if row["kind"] == "task"
        }
        return {"scope_id": "global", "records": rows, "blocks": blocks}

    def create(self, body):
        if body.kind in {"source", "package", "job", "candidate", "debug_issue"}:
            raise ValueError("请使用对应的业务录入入口")
        return self.repository.create(body.kind, body.title, body.payload, body.actor)

    def update(self, identifier, body):
        if body.kind == "debug_issue":
            raise ValueError("请使用调试问题的编辑入口")
        return self.repository.update(identifier, body)
