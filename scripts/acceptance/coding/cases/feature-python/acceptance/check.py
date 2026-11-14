"""独立验收：直接调用待办服务，验证 due/overdue 新行为。"""

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from todo import Store, TodoService  # noqa: E402

FAILS = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tasks.json"
        todo = TodoService(Store(path))

        task = todo.add("过期任务", due="2026-01-01")
        check("add 接受 due", getattr(task, "due", None) == "2026-01-01", str(getattr(task, "due", None)))
        future = todo.add("未来任务", due="2026-02-01")
        no_due = todo.add("无截止")
        check("无 due 为 None", getattr(no_due, "due", "missing") is None)

        overdue = todo.overdue(date(2026, 1, 10))
        check(
            "overdue 只含过期未完成",
            [item.id for item in overdue] == [task.id],
            str([item.id for item in overdue]),
        )

        reloaded = TodoService(Store(path))
        due = getattr(reloaded.overdue(date(2026, 1, 10))[0], "due", None)
        check("due 持久化", due == "2026-01-01", str(due))

        todo.complete(task.id)
        check("完成后不算逾期", todo.overdue(date(2026, 1, 10)) == [])

        future_task = todo.add("再检查未来", due="2026-03-01")
        check(
            "未来任务不算逾期",
            all(item.id != future_task.id for item in todo.overdue(date(2026, 1, 10))),
        )

        try:
            todo.add("坏日期", due="2026-13-40")
            check("非法 due 抛 ValueError", False)
        except ValueError:
            check("非法 due 抛 ValueError", True)
        except Exception as error:  # noqa: BLE001
            check("非法 due 抛 ValueError", False, repr(error))

        check("现有 list 行为", len(todo.list("all")) >= 4)
        check("未来任务存在", getattr(future, "due", None) == "2026-02-01")
    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
