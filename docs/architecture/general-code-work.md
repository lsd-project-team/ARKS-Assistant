# 通用代码工作与就地模式（双模式）设计

开始日期：2026-11-11。

目标：把当前只服务 `AKRS.ZX2200` 的代码修改能力，扩展为通用代码工作，并新增 Codex 式就地工作模式。用户已确认两点：保留现有隔离副本能力作为“严格模式”，同时新增就地模式；命令执行必须走白名单、审批和超时。

结论：现有功能不删除。绑定 ZX2200 的部分降级为一个适配器，通用内核抽到独立模块，就地模式作为第二个工作区适配器接入。

## 一、为什么不删除

`backend/app/modules/code_work/` 约 2500 行，业务绑定集中在 6 个文件、约 28 处；前端约 2900 行，业务字符串只有 3 处。其余部分是任何代码代理都需要、且容易做错的能力：

- 版本乐观锁编辑与唯一匹配替换（避免改错位置）。
- 基线 + 逐轮内容哈希快照（旧轮次差异不随后续编辑漂移）。
- 行级差异、修改块撤销、编码/BOM/换行保持。
- 事务式多文件写回、崩溃恢复、恢复冲突人工确认。
- 并发互斥、路径越界与链接拒绝、磁盘与大小配额。
- 前端变更面板、逐文件差异、选区反馈、验证报告与截图。

直接删除会连带丢掉这些，并让 `data/scratch/cw/` 下的历史副本、验证报告和合并记录失去入口。

## 二、保留与改造清单

| 类别 | 内容 | 处置 |
| --- | --- | --- |
| 通用内核 | 路径策略、版本编辑、历史快照、差异/块撤销、事务写回、恢复、锁 | 抽到 `modules/coding/`，行为不变 |
| 隔离适配器 | `PROJECT` 白名单、`locked` 清单、固定四步验证、C# Harness、三方合并、管理员确认 | 保留为“严格模式”适配器 |
| 前端面板 | 变更摘要、右侧工作区、差异、需求断言、合并、报告 | 复用，按模式切换页签 |
| 命令执行 | 当前刻意不提供（runner 首行“不接受模型生成的命令”） | 新增受控执行层 |
| 就地模式 | 无 | 新增工作区适配器、工具与审批界面 |
| 独立新工程 | 不支持（工程名写死） | 本期仍不做，单列后续评审 |

绑定证据：`files.py` 的 `PROJECT` 与 `editable_path`、`environment.py` 的来源校验、`service.py` 与 `merging.py` 的 `locked`、`runner.py` 的整条流水线、`checks.py` 的 using/引用/`AKRS.ZX2200.exe`。前端只有 `CodeEnvironmentPanel` 与 `RequirementPanel` 的说明文案提到 ZX2200。

## 三、目标结构

```text
backend/app/modules/coding/            通用内核（新增，无业务名）
  policy.py        WorkspacePolicy：根目录、工程、语言、允许/禁止路径、locked、忽略项
  editor.py        读/写/版本锁/唯一匹配替换/编码保持
  journal.py       基线、changes、逐轮 blob 快照、摘要、轮次时间线
  diff.py          统一差异、修改块、块撤销
  commands.py      CommandPolicy：白名单、审批、超时、输出上限、进程树终止
  verify.py        可配置验证编排（steps + 结果解析）
  guard.py         锁、并发互斥、恢复入口

backend/app/modules/code_work/         严格模式适配器（保留）
  ...              改为调用 coding 内核；ZX2200 策略与仿真验证留在本模块

backend/app/modules/local_work/        就地模式适配器（新增）
  service.py       工作目录来源、写盘前快照、还原
  router.py        /api/p/{project}/local-work
  approvals.py     命令审批的挂起/超时/决定

backend/app/agents/tools/local_work.py 就地模式工具与提示

frontend/src/features/chat/code_work/  复用面板，新增模式切换与审批对话框
```

约束：内核不导入 `code_work` 或 `local_work`；两个适配器分别导入内核。避免形成双向依赖。

## 四、关键契约

### WorkspacePolicy

```python
policy = WorkspacePolicy(
    root=Path(...),            # 工作区根，绝对路径，不允许链接
    project="AKRS.ZX2200",     # 可选；就地模式可为空
    languages={".cs"},         # 可编辑文件后缀
    denied=[...],              # 相对路径或目录前缀，如 Program.cs、**/Simulation/**
    locked=[...],              # 不允许修改但需校验指纹的文件
    ignored={...},             # 复制/遍历排除项
)
```

`editable_path` 的判定改为：后缀在 `languages` 内、不命中 `denied`、路径在 `root` 内且无链接。ZX2200 的现有硬编码规则原样迁移成该策略的默认值，行为必须与改造前一致。

### ChangeJournal

沿用现有 `history` 语义：`baseline/<path>` 保存首次改动前内容，`history/blobs/<sha256>` 按内容寻址保存每轮前后版本，事件带 `run_id`/`action`/`revision`。对外接口：`record` / `content` / `timeline` / `turn_changes` / `summary`。

### CommandPolicy

```python
policy = CommandPolicy(
    allow=[("dotnet", ("build", "test")), ("npm", ("test", "run")), ("pytest", ())],
    cwd_root=workspace,
    timeout_seconds=120,          # 单条命令；总验证另有上限
    max_output_bytes=8_000_000,    # 复用现有日志上限
    requires_approval=True,        # 未命中白名单一律拒绝，不做“询问后放开”
)
```

