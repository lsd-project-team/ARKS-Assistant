# 任务：从零实现多页面产能统计桌面应用

工作区为空，只有 `data/capacity.csv`（`date,count`）。请从零创建 .NET 8 WinForms 应用 `CapacityStats`：

1. SDK 工程 `net8.0-windows`，`UseWindowsForms=true`，根目录 `CapacityStats.csproj`；主窗口标题 `产能统计`；
2. 左侧 5 个导航按钮：`产能统计`、`工况统计`、`故障统计`、`设置`、`信息导出`；
3. 点击导航按钮切换内容页；每个页面顶部有一个标题 Label，文本为 `PAGE <页面名>`；
4. 第 1 页（索引 0，产能统计）：
   - 读取 `data/capacity.csv`，绘制 `2026-03-09` 至 `2026-03-15` 七天柱状图，每天下方显示日期；
   - 状态栏显示 `WEEK <周总计>`，界面显示 `MONTH <2026-03 月总计>`；
5. 提供导出：`--export <csv路径>` 写出 `date,count` 表头与 7 天（周一至周日）数据，退出码 0；
6. 提供截图：`--screenshot <png路径> <页面索引 0-4>`：
   - 选中对应页面，`DrawToBitmap` 保存 PNG；
   - 向 stdout 与 `<png>.layout.txt` 打印控件行：
     `<类型> <名称> bounds={X=..,Y=..,Width=..,Height=..} visible=True text="<控件文本>"`
   - 第一行 `FORM bounds={X=0,Y=0,Width=..,Height=..} text="产能统计"`；
7. 写 README；构建 0 错误 0 警告；不要留 TODO/占位。

隐藏验收会构建、分别截图 5 个页面、检查 `PAGE` 标题与页面 0 的 `WEEK/MONTH`，并对比 `--export` 输出。
