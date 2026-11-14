# 任务：为图书馆服务增加搜索分页与热门榜

工作区是一个多模块 Python 图书馆服务（`library/`）与 15 个现有测试，当前全部通过。

要求（不得修改现有测试）：

1. `LibraryService.search_books(query="", page=1, size=10)`：
   - 按标题或作者做**不区分大小写**的子串匹配；`query` 为空返回全部；
   - 返回 `{"items": [...], "total": 总数, "page": page, "size": size}`；
   - `page < 1`、`size < 1` 或 `size > 100` 抛 `ValueError`；
   - 分页按书籍 id 升序。
2. `library/reports.py` 增加 `popular_books(service, limit=5)`：
   - 返回 `[(书名, 借阅次数), ...]`，按次数降序、书名升序打破平局，最多 `limit` 条；
   - `limit < 1` 抛 `ValueError`。
3. 保持现有 `add_book/loan/return_book/overdue/counts/loans_by_member` 行为；
4. README 补充新接口说明；不要留 TODO/占位。

完成前运行 `python -m pytest -q`，现有 15 个测试必须全部通过；可另加自己的测试。
