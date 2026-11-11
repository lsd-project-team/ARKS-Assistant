# 通用代码工作与就地模式（双模式）改造方案

开始日期：2026-11-11。

范围确认：保留现有隔离副本能力作为“严格模式”，新增 Codex 式就地模式；命令执行走白名单、审批和超时；允许在已配置的工作区内新建独立工程；首个验收样例为 WinForms 串口调试助手。

结论：现有功能不删除。ZX2200 绑定降级为一个适配器，通用能力抽到 `modules/coding/`，就地模式作为第二个工作区适配器接入，两模式共用同一变更内核与前端面板。

## 一、为什么不删除

`backend/app/modules/code_work/` 约 2500 行，业务绑定集中在 6 个文件、约 28 处；前端约 2900 行，业务字符串只有 3 处。其余部分是任何代码代理都需要、且容易做错的能力：

- 版本乐观锁编辑与唯一匹配替换（避免改错位置）。
- 基线 + 逐轮内容哈希快照（旧轮次差异不随后续编辑漂移）。
- 行级差异、修改块撤销、编码/BOM/换行保持。
- 事务式多文件写回、崩溃恢复、恢复冲突人工确认。
- 并发互斥、路径越界与链接拒绝、磁盘与大小配额。
- 前端变更面板、逐文件差异、选区反馈、验证报告与截图。

直接删除会连带丢掉这些，并让 `data/scratch/cw/` 下的历史副本、验证报告和合并记录失去入口。

## 二、现状边界（证据）

绑定点：

- `files.py`：`PROJECT = "AKRS.ZX2200"`、`editable_path` 白名单、`PROTECTED = {Program.cs}`、快照目录。
- `environment.py`：来源必须含 `AKRS.ZX2200/Infrastructure/Simulation/OriginalSimulation.cs`；只接受 `MSBuild.exe`。
- `service.py` / `merging.py`：`locked` 清单写死 `Program.cs`、`csproj`、`App.config`、`Infrastructure/Simulation/*.cs`。
- `runner.py`：固定四步（虚拟驱动测试 → Simulation 编译 → 自检 → Harness），参数与 `PASS:` 正则写死。
- `checks.py`：Harness 的 `using AKRS.ZX2200.*`、引用 `AKRS.ZX2200.exe`、`CountCalls` 语义。
- 前端：仅 `CodeEnvironmentPanel`、`RequirementPanel` 两处文案提到 ZX2200。
- 工具层：`CODE_WORK_GUIDANCE` 混装“通用改码规则”与“ZX2200 业务规则”。

## 三、保留 / 改造 / 新增 / 删除

| 类别 | 内容 | 处置 |
| --- | --- | --- |
| 通用内核 | 路径策略、版本编辑、历史快照、差异与块撤销、事务写回、恢复、锁 | 新建 `modules/coding/`，代码平移，行为不变 |
| 严格模式适配器 | ZX2200 策略、固定四步验证、C# Harness、三方合并、管理员确认 | 保留在 `code_work`，改为调用内核 |
| 就地模式适配器 | 工作区来源、写盘前快照、还原、命令执行、工程脚手架 | 新建 `local_work` |
| 命令执行 | 当前无（runner 首行“不接受模型生成的命令”） | 新建通用受控执行层 |
| 前端 | 变更摘要、右侧面板、差异、需求断言、合并、报告 | 复用；新增模式切换、审批弹窗、还原入口 |
| 删除 | 无 | 本期不删除任何现有能力；仅 3 处文案与提示词按模式拆分 |

## 四、逐文件改造映射

### 内核（新建 `backend/app/modules/coding/`）

