# 任务：重构现有 Python 订单统计模块

工作区已有 `orders.py` 与 `tests/test_orders.py`，两个公开函数各自重复实现了“按字段分组求和”。

要求：

1. 提取一个共享的内部函数（如 `_group_total(orders, field)`），两个公开函数改为调用它；
2. **不要改变** `total_by_customer` / `total_by_product` 的签名与返回结果；
3. **不要修改测试文件**，测试是验收依据；不要删除或跳过测试；
4. README 补充一句重构说明；
5. 运行 `python -m pytest -q`，全部通过；不要留 TODO/占位。
