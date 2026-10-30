"""导入预览不落库；确认时复核整个台账版本并原子写入。"""

from app.modules.action_timing.ledger_files import export_file, read_rows
from app.modules.action_timing.ledger_schemas import name_key
from app.modules.action_timing.models import TimingAction, TimingCategory


def category_key(value):
    key = name_key(value)
    return "" if key == name_key("未分类") else key


def plan_rows(rows, categories, actions, mode):
    names = {row.id: category_key(row.name) for row in categories}
    existing = {(names.get(row.category_id, ""), row.name_key): row for row in actions}
    seen, errors, planned = set(), [], []
    counts = {"add": 0, "update": 0, "skip": 0}
    for row in rows:
        key = (category_key(row.category), name_key(row.name))
        if key in seen:
            errors.append(
                {"row_number": row.row_number, "message": "文件中分类与动作名称重复，请合并后导入"}
            )
        seen.add(key)
        current = existing.get(key)
        operation = mode if current else "add"
        counts[operation] += 1
        planned.append(
            {
                **row.model_dump(mode="json"),
                "category": row.category or "未分类",
                "operation": operation,
                "effective_duration_seconds": (
                    current.duration_seconds
                    if current and row.duration_seconds is None
                    else row.duration_seconds
                ),
            }
        )
    return planned, counts, errors


class LedgerTransfer:
    def __init__(self, ledger):
        self.ledger = ledger

    def preview(self, raw, filename, mode, unit="auto"):
        rows, errors = read_rows(raw, filename, unit=unit)
        with self.ledger.transaction() as (session, scope):
            categories, actions = self.ledger.load(session, scope)
            planned, counts, duplicates = plan_rows(rows, categories, actions, mode)
            return {
                "rows": planned,
                "counts": counts,
                "errors": errors + duplicates,
                "revision": self.ledger.revision(categories, actions),
            }

    def commit(self, payload):
        with self.ledger.transaction(writing=True) as (session, scope):
            categories, actions = self.ledger.load(session, scope)
            if self.ledger.revision(categories, actions) != payload.revision:
                raise ValueError("预览后台账已发生变化，请重新预览后导入")
            _, counts, errors = plan_rows(payload.rows, categories, actions, payload.mode)
            if errors:
                raise ValueError("文件内有重复动作，请修正后重新导入")
            category_map = {category_key(row.name): row for row in categories}
            category_names = {row.id: category_key(row.name) for row in categories}
            action_map = {
                (category_names.get(row.category_id, ""), row.name_key): row for row in actions
            }
            for item in payload.rows:
                key = (category_key(item.category), name_key(item.name))
                row = action_map.get(key)
                if row and payload.mode == "skip":
                    continue
                category = category_map.get(key[0])
                if key[0] and not category:
                    category = TimingCategory(scope_id=scope, name=item.category, name_key=key[0])
                    session.add(category)
                    session.flush()
                    category_map[key[0]] = category
                duration = item.duration_seconds
                if row:
                    row.version += 1
                    if duration is None:
                        duration = row.duration_seconds
                else:
                    row = TimingAction(scope_id=scope)
                    session.add(row)
                self.ledger.assign_action(
                    row, item.name, category.id if category else None, duration, item.notes
                )
            session.flush()
            return {"counts": counts}

    def export(
        self,
        format,
        category_id="",
        search="",
        duration_status="all",
        template=False,
        sort="name",
        template_unit="s",
    ):
        # 模板下载也校验项目权限，但不创建分类或示例动作。
        data = self.ledger.listing(category_id, search, duration_status, limit=None, sort=sort)
        return export_file(
            [] if template else data["items"], format, unit=template_unit if template else "s"
        )
