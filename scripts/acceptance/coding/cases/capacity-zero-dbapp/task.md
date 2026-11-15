# 任务：从零实现直连 SQLite 的产能统计桌面应用（.NET Framework 4.8）

工作区只有 `data/capacity.db`（表 `cap(date,time,count)`）和 `refs/` 下的 `System.Data.SQLite.dll`、`SQLite.Interop.dll`。

从零创建 .NET Framework 4.8 WinForms 应用 `CapacityStats`（老式 csproj，MSBuild 构建，PlatformTarget=x86）：

1. 工程根目录 `CapacityStats.csproj`，引用 `refs/System.Data.SQLite.dll`（相对路径），构建时把 `refs/SQLite.Interop.dll` 复制到输出目录；
2. 主窗口标题 `产能统计`；左侧 5 个导航按钮：`产能统计`、`工况统计`、`故障统计`、`设置`、`信息导出`；
3. 点击导航切换内容页，每个页面顶部 Label 文本为 `PAGE <页面名>`；
4. 第 1 页（索引 0）：从 `data/capacity.db` 的 `cap` 表按 `date` 汇总，绘制 `2026-03-09` 至 `2026-03-15` 七天柱状图并显示日期；状态栏 `WEEK <周总计>`，界面显示 `MONTH <2026-03 月总计>`；
5. `--export <csv路径>`：写 `date,count` 表头与上述 7 天数据，退出码 0；
6. `--screenshot <png路径> <页面索引 0-4>`：选中页面、保存 PNG，向 stdout 与 `<png>.layout.txt` 打印控件行：
   `<类型> <名称> bounds={X=..,Y=..,Width=..,Height=..} visible=True text="<控件文本>"`
   第一行 `FORM bounds={X=0,Y=0,Width=..,Height=..} text="产能统计"`；
7. 写 README；构建 0 错误 0 警告；不要留 TODO/占位。

隐藏验收会 MSBuild 构建、运行截图/导出，核对标题、5 页、7 天、WEEK/MONTH 与导出数据。