| 新文件 | 来源 | 内容 |
| --- | --- | --- |
| `policy.py` | `files.py` 的路径判定 | `WorkspacePolicy`：根、工程名、语言后缀、denied、locked、ignored；`editable_path` 改为策略判定 |
| `paths.py` | `files.py` 的 `atomic_bytes`/`safe_path` 调用、`encode_text` | 原子写、编码/BOM/换行保持、越界与链接拒绝 |
| `journal.py` | `history.py` 全量 | 基线、blob、逐轮事件、`turn_changes`、`timeline`、`summary` |
| `diff.py` | `changes.py` + `review.py` | 统一差异、hunks、`reverse_hunk`、行数统计 |
| `commands.py` | `runner.py` 的 `execute`/`stop_process`/`log_text` | 白名单、审批挂起、超时、输出上限、进程树终止 |
| `verify.py` | `runner.py` 的步骤编排与报告校验 | `Verifier` 接口、步骤状态机、报告/产物哈希校验 |
| `guard.py` | `service.py` 的锁与 `_ensure_idle`、`transactions.recover` | 并发互斥、恢复入口、写盘前快照钩子 |

### 严格模式（改造 `code_work`，API 与数据不变）

| 文件 | 动作 |
| --- | --- |
| `files.py` | 保留 `PROJECT`/`snapshot`/`copy_project_outputs`；路径判定改调 `coding.policy`；`PROJECT` 由适配器策略提供 |
| `service.py` | 状态机保留；`_ensure_idle`、`read`/`write`/`revert` 改调内核；新增 `mode: "scratch"` |
| `runner.py` | 只留 ZX2200 四步与 Harness 调用，进程执行改调 `coding.commands`，报告校验改调 `coding.verify` |
| `checks.py` | `RequirementWrite` 的 C# 语法/CountCalls 校验留在适配器；`read_report` 通用部分上移 |
| `merging.py`/`merge_text.py`/`transactions.py` | 保留；`target_file` 白名单由策略提供，事务写回调内核 guard |
| `history.py`/`changes.py`/`review.py` | 改为对内核对内核的薄包装，先保留旧导入路径 |
| `environment.py` | 拆出通用设置（工作区根、编译器、命令白名单），ZX2200 校验留在适配器 |
| `router.py` | 路径与响应不变；依赖注入改为通用服务 + 模式 |

### 就地模式（新建 `backend/app/modules/local_work/` + 工具）

| 新文件 | 内容 |
| --- | --- |
| `service.py` | 工作区根校验、对话状态（`data/scratch/lw/<hash>`）、写盘前快照、还原、互斥 |
| `router.py` | `/api/p/{project}/local-work`：状态、文件、差异、还原、命令、审批、验证 |
| `approvals.py` | 审批记录：挂起、决定（同意/拒绝）、超时（默认 5 分钟）、持久化 |
| `scaffold.py` | 工程脚手架：`net48` WinForms/控制台模板；SDK 风格可选 `net9.0-windows` |
| `agents/tools/local_work.py` | 工具：准备、读、写、编辑、搜索、执行命令、状态、还原、脚手架 |
| `agents/runtime/local_work_guard.py` | 命令与写盘的轮次额度、重复执行保护 |

### Agent 装配

| 文件 | 动作 |
| --- | --- |
| `agents/tools/code_work.py` | `CODE_WORK_GUIDANCE` 拆为通用规则 + 适配器规则；工具按模式装配 |
| `agents/runtime/code_work_repair.py` | 通用化：失败日志回灌，提示片段由 verifier 提供 |
| `agents/runtime/code_work_reads.py` | 改名/保留为通用读进度保护，工具名集合按模式注入 |
| `agents/runtime/graph_builder.py` | 三处装配点改为“按项目配置选择模式”，默认严格模式 |

### 前端

| 文件 | 动作 |
| --- | --- |
| `code_work/CodeWorkDialog.tsx` | 增加 `mode` 与“命令/审批/还原”页签；严格模式保持现有三页签 |
| `code_work/types.ts` | 增加 `mode`、`command`、`approval`、`snapshot` 类型 |
| `code_work/ApprovalDialog.tsx`（新） | 命令审批：命令、cwd、超时、拒绝/同意 |
| `code_work/ReviewDiff.tsx` 等 | 不改 |
| `features/chat/components/ChatPane.tsx` | 摘要卡读取当前模式，链接到对应面板 |
| `features/admin/ConfigurationPage.tsx` | 新增“工作模式与命令白名单”配置块 |

## 五、目标结构与依赖规则

