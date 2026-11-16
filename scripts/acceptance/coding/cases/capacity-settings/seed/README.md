# 产能统计（CapacityStats）

按 `screenshot.png` 与 `data/AKRS.capacity.db`、`data/AKRS.Classification.db` 复刻的 C# WinForms 桌面应用：左侧导航 + 右侧 7 个页面（产能统计、工况统计、故障统计、故障分类及趋势、故障分析、设置、信息导出），数据全部来自 SQLite 数据库，并支持命令行导出 CSV。

## 运行环境

- .NET 9 SDK（`net9.0-windows`，WinForms）
- Windows 桌面
- 唯一外部依赖：`Microsoft.Data.Sqlite` 9.0.0（NuGet）

## 目录结构

```
CapacityStats/                 主程序（WinExe）
  Program.cs                   入口：--screenshot / --export 两个命令行契约
  MainForm.cs                  主窗体：导航、7 个页面视图、日期切换、周/月统计
  Core/CapacityAggregator.cs   产能统计口径（周/月分柱、轴上限、格式化）
  Core/PageStats.cs            页面统计口径（cap 求和、Info/Class/Category 行数、Capacity 区间、导出内容）
  Core/UiText.cs               文案与格式化
  Core/CsvWriter.cs            CSV 写出（表头 + 行，UTF-8 无 BOM，LF 换行）
  Data/CapacityRepository.cs   SQLite 只读访问（产能、分钟产能、良率、工况、故障、班次配置、分类表）
  UI/NavPanel.cs               左侧导航（返回箭头 + 7 个导航项）
  UI/CapacityChartControl.cs   柱状图（K 轴刻度、网格线、柱顶竖排数值、底部标签）
  UI/CircleArrowButton.cs      圆形箭头按钮
CapacityStats.SelfTest/        离线自测控制台（口径 + 真实数据库 + 导出）
data/                          原应用数据库（运行时只读）
screenshot.png                 原应用界面截图（界面规格）
```

## 7 个页面与规定文本

每个页面顶部标题 Label 的文本严格为 `PAGE <页面名>`，页面正文 Label 显示下列文本（数字来自数据库）：

| 索引 | 页面 | 规定文本 | 数据来源与口径 |
| --- | --- | --- | --- |
| 0 | 产能统计 | `WEEK 213,081`、`MONTH 213,081` | `Capacity` 表按 `cap` 口径求和：2022-04-07 所在周（2022-04-04~04-10）与 2022-04 月合计 |
| 1 | 工况统计 | `SHIFT 13,756,319` | `cap` 表全部 `count` 之和 |
| 2 | 故障统计 | `FAULT 421` | `AKRS.Classification.db` 的 `Info` 表行数 |
| 3 | 故障分类及趋势 | `CLASS 3` | `Class` 表行数，并按 Class 画柱状图（每根柱 = 该 Class 的 Info 条数） |
| 4 | 故障分析 | `CATEGORY 6` | `Category` 表行数 |
| 5 | 设置 | `PAGE 设置` | 说明文本（班次配置、数据目录） |
| 6 | 信息导出 | `PAGE 信息导出` | 说明文本 + 导出命令提示 |

页面 0 保留周/月柱状图与日期切换；页面 3 的柱状图与页面 0 共用同一套绘制控件。

## 数据来源与统计口径

| 界面元素 | 数据来源 | 口径 |
| --- | --- | --- |
| 柱状图（周统计） | `AKRS.capacity.db` 的 `Capacity(date, count)` | 选中日期所在自然周（周一起）7 天，柱值 = 当天 `count`，缺失日记 0 |
| 柱状图（月统计） | 同上 | 选中日期所在自然月，按自然周（周一起）汇总，柱值 = 该周合计（不跨月累计） |
| 日期切换 | — | 周统计 ±7 天，月统计 ±1 月；初始定位到数据库最新日期（2022-04-07） |
| 统计行 | 图表数据 | 合计、日均（合计/柱数）、峰值及峰值日期 |
| `WEEK` / `MONTH` | `Capacity` 表 | 区间内 `count` 求和，缺失日期按 0 计 |
| `SHIFT` | `cap` 表 | 全部 `count` 求和（含 `0001-01-01` 占位行，其 `count` 为 0） |
| `FAULT` / `CLASS` / `CATEGORY` | `AKRS.Classification.db` | `Info` / `Class` / `Category` 表行数 |
| 故障分类柱状图 | `Info` 表 | 按 `class` 分组计数，柱标签为 Class 名称 |
| 设置 | `config(key='shift')` | 班次时间配置 |
| 信息导出 | — | 显示数据目录与导出命令 |

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

参数为 `--screenshot <png路径> <页面索引 0-6>`（0=产能统计 … 6=信息导出）。程序会选中对应页面、离屏渲染主窗体、保存 PNG，并把全部控件的 bounds 递归打印到标准输出（无深度限制，含每个控件的 `text="..."` 与 `FORM ... text="..."`）。

## 导出契约

```powershell
dotnet run --project CapacityStats/CapacityStats.csproj -- --export out
```

写出两个文件（目录不存在时自动创建，UTF-8 无 BOM，LF 换行）：

- `capacity.csv`：表头 `date,count`，`Capacity` 表 2022-04-04 至 2022-04-10 共 7 行，缺失日期 `count` 写 0；
- `faults.csv`：表头 `id,class,category,name`，`Info` 表全部 421 行（按 `id` 升序）。

导出成功时 stdout 打印 `EXPORT <目录>` 与两个文件的绝对路径，退出码 0。

## 自测

```powershell
dotnet run --project CapacityStats.SelfTest/CapacityStats.SelfTest.csproj
```

覆盖：周起点计算、周统计 7 柱与缺失日补 0、月统计按自然周分柱且不跨月、周期平移、轴上限与 K/M 格式化、统计行文案、页面标题与规定文本格式、`cap` 求和、`Info/Class/Category` 行数、`Capacity` 区间补 0、CSV 内容与导出文件，以及真实数据库读取（周/月合计、分钟产能、故障分类、工况、班次、良率）。全部通过时退出码为 0，并输出 `通过 N 项，失败 0 项`。

## 验收命令

```powershell
dotnet build CapacityStats/CapacityStats.csproj -t:Rebuild
dotnet run --project CapacityStats.SelfTest/CapacityStats.SelfTest.csproj
dotnet run --project CapacityStats/CapacityStats.csproj -- --export out
dotnet run --project CapacityStats/CapacityStats.csproj -- --screenshot shots/tab0.png 0
```

## 已知数据特征

- `Capacity` 共 152 天记录，最新日期 2022-04-07；2022-04-06/07 两天分别 86,636 / 126,445，周合计 213,081。
- `cap` 共 2,665 行，`count` 合计 13,756,319；2022-04-07 当天 12 行合计 2,241。
- `Info` 421 行、`Class` 3 行、`Category` 6 行；`Log` 28,459 条；`Yield` 187 条。
- 数据库中存在 `0001-01-01` 之类的占位日期，统计时按日期原样参与，不参与当前周/月的柱值。
