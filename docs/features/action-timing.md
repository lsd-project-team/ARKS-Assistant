# 首批动作耗时采集与统计

ARKS 左侧“交接工作台”下面提供“动作耗时统计”。普通用户和管理员均可进入，按所属项目导入、查询和导出。首批范围为 S1 焊点定位、S1 点胶、S2 取片、S2 上视纠偏、S2 固晶。

采集接在 ZX2200 原有 `DryCycle` 调度与动作调用上。工具不启动设备，不生成随机耗时。`trunk/` 始终作为只读输入；设备侧改动由工具生成在 `output/` 隔离副本中。

## 使用步骤

在仓库根目录运行：

```powershell
.\backend\.venv\Scripts\python.exe -X utf8 backend/tools/ActionTiming/prepare_copy.py `
  --destination output/action-timing-workspace/AKRS.ZX2200
```

工具先核对语法入口，再复制主工程和可找到的引用工程，保持同级目录布局。它生成副本、差异文件及带文件哈希的 `AKRS.ZX2200-timing-copy.json`，拒绝覆盖已有副本、重复接入、链接目录或写入 `trunk/`。输入缺少的工程会记录到 `missing_project_references`，不会创建占位依赖。

在具备原设备 SDK、项目引用、配方及硬件条件的开发环境中构建副本。设置 `ARKS_TIMING_OUTPUT` 为采集输出目录，再沿用原设备程序的工作模式选择、启动和停止操作：

```powershell
$env:ARKS_TIMING_OUTPUT = 'D:\agent_project\code_agent\output\device-action-timing'
```

采集只在原 `DryCycle` 模式启用。空跑仍包含原有运动和信号操作，需要原项目运行条件。每个批次保存 `manifest.json` 与 `events.jsonl`；停止后后台写入最终状态。停止期限内未返回的调用标为未完成，达到记录上限或写入失败会标记批次不完整。

把已经结束的批次打包：

```powershell
.\backend\.venv\Scripts\python.exe backend/tools/ActionTiming/pack_run.py `
  output/device-action-timing/实际运行目录 output/action-timing.zip
```

进入 ARKS → 动作耗时统计，选择所属项目，点击“导入采集数据”。支持此 ZIP 或从页面导出的完整 JSON 包，文件及 ZIP 展开总量上限为 16 MiB，每包最多 20,000 条动作和阶段记录。

## 采集与统计口径

| 动作 | 接入的同步内部阶段 |
| --- | --- |
| S1 焊点定位 | 原定位流程，空跑替代视觉结果 |
| S1 点胶 | 单步等待、预点胶调用、运行/暂停等待、不出胶轨迹 |
| S2 取片 | 允许取片等待、静态料盒拍照位或取片中心移动、空跑高度、抬起、运行等待 |
| S2 上视纠偏 | 一点/两点移动、配置拍照停留 |
| S2 固晶 | 空跑固晶位移动、放置配置停留、抬起 |

动作区间包含整个 `DoWork` 同步调用，因此也包含节点原有准备、报警和事件回调开销。当前内部阶段只覆盖上表；后台供料通知等任务不算作同步调用完成，也不在首期后台任务采集范围内。

每次调用用独立单调时间边界记录，携带工位、产品实例、基板、基岛、焊点、工序、逻辑动作和尝试号。动作返回值原样保留；调度跳过、未进入工作阶段、重试、中止、失败及未完成分别显示。`WorkStart/WorkStop` 不是计时依据。

空跑视觉替代结果的流程耗时不代表真实识别算法耗时，空跑点胶不代表真实出胶耗时。调用时间含等待和暂停，首期不提供未经验证的“扣除暂停后的纯机械耗时”。父子区间、并发区间不相加为产品节拍。

仅完整批次内完整成功调用参与均值、最小、最大、P50、P95，分位数使用 nearest-rank。不同分支单独计算；多个分支时汇总行不混算分布。失败父动作中的阶段保留原始记录，但不加入成功动作的阶段分布。不完整批次保留记录与状态，不计算成功分布。无样本显示“—”和原因，而不是零耗时。

`source_kind=collector_test` 在页面、批次选项及 CSV 中明确标为采集器测试。这类数据验证软件通路，不能用作设备性能结论。`source_kind=zx2200` 表示由副本内原空跑调度采集。

## 数据接口

接口位于 `/api/p/{projectId}/action-timing`，独立工作区使用 `independent`，复用现有会话、CSRF 和服务端项目权限。数据包不能指定账号或项目归属。

| 接口 | 用途 |
| --- | --- |
| `GET /catalog` | 首批动作代码、工位、类名及源码位置 |
| `POST /imports` | 原始 JSON/ZIP 请求体，校验后整包事务入库 |
| `GET /runs` | 批次分页 |
| `GET /runs/{id}/summary` | 五项动作、分支及阶段统计 |
| `GET /runs/{id}/events` | 按动作、结果筛选及分页 |
| `GET /runs/{id}/events/{eventId}` | 一次动作及同步子阶段 |
| `GET /runs/{id}/export?format=json或csv` | 原始协议或统计导出 |

协议版本为 1。批次含源码指纹、配方指纹、开始结束时间、时钟频率、记录数、丢失数和采集边界。事件含原始起止毫秒、结果、上下文和父子引用，耗时由后台根据起止计算。协议定义见 `backend/app/modules/action_timing/schemas.py`。

同一作用域内相同运行及相同内容重复导入不重复计数；相同运行编号、不同内容报冲突。事件顺序改变不影响去重。重复事件、重复尝试、孤儿阶段、循环引用、越出父动作的同步阶段、非法时间及未结束批次均拒绝。原始包和查询事件同事务保存，失败不留下半批成功记录。

## 验证范围与运行条件

自动检查覆盖统计反例、协议边界、真实 API/临时 SQLite 事务、重启保存、重复/冲突/并发导入、账号与项目隔离、导出，以及 Windows .NET Framework 采集器的编译和实际执行。C# 验证程序对首批五个动作代码各执行 100 次测试委托，导出后由真实 ARKS 导入接口核对五项计数；这些委托不是 ZX2200 设备动作。

针对性检查：

```powershell
cd backend
.\.venv\Scripts\python.exe -X utf8 -m pytest -q tests/unit/test_action_timing.py tests/integration/test_action_timing.py
```

前端沿用 `npm test`、TypeScript 与生产构建。页面验收使用独立测试账号和临时数据目录，检查导入、去重反馈、动作筛选、阶段明细、刷新恢复、两个角色的入口及导出；正式 `data/` 不导入验收样本。

本轮检查结果：功能专项 32 项通过，项目、认证与架构相关回归 75 项通过，前端 301 项通过，TypeScript、生产构建与 Ruff 通过。浏览器实际导入 1,000 条测试记录，五项各得到 100 次调用，重复导入不增加计数。主工程 2,416 个文件及 9 个引用工程的源文件哈希核对一致；正式库升级到 `0022`，原业务表记录数不变，两个统计表保持空表。按既有认证规则，重启服务后需要重新登录。

2026-10-21 本机源码缺少 `AKRS.Galaxy2.Parameters/AKRS.Galaxy2.Parameters.csproj`；现有 `bin/Debug` 中的 Machine/Config 接口也与当前源码不同。设备侧当前交付为采集器、原调用链接入工具、隔离副本和可审查差异，整机工程构建及原设备空跑尚待具备匹配依赖后验证。采集器检查通过不替代这两项验证。