```text
modules/coding/        通用内核，不导入 code_work / local_work
modules/code_work/     严格模式适配器，导入 coding
modules/local_work/    就地模式适配器，导入 coding
agents/tools/*         只依赖模块对外服务，不直接碰文件系统
frontend/features/chat/code_work/  两模式共用
```

规则：内核零业务名；适配器不允许互相导入；前端不感知后端文件布局，只按 `mode` 分支。

## 六、关键契约

### WorkspacePolicy

```python
WorkspacePolicy(
    root=Path(...),            # 绝对路径，不允许链接
    project="AKRS.ZX2200",     # 就地模式可为空
    languages={".cs", ".csproj"},
    denied=["Program.cs", "**/Simulation/**", "**/bin/**", "**/obj/**"],
    locked=["AKRS.ZX2200/AKRS.ZX2200.csproj"],
    ignored={...},
    allow_new_project=True,    # 就地模式开启；严格模式保持 False
)
```

ZX2200 的现有规则原样迁移为默认策略，改造前后必须逐项对照。

### ChangeJournal

沿用现有语义：`baseline/<path>` 首次改动前内容；`history/blobs/<sha256>` 按内容寻址；事件带 `run_id`/`action`/`revision`。接口：`record`/`content`/`timeline`/`turn_changes`/`summary`/`restore`。

### CommandPolicy

```python
CommandPolicy(
    allow=[("dotnet", ("build", "test", "run")), ("MSBuild.exe", ()), ("git", ("status", "diff"))],
    cwd_root=workspace,
    timeout_seconds=120,
    max_output_bytes=8_000_000,
    approval="always",          # always | 白名单内可跳过
    max_runs_per_turn=20,
)
```

执行规则：参数数组、`shell=False`；未命中白名单直接拒绝；命中后按 `approval` 挂起等用户决定；超时/拒绝均按失败返回；输出截断；进程树终止；cwd 与参数禁止越界。

### Verifier

```python
Verifier(steps=[
    Step("build", ["dotnet", "build", "-c", "Release"], pattern=r"Build succeeded"),
    Step("test",  ["dotnet", "test", "--no-build"], pattern=r"Failed:\s*0"),
    Step("smoke", ["./bin/Release/net48/SerialDebugger.exe", "--selftest"], pattern=r"SELFTEST OK"),
])
```

ZX2200 四步是该接口的一个实现；`verification.json`、产物哈希、报告校验契约不变。

## 七、就地模式的安全模型

1. **写盘前快照**：每次写入前保存该文件当前内容到对话 blob；不依赖 git。
2. **还原**：按精确版本还原文件或本轮全部改动；版本不符拒绝。
3. **可选 git**：检测到仓库时展示分支与未提交数量，只读 `git diff`；系统不自动 commit/stash。
4. **命令审批**：默认全部审批；白名单只决定“是否允许执行”，不决定“是否免审批”。
5. **不提供 OS 沙箱**：本机用户权限，界面与文档明示。
6. **互斥**：同一对话同一时刻一个写操作或一条命令；跨对话并行但共享全局并发上限。
7. **配额**：快照目录上限、命令输出上限、每轮命令次数上限。

## 八、数据与 API 兼容

- `data/scratch/cw/<hash>/state.json` 增加 `mode: "scratch"`，缺省按 `scratch` 解释，旧副本免迁移。
- 就地模式状态放 `data/scratch/lw/<hash>/state.json`，只存 journal、审批、验证结果。
- `/api/threads/{thread}/code-work` 全部保留；新增 `/local-work`，响应结构共用 `mode` 字段。
- 前端现有挂载点不变，仅增加模式来源。

## 九、分阶段实施

### 第一阶段：内核抽取（行为不变）

- [ ] 新建 `coding/`：`policy.py`、`paths.py`、`journal.py`、`diff.py`、`guard.py`。
- [ ] `code_work` 的 `files`/`history`/`changes`/`review`/`service`/`transactions` 改调内核；ZX2200 规则转为策略常量。
- [ ] 旧导入路径保留薄包装，避免一次性改测试。
- 退出条件：`backend/tests/unit/code_work` 全绿；Ruff 通过；前端 `npm test`、`npm run build` 通过；同一副本的差异文本、验证报告与改造前逐字节一致。
- 回滚点：仅新增文件 + 包装层，任何一步可单独回退。

