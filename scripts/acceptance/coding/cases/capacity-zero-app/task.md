# 任务：从零实现产能统计桌面应用（.NET 8 WinForms，无骨架）

工作区为空，只有 `data/capacity.csv`（列 `date,count`）。请从零创建 .NET 8 WinForms 应用 `CapacityStats`：

1. 工程：SDK 风格 `net8.0-windows`，`UseWindowsForms=true`，根目录 `CapacityStats.csproj`；
2. 主窗口标题：`产能统计`；
3. 左侧一列 5 个导航按钮，文本分别为：`产能统计`、`工况统计`、`故障统计`、`设置`、`信息导出`；
4. 主区域读取 `data/capacity.csv`，绘制 `2026-03-09` 至 `2026-03-15` 七天柱状图（可用 Panel 的 Paint 事件画矩形，柱子高度与当日 count 成比例），每天下方显示日期文本（Label 控件或自绘文本均可）；
5. 底部状态栏文本：`WEEK <周总计>`；另在界面某处显示 `MONTH <2026-03 月总计>`；
6. 启动参数 `--screenshot <png路径> <标签页索引>`：
   - 启动窗体、执行一次布局、用 `DrawToBitmap` 保存 PNG；
   - 向 stdout 与 `<png>.layout.txt` 打印控件行：
     `<类型> <名称> bounds={X=..,Y=..,Width=..,Height=..} visible=True text="<控件文本>"`
   - 第一行为 `FORM bounds={X=0,Y=0,Width=..,Height=..} text="产能统计"`；
   - 完成后退出码 0；
7. 写 README；构建 0 错误 0 警告；不要留 TODO/占位。

隐藏验收会构建、运行 `--screenshot`，解析控件文本核对标题、5 个导航、7 天日期、`WEEK/MONTH` 数字，并检查截图非空白。
