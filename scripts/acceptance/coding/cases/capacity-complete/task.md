# 任务：补完产能统计 7 个页面

工作区已有可运行的 .NET 9 WinForms 应用（`CapacityStats/`），当前只有“产能统计”页有内容，其余导航只是切换标题。请补完：

每个页面顶部 Label 文本为 `PAGE <页面名>`，并显示下列文本（数字来自数据库）：

1. `PAGE 产能统计`：保留周/月柱状图；显示 `WEEK <2022-04-07 所在周总计>`、`MONTH <2022-04 月总计>`；
2. `PAGE 工况统计`：显示 `SHIFT <cap 表全部 count 之和>`；
3. `PAGE 故障统计`：从 `data/AKRS.Classification.db` 读取，显示 `FAULT <Info 表行数>`；
4. `PAGE 故障分类及趋势`：显示 `CLASS <Class 表行数>`，并按 Class 画柱状图；
5. `PAGE 故障分析`：显示 `CATEGORY <Category 表行数>`；
6. `PAGE 设置`：显示 `PAGE 设置`（可留说明文本）；
7. `PAGE 信息导出`：支持 `--export <目录>`，写出：
   - `capacity.csv`：表头 `date,count`，2022-04-04 至 2022-04-10 共 7 行；
   - `faults.csv`：表头 `id,class,category,name`，Info 表全部 421 行。

保留 `--screenshot <png> <页面索引 0-6>`：选中页面、保存 PNG，并向 stdout 打印控件行（含每个控件 `text="..."`）与 `FORM ... text="..."`。

要求：7 个页面都要真正渲染（截图不同），构建 0 错误；写 README。不要留 TODO/占位。
