# 任务：为现有待办服务增加截止日期与逾期功能

工作区是一个多模块 Python 待办服务（`todo/`）与测试 `tests/test_service.py`，现有测试全部通过。

要求（不得修改现有测试文件）：

1. `todo/models.py` 的 `Task` 增加 `due` 字段（可选，ISO 日期字符串 `YYYY-MM-DD`）。
2. `TodoService.add(title, due=None)`：校验 due 格式，非法时抛 `ValueError`；保存到存储。
3. `TodoService.overdue(today=None)`：返回“未完成且 due 早于 today”的任务列表；`today` 默认当天；无 due 的任务不算逾期。
4. 保持 `add/complete/list` 现有行为与持久化格式兼容（旧数据没有 due 也能加载）。
5. 写 README 的新增用法说明；不要留 TODO/占位。

完成前运行 `python -m pytest -q`，现有 10 个测试必须全部通过；可另加自己的测试。
