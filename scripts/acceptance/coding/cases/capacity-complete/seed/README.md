# 产能统计（CapacityStats）

按 `screenshot.png` 与 `data/AKRS.capacity.db`、`data/AKRS.Classification.db` 复刻的 C# WinForms 桌面应用：左侧导航 + 右侧「产能统计」页（标题、日期切换、产能柱状图、周/月统计切换），数据全部来自 SQLite 数据库。

## 运行环境

- .NET 9 SDK（`net9.0-windows`，WinForms）
- Windows 桌面
- 唯一外部依赖：`Microsoft.Data.Sqlite` 9.0.0（NuGet）

## 目录结构

```
CapacityStats/                 主程序（WinExe）
  Program.cs                   入口 + --screenshot 截图契约
  MainForm.cs                  主窗体：导航、标题、日期切换、图表、周/月统计
  Core/CapacityAggregator.cs   统计口径（周/月分柱、轴上限、格式化）
  Core/UiText.cs               文案与格式化
  Data/CapacityRepository.cs   SQLite 只读访问（产能、分钟产能、良率、工况、故障、班次配置）
  UI/NavPanel.cs               左侧导航（返回箭头 + 7 个导航项）
  UI/CapacityChartControl.cs   柱状图（K 轴刻度、网格线、柱顶竖排数值、日期标签）
  UI/CircleArrowButton.cs      圆形箭头按钮
CapacityStats.SelfTest/        离线自测控制台（46 项断言）
data/                          原应用数据库（运行时只读）
screenshot.png                 原应用界面截图（界面规格）
```

## 数据来源与统计口径

| 界面元素 | 数据来源 | 口径 |
| --- | --- | --- |
| 柱状图（周统计） | `AKRS.capacity.db` 的 `Capacity(date, count)` | 选中日期所在自然周（周一起）7 天，柱值 = 当天 `count`，缺失日记 0 |
| 柱状图（月统计） | 同上 | 选中日期所在自然月，按自然周（周一起）汇总，柱值 = 该周合计（不跨月累计） |
| 日期切换 | — | 周统计 ±7 天，月统计 ±1 月；初始定位到数据库最新日期（2022-04-07） |
| 统计行 | 图表数据 | 合计、日均（合计/柱数）、峰值及峰值日期 |
| 工况统计 | `Log(state)` | 按状态计数 |
| 故障统计 / 故障分类 | `Log(code)` + `AKRS.Classification.db` 的 `Info/Class/Category` | 按故障分类（电气/视觉/工艺/软件/原辅材料/其它）汇总 |
| 故障分析 | `Log` 关联 `Info` | 最近一条故障的代码、名称、分类 |
| 设置 | `config(key='shift')` | 班次时间配置 |
| 信息导出 | — | 显示当前数据目录 |

数据库查找顺序：环境变量 `AKRS_DATA_DIR` → 程序目录 `data/` → 程序目录 → 当前目录 `data/` → 当前目录。数据库以只读方式打开，不会修改原始数据。

## 构建与运行

```powershell
dotnet build CapacityStats/CapacityStats.csproj
dotnet run --project CapacityStats/CapacityStats.csproj
```

## 截图契约

```powershell
dotnet run --project CapacityStats/CapacityStats.csproj -- --screenshot shots/tab0.png 0
```

参数为 `--screenshot <png路径> <导航页索引>`（0=产能统计 … 6=信息导出）。程序会离屏渲染主窗体、保存 PNG，并把全部控件的 bounds 递归打印到标准输出（无深度限制）。

## 自测

```powershell
dotnet run --project CapacityStats.SelfTest/CapacityStats.SelfTest.csproj
```

覆盖：周起点计算、周统计 7 柱与缺失日补 0、月统计按自然周分柱且不跨月、周期平移、轴上限与 K/M 格式化、统计行文案，以及真实数据库读取（周/月合计、分钟产能、故障分类、工况、班次、良率）。全部通过时退出码为 0，并输出 `通过 N 项，失败 0 项`。

## 验收命令

```powershell
dotnet build CapacityStats/CapacityStats.csproj -t:Rebuild
dotnet run --project CapacityStats.SelfTest/CapacityStats.SelfTest.csproj
dotnet run --project CapacityStats/CapacityStats.csproj -- --screenshot shots/tab0.png 0
```

## 已知数据特征

- `Capacity` 共 152 天记录，最新日期 2022-04-07；2022-04-06/07 两天分别 86,636 / 126,445，周合计 213,081。
- `Log` 共 28,459 条；`Yield` 187 条；`cap` 为分钟级产能。
- 数据库中存在 `0001-01-01` 之类的占位日期，统计时按日期原样参与，不参与当前周/月的柱值。