执行规则：

1. 只接受参数数组，`shell=False`，不做字符串拼接执行。
2. 可执行名与参数前缀必须命中白名单；未命中直接拒绝并返回可读原因，不给模型“换个写法重试”的空间。
3. 命中白名单但属于写操作或长任务时进入审批：服务端挂起请求，页面弹窗，用户在超时（默认 5 分钟）内决定；拒绝或超时都按失败返回，不自动放行。
4. 统一超时、输出截断和进程树终止，复用 `runner.stop_process` 的 `taskkill /T /F` 方式，只操作本次持有句柄的进程。
5. 工作目录必须在工作区根内；命令不允许 `..` 越界参数。

### Verifier

```python
verifier = Verifier(steps=[
    Step("build", ["dotnet", "build"], pattern=r"Build succeeded"),
    Step("test",  ["dotnet", "test"],  pattern=r"Passed!\s+-\s+Failed:\s+0"),
])
```

ZX2200 的固定四步作为该接口的一个实现保留，输出契约（`verification.json`、artifacts 哈希、报告校验）不变。

## 五、就地模式的安全模型

就地模式直接改真实文件，必须补上“只写副本”原本提供的保证：

1. **写盘前快照**：每次模型写入前，把该文件当前内容写入本对话的 blob 目录；等同于现有 `history` 机制，不依赖 git。
2. **还原入口**：面板提供“还原本次改动/还原该文件”，绑定精确版本，版本不符则拒绝。
3. **可选 git**：工作区是 git 仓库时，面板显示当前分支与未提交改动数量，并给出 `git diff` 只读视图；系统不自动 commit、不自动 stash，避免污染用户历史。
4. **命令审批**：见上，默认要求审批，白名单命中也不放开任意参数。
5. **不提供 OS 沙箱**：与现状一致，就地模式仍是本机用户权限，文档与界面必须明示。
6. **互斥**：同一对话同一时刻只允许一个写操作或一条命令；切换会话不打断已在执行的命令，但禁止并行写入。

## 六、数据与兼容

- 现有 `data/scratch/cw/<hash>/state.json` 增加 `mode: "scratch"`，缺省按 `scratch` 解释；旧副本无需迁移即可读取。
- 就地模式的对话状态放在 `data/scratch/lw/<hash>/state.json`，只保存 journal、审批记录与验证结果，不复制工作区文件。
- API 保持向后兼容：`/code-work` 全部保留；新增 `/local-work`。两个前缀共用同一套响应结构，前端按 `mode` 渲染差异。
- 现有前端挂载点（回答下方摘要、右侧工作区）不变，仅增加模式来源。

## 七、分阶段实施

### 第一阶段：内核抽取（行为不变）

- [ ] 新建 `modules/coding/`：`policy.py`、`editor.py`、`journal.py`、`diff.py`、`guard.py`。
- [ ] `code_work` 改为调用内核，ZX2200 规则迁移为默认策略常量。
- [ ] 现有 API、状态结构、验证流程、前端一律不动。
- 退出条件：`backend/tests/unit/code_work` 全绿；`ruff` 通过；前端 `npm test` 与 `npm run build` 通过；手工对照一份真实副本的差异与验证报告，内容与改造前一致。

### 第二阶段：受控命令执行

- [ ] `commands.py` 与单元测试：白名单命中/未命中、审批同意/拒绝/超时、超时终止、输出截断、进程树终止、cwd 越界拒绝。
- [ ] 审批挂起/决定接口与前端最小可用弹窗。
- 退出条件：上述反例全部覆盖；无审批不执行任何非白名单命令。

### 第三阶段：就地工作区与工具

- [ ] `local_work` 服务、路由、状态结构、写盘前快照与还原。
- [ ] 工具集：准备、读、写、编辑、搜索、执行命令、查看状态、还原。
- [ ] 与严格模式互斥、权限与项目隔离。
- 退出条件：在临时目录完成“写→差异→还原→再写”的往返；崩溃后状态可恢复；路径越界与链接被拒绝。

### 第四阶段：前端与收尾

- [ ] 面板模式切换、审批弹窗、还原入口、命令输出展示。
- [ ] ZX2200 适配器降级为预置方案，文档标明“预置方案”而非“唯一来源”。
- [ ] 更新 `agent.md`、`docs/features/code-work.md`，补验收记录。
- 退出条件：两模式在浏览器中可切换并各自完成一次真实流程。

## 八、验收口径

- 回归：后端完整 pytest、前端 `npm test`、TypeScript 与生产构建、Ruff。
- 安全反例：路径穿越、符号链接、硬链接、cwd 越界、非白名单可执行、审批超时、并发写。
- 一致性：同一份改动在两种模式下产生的差异文本一致；严格模式的合并与回退仍通过现有 `test_merging.py`。
- 数据：正式 `trunk/` 只读，指纹不变；正式数据目录不被测试写入。

## 九、不做与未决

- 不做“任意新建工程/解决方案”：`PROJECT` 虽改由策略提供，但本期只接受管理员配置的单个可信工程；多工程另行评审。
- 不做远程执行、容器或 OS 级沙箱。
- 不自动 commit/stash；不替用户管理 git 历史。
- 未决：审批超时后是否允许“重新发起”（倾向需要用户明确再次确认）；就地模式默认关闭还是默认开启（倾向默认关闭，由管理员或项目配置启用）。