### 第二阶段：受控命令执行

- [ ] `coding/commands.py`、`coding/verify.py`；`runner.py` 改为调用。
- [ ] 审批挂起/决定接口（先接口，后 UI）；超时与拒绝路径。
- [ ] 单元测试：白名单命中/未命中、审批同意/拒绝/超时、命令超时、输出截断、进程树终止、cwd 越界。
- 退出条件：反例全覆盖；无审批不执行任何命令。
- 回滚点：ZX2200 四步仍走同一执行器，行为不变。

### 第三阶段：就地工作区、工具与脚手架

- [ ] `local_work` 服务/路由/状态；写盘快照与还原；互斥与配额。
- [ ] `scaffold.py`：`net48` WinForms/控制台模板（离线可编译，SerialPort 在 `System.dll`）；SDK 风格 `net9.0-windows` 可选（需 NuGet）。
- [ ] 工具集与提示片段；`graph_builder` 按项目配置选择模式。
- [ ] 首个验收样例：**WinForms 串口调试助手**（端口枚举/刷新、波特率/数据位/停止位/校验、打开/关闭、收发文本与 HEX、时间戳、清空、`--selftest` 无界面自检）。
- 退出条件：临时目录完成“建工程 → 写文件 → 编译 → 自检 → 差异 → 还原”往返；路径越界与链接被拒绝；崩溃后状态可恢复。

### 第四阶段：前端与收尾

- [ ] 模式切换、审批弹窗、还原入口、命令输出展示、配置页白名单。
- [ ] ZX2200 降级为“预置方案”，文档与界面去掉“唯一来源”表述。
- [ ] 更新 `agent.md`、`docs/features/code-work.md`，补验收记录。
- 退出条件：两模式在浏览器中各完成一次真实流程；严格模式回归不变。

## 十、验收与测试矩阵

| 层 | 用例 |
| --- | --- |
| 内核 | 路径策略、编码保持、blob 一致性、hunk 撤销、并发互斥、恢复 |
| 命令 | 白名单/审批/超时/输出截断/进程树/cwd 越界 |
| 就地 | 建工程、写读改、差异、还原、崩溃恢复、配额 |
| 严格模式 | 现有 9 个测试模块全绿；差异与报告逐字节对照 |
| 前端 | 两模式面板、审批弹窗、还原、键盘可达、窄屏 |
| 安全 | 路径穿越、符号链接、硬链接、越权跨对话 |
| 数据 | `trunk/` 只读且指纹不变；正式数据不被测试写入 |

## 十一、风险与未决

- 就地模式误写：靠写盘快照 + 精确还原；不是 OS 沙箱。
- 审批疲劳：默认全部审批，白名单只决定可执行性；后续可按项目放宽。
- 双模式维护成本：内核单一实现，适配器最小化；禁止适配器互导。
- 新建工程的可信边界：只允许在工作区根内、只允许脚手架白名单模板，禁止覆盖已有工程文件。
- 未决：默认模式（建议默认严格模式）；审批超时后是否允许重发（建议需用户重新确认）；SDK 风格模板是否默认启用（建议按有无网络判断）。

## 十二、工作量估算

| 阶段 | 估算 |
| --- | --- |
| 第一阶段 内核抽取 | 3～5 人日 |
| 第二阶段 命令执行 | 4～6 人日 |
| 第三阶段 就地模式 + 脚手架 + 串口样例 | 5～8 人日 |
| 第四阶段 前端与收尾 | 3～5 人日 |
| 合计 | 15～24 人日 |

估算含测试与验收文档，不含真实设备串口联调。

## 十三、不做

- 不做远程执行、容器或 OS 级沙箱。
- 不自动 commit/stash，不替用户管理 git 历史。
- 不做多工程解决方案的自动解析（脚手架只生成单工程；跨工程引用另行评审）。
- 不验证真实串口收发；本机无设备时只验编译、端口枚举与失败路径。
