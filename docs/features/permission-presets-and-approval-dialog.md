# 任务书：权限三档 + 审批确认弹窗

- 状态：已实施（2026-11-13）
- 日期：2026-11-13
- 关联文档：[原地编码代理](in-place-coding-agent.md)
- 关联代码：`backend/app/modules/coding/`、`frontend/src/features/coding/`、`frontend/src/features/chat/`

## 1. 目标

1. 把现有的「写权限（enabled/writable）」和「审批档位（approval_mode）」两个旋钮，合成用户能直接理解的**三档权限**：仅可查看 / 工作区内修改 / 完全权限；在聊天头部提供一键切换，编码面板设置里同步展示。
2. 把命令审批从**聊天内联卡片**改为**全局模态确认弹窗**，交互对齐 Codex：标题一句话、命令单独等宽代码块、`Esc` 拒绝、`Enter` 允许一次、主按钮带下拉（本会话内允许）。
3. 保持后端接口与旧配置兼容，补齐单元测试、接口测试、前端测试与文档。

## 2. 非目标

- 不实现真正的操作系统沙箱或容器隔离（现有白名单仍是唯一约束）。
- 不放开文件 API 到项目外；「完全权限」仍只作用于项目目录内。
- 不做「始终允许」持久白名单、不做审批跨设备/跨账号同步。
- 不开放非管理员切换权限。

## 3. 现状与问题

### 3.1 后端

- 命令分类与放行：[executor.py](../../backend/app/modules/coding/executor.py) 的 `classify()` / `allowed()`；`ALLOW` 只含 `node --version`，`node -e ...` 会落到 `unknown` 而弹确认。
- 设置与写权限：[service.py](../../backend/app/modules/coding/service.py) 的 `DEFAULT_SETTINGS`、`MODES`、`save_settings()`、`writable()`、`_require_writable()`。
- 审批闭环：`request_approval()` / `decide_approval()` / `_wait_for_approval()`，`APPROVAL_TIMEOUT = 300`，事件 `coding_approval`。
- 审批只在工具有 `emit` 的 run 内推送，页面离开聊天后事件会断。

### 3.2 前端

- 审批状态存在 `useRunStream` 的局部 state（`approval`），聊天内联渲染 `CodingApprovalCard`（带「允许一次 / 拒绝」按钮）。
- 编码面板自带轮询 `['coding-approvals']`，与聊天内联卡片是两套入口，状态可能不同步。
- 现有 `Modal` 基于 Radix Dialog，但带固定头部和关闭 X，不适合审批场景。

### 3.3 问题

- 用户看到的是「聊天里突然多一张卡片」，打断阅读且容易被忽略；离开聊天页后审批入口也消失。
- 三档审批（白名单/全确认/全放行）和写权限正交，界面上要解释两层概念。

## 4. 已定决策（按此实施）

| 编号 | 决策 | 取值 |
| --- | --- | --- |
| D1 | 只读档遇到非只读命令 | 直接拒绝并返回明确提示，不创建审批 |
| D2 | 权限切换人 | 项目所有者（项目归属由分发层校验）；超时/构建命令等其它编码设置仍仅管理员 |
| D3 | 完全权限的范围 | 仍限项目内；命令除危险命令外直接执行，不弹确认 |
| D4 | 弹窗默认焦点 | 「允许一次」（与参考图和 `Enter` 语义一致）；`Esc` 始终拒绝 |
| D5 | 下拉选项 | P0 提供「允许一次」与「本会话内允许这条命令」；不做「始终允许」 |
| D6 | 队列 | 同一时刻只显示一条审批，其余排队并显示剩余数量 |
| D7 | 状态来源 | 全局 Host 轮询 `['coding-approvals']`（3s）+ SSE 收到 `coding_approval` 时失效重取 |
| D8 | 会话放行粒度 | `thread_id` + 完整命令字符串精确匹配；TTL 4 小时；切换权限即清空；不落盘 |

## 5. 权限三档

### 5.1 档位定义

| 界面档位 | 值 | 文件写 | 命令策略 | 审批 |
| --- | --- | --- | --- | --- |
| 仅可查看 | `read-only` | 全部拒绝 | 只跑只读命令白名单 | 不弹，直接拒绝 |
| 工作区内修改 | `workspace-write` | 项目内可写；`trunk` 只读目录仍需显式启用 | 现状 allowlist：安全命令自动，未知命令弹窗 | 未知命令弹 |
| 完全权限 | `full-access` | 项目内可写 | 除 `DANGEROUS` 外全部自动 | 不弹 |

`read-only` 下写文件/删除/移动/回滚/写命令的错误文案必须指向「切换到工作区内修改或完全权限」，不要只说「无权限」。

### 5.2 后端数据模型

`DEFAULT_SETTINGS` 增加：

```python
"permission": "workspace-write",   # read-only | workspace-write | full-access
```

- 保留 `approval_mode` 字段并继续写回（`read-only`/`workspace-write` → `allowlist`，`full-access` → `full`），供审计与旧前端读取。
- 保留 `enabled` 字段：仅用于 `trunk`（只读分析目录）的显式启用。
- `writable()` 改为：

```python
return self.permission() != "read-only" and (
    not root.is_relative_to(READONLY_ROOT) or bool(settings["enabled"])
)
```

- `settings()` 返回值增加 `permission`，其余字段不变。
- `save_settings(changes)`：
  - 校验 `permission in PERMISSIONS`；
  - 写入 `permission`，同步 `approval_mode`；
  - 切换后把仍在 pending 的审批标记为 `cancelled` 并 `_emit_approval`；
  - 清空所有会话放行集合；
  - 写审计 `action="permission"`，`command=f"{old} -> {new}"`；
  - 返回最新 `settings()`。

### 5.3 旧配置迁移

`load_settings()` 读取后如无 `permission`，按以下顺序推导（只在内存推导，下次保存时落盘，不在读取时写文件）：

1. `approval_mode == "full"` → `full-access`；
2. `writable()` 为真 → `workspace-write`；
3. 其余 → `read-only`（例如 `trunk` 下未启用编码的项目）。

### 5.4 执行策略

**`executor.py`**

- 新增 `policy`（`read-only` / `allowlist` / `full`），由 `service` 在 `save_settings()` 与构造时同步；保留 `mode` 作为兼容别名。
- 新增只读白名单：

```python
READONLY_ALLOW = [
    r"^(ls|dir|pwd|cat|type|head|tail|rg|grep|findstr)\b",
    r"^git\s+(status|diff|log|show|rev-parse)\b",
    r"^(where|which)\s+",
    r"^(pip|pip3)\s+(list|show)\b",
    r"^node\s+--version\b",
    r"^(dotnet|msbuild)\s+--(info|version|list-sdks)\b",
]
```

- 新增 `readonly_allowed(command)`：必须同时满足
  1. 不命中 `DANGEROUS`；
  2. `_escapes_project()` 为假；
  3. 不含 shell 连接符 `;`、`|`、`&`、`>`、`<`、反引号、`$(`；
  4. 命中 `READONLY_ALLOW` 任一模式。
- `allowed()` 按 `policy` 分支：`read-only` → `readonly_allowed()`；`allowlist` → 现状；`full` → `classify() != "dangerous"`。

**`service.py`**

- `run_command()`：
  - `read-only`：`readonly_allowed(command)` 为假时抛 `ValueError("当前权限为『仅可查看』，不能执行会改动文件或系统状态的命令；需要执行请先切换权限。")`，**不创建审批**；
  - `workspace-write`：`_require_writable()` 后按现状走审批；
  - `full-access`：不走审批，直接执行。
- `_execute_command()`：去掉 `_require_writable()`；仅当 `writable()` 时才 `snapshots.ensure()` 和命令前检查点。
- `start_process()`：`read-only` 一律拒绝（后台进程不能只读），`workspace-write` 保持 `_require_writable()`。
- 写文件、删除、移动、回滚等入口继续用 `_require_writable()`，只改文案。

### 5.5 会话内允许（D5/D8）

- `CodingWorkspace` 增加内存结构：`self.session_allow: dict[str, dict[str, float]]`（`thread_id` → `{command: 到期时间}`）。
- `run_command()` / `start_process()` 判断顺序：`allowed(command) or _session_allowed(command, thread_id)`；命中则跳过审批直接执行。
- `decide_approval(approval_id, approved, scope="once")`：批准且 `scope == "session"` 且有 `thread_id` 时，写入放行集合并把 `scope` 记到审批行。
- 清理：TTL 4 小时；单个线程最多 50 条；切换权限、删除对话（若有清理钩子）、服务重启即失效；不写入任何文件。

### 5.6 API 契约

`PUT /api/coding/settings`（管理员）：

```json
{ "permission": "workspace-write" }
```

- 响应：完整 `settings()`，含 `permission`、`approval_mode`、`writable`、`readonly`。
- 非管理员 403；非法值 422。
- `POST /api/coding/approvals/{id}` 请求体扩展：

```json
{ "approved": true, "scope": "once" }   // scope: once | session
```

- `CodingApproval` 增加 `scope?: "once" | "session"`（仅已决定的记录有值）。

### 5.7 审计与模型提示

- `_audit()` 行增加 `permission` 字段；审批通过时记录 `scope`。
- `graph_builder.py` 中「只读项目」提示按 `permission` 改写：
  - 只读：写入与写命令都会被拒绝，需要用户切换权限；
  - 工作区：可写、未知命令等待确认；
  - 完全：可写、命令直接执行，危险命令仍拒绝。
- `agents/tools/coding.py` 的 `CODING_GUIDANCE` 同步一句「当前权限决定可写与是否弹确认」。

## 6. 审批确认弹窗

### 6.1 视觉规格

- 全屏遮罩 `rgba(0,0,0,.35)`，卡片居中，宽 `min(600px, calc(100vw - 48px))`，圆角 12，阴影沿用现有 `--shadow`。
- 头部：16px 图标（`SquareTerminal`）+ 12px 来源标签「终端」/「后台进程」。
- 标题：18px，600 字重，「允许运行这条命令吗？」/「允许启动这个后台进程吗？」。
- 命令块：13px 等宽字体，浅底 `var(--surface-2)`，内边距 12，圆角 8，`max-height: 30vh`，`overflow: auto`，保留换行与空格，可选中。
- 元信息：12px muted，`目录：{cwd || '.'} · 一次性命令 / 后台常驻`。
- 底部：右对齐；「拒绝」次级按钮 + `kbd` Esc；「允许一次」主按钮 + `kbd` ↵ + 下拉箭头。

### 6.2 交互规格

| 行为 | 结果 |
| --- | --- |
| `Enter` | 允许一次（`scope="once"`） |
| `Esc` | 拒绝 |
| 点击遮罩 | 不关闭、不决策 |
| 点击 X | 不提供关闭按钮 |
| 决策中 | 两个按钮禁用，主按钮显示「处理中…」 |
| 多条待确认 | 左下角显示「还有 N 条待确认」；处理完自动弹下一条 |
| 待确认消失（超时/取消） | 自动关闭并 toast「该命令的确认已结束」 |
| 切换权限导致取消 | 同上 |

- 焦点：Radix 焦点锁；打开时聚焦「拒绝」（D4）；`Tab` 可在按钮与下拉间移动。
- 下拉菜单：`role="menu"`，两项「允许一次」「本会话内允许这条命令」，`Esc` 只关菜单不关弹窗。
- 无障碍：`Dialog.Title` 为标题，`aria-describedby` 指向命令块；命令块 `aria-label="待执行的命令"`。

### 6.3 状态来源

- 新增 `useApprovals()`：`useQuery(['coding-approvals', projectId])` 调 `GET /api/coding/approvals`，`refetchInterval: 3000`，`refetchOnWindowFocus: true`。
- 新增 `<ApprovalDialogHost />`，挂在 `App` 根节点（`<Toasts />` 旁），读 `useApprovals()`，取 `status === "pending"` 的第一条。
- `useRunStream` 的 `coding_approval` 改为 `invalidateQueries(['coding-approvals'])`，不再保存 `approval` state。
- 决策走 `useDecideApproval()`（POST 后失效 `['coding-approvals']`），面板和弹窗共用。
- 效果：人在知识库/交接页时也能收到弹窗；刷新页面后仍能从待确认列表恢复。

### 6.4 文案

- 标题：「允许运行这条命令吗？」
- 拒绝按钮：「拒绝」+ `Esc`
- 允许按钮：「允许一次」+ `↵`
- 下拉：「允许一次」「本会话内允许这条命令」
- 成功 toast：「已允许，命令开始执行」
- 拒绝 toast：「已拒绝，本轮不会执行这条命令」
- 只读档拒绝：「当前权限为『仅可查看』，需要执行命令请先切换权限」

## 7. 现有界面改造

1. `CodingApprovalCard`（[CodingApproval.tsx](../../frontend/src/features/chat/components/CodingApproval.tsx)）：删除两个按钮，改为状态条：
   - pending：「等待确认，请在弹出的确认框中处理」
   - approved：「已批准，正在执行…」
   - rejected / expired / cancelled：对应文案。
2. `ChatPane`：内联卡片数据改从 `useApprovals()` 取 `run_id === run.id` 的记录；头部「项目编码」按钮左侧新增 `<PermissionMenu />`。
3. `CodingPanel`：
   - 「待确认命令」保留按钮作为兜底，决策后共享 query 自动刷新；
   - 「编码设置」中的审批档位下拉替换为三档选择（与 `PermissionMenu` 共用选项定义）。
4. `PermissionMenu`：
   - 触发 chip：图标 + 当前档位短文案；管理员可点，非管理员只读展示（`title` 说明原因）。
   - 菜单三项，`role="menuitemradio"`，当前项打勾；
   - 切到「完全权限」前弹二次确认（说明会跳过命令确认）；
   - 切到「工作区内修改」且项目是 `trunk` 未启用时，提示「需要先启用编码」并一并提交 `enabled: true`（确认后）。
   - 乐观更新 + 失败回滚 + toast。

## 8. 文件改动清单

### 后端

| 文件 | 改动 |
| --- | --- |
| `backend/app/modules/coding/executor.py` | `policy`、`READONLY_ALLOW`、`readonly_allowed()`、`allowed()` 分支 |
| `backend/app/modules/coding/service.py` | `permission` 设置与迁移、`writable()`、`run_command`/`start_process` 分档、`_execute_command` 调整、审批取消、会话放行、`scope`、审计字段 |
| `backend/app/modules/coding/router.py` | `SettingsWrite.permission`、`ApprovalDecision.scope` |
| `backend/app/agents/runtime/graph_builder.py` | 只读/工作区/完全三套提示 |
| `backend/app/agents/tools/coding.py` | `CODING_GUIDANCE` 补权限说明 |
| `backend/tests/unit/coding/test_workspace.py` | 三档、迁移、只读拒绝、会话放行 |
| `backend/tests/integration/coding/test_api.py` | 权限接口 403/422、审批 scope |

### 前端

| 文件 | 改动 |
| --- | --- |
| `frontend/src/features/coding/PermissionMenu.tsx` | 新增：chip + 菜单 + 切换确认 |
| `frontend/src/features/coding/ApprovalDialog.tsx` | 新增：模态弹窗（Radix Dialog） |
| `frontend/src/features/coding/useApprovals.ts` | 新增：待确认查询、决策 mutation |
| `frontend/src/features/chat/components/CodingApproval.tsx` | 去按钮，改状态条 |
| `frontend/src/features/chat/components/ChatPane.tsx` | 挂 chip、内联卡数据来源、移除本地 approval |
| `frontend/src/features/chat/hooks/useRunStream.ts` | `coding_approval` 只做失效 |
| `frontend/src/features/coding/CodingPanel.tsx` | 三档选择替换下拉、共享决策 |
| `frontend/src/app/App.tsx` | 挂 `<ApprovalDialogHost />` |
| `frontend/src/shared/types/api.ts` | `CodingSettings.permission`、`CodingApproval.scope` |
| `frontend/src/features/coding/styles/*.css` | 弹窗与 chip 样式（若无可新建 `approval.css`） |

### 文档/测试

| 文件 | 改动 |
| --- | --- |
| `docs/features/in-place-coding-agent.md` | 新增 18.x 节：权限三档与弹窗 |
| `frontend/tests/coding/approval-dialog.test.mjs` | 键盘、队列、下拉 |
| `frontend/tests/coding/permission-menu.test.mjs` | 三档展示、管理员门禁 |

## 9. 测试计划

### 9.1 后端单测

1. 默认 `settings()["permission"] == "workspace-write"`。
2. 迁移：旧 `full` → `full-access`；可写 → `workspace-write`；`trunk` 未启用 → `read-only`。
3. `read-only`：写文件抛错；`git log` 可执行；`node -e ...` 抛错且 `list_approvals()` 为空。
4. `workspace-write`：`node -e ...` 返回 `approval_required`；批准后执行。
5. `full-access`：`node -e ...` 不建审批直接执行；`rm -rf` 仍拒绝。
6. 会话放行：`scope="session"` 批准后第二次相同命令不再弹；不同命令仍弹；切换权限后失效。
7. 切换权限会取消 pending 审批。

### 9.2 接口测试

- 非管理员 `PUT /api/coding/settings {"permission": ...}` → 403。
- 非法值 → 422。
- `POST /approvals/{id} {"approved": true, "scope": "session"}` → 生效并写入 `scope`。

### 9.3 前端测试（node:test + jsdom + esbuild，参照 `tests/chat/code-interaction.test.mjs`）

- 弹窗渲染命令、`Enter` 触发允许一次、`Esc` 触发拒绝。
- 下拉选择「本会话内允许」提交 `scope="session"`。
- 两条 pending 时显示第一条并展示剩余数量。
- 权限菜单三项、当前项打勾、非管理员只展示不可点。

### 9.4 手工验收

1. 工作区内修改：`node -e "console.log(1)"` 弹模态框；`Enter` 后命令执行，内联卡变已批准。
2. `Esc` 拒绝，模型收到拒绝状态且不重试。
3. 只读档：写文件被拒；`git log` 正常；非只读命令给出切换提示且不弹框。
4. 完全权限：同一命令直接执行，不弹框。
5. 待确认时切到知识库页面，弹窗仍在；刷新页面后仍弹出。
6. 权限切换后，头部 chip、面板设置、实际行为三者一致。
7. 旧项目（无 `permission` 字段）打开后档位推导正确。

## 10. 验收标准

- [ ] 三档权限可在聊天头部一键切换，仅管理员可操作。
- [ ] 只读/工作区/完全三档的写入与命令行为符合 5.1 表格。
- [ ] 旧配置文件可直接加载，无需手工迁移。
- [ ] 审批以模态弹窗呈现，`Enter`/`Esc`/下拉/队列/超时行为符合第 6 节。
- [ ] 聊天内联卡片不再有决策按钮，与弹窗状态一致。
- [ ] 后端单测、接口测试、前端测试全部通过；`npm run build` 通过。
- [ ] 文档更新完成，审计记录可查到权限切换与会话放行。

## 11. 实施顺序与工时

| 阶段 | 内容 | 预计 |
| --- | --- | --- |
| P1 | 后端 permission 模型、迁移、三档执行、API、单测 | 0.5 天 |
| P2 | 会话放行（scope=session）与测试 | 0.25 天 |
| P3 | `PermissionMenu` + 面板设置改造 | 0.5 天 |
| P4 | `ApprovalDialog` + 全局 Host + 卡片改造 | 0.75 天 |
| P5 | 前端测试、全量回归、手工验收 | 0.5 天 |
| P6 | 文档更新与收尾 | 0.25 天 |

合计约 2.75 天；P1 完成后即可先合入，P3/P4 可并行。

## 12. 风险与回滚

| 风险 | 缓解 |
| --- | --- |
| 迁移误判导致项目被锁成只读 | 迁移规则固定、`trunk` 需显式启用、chip 显示当前档位可立即切回 |
| 只读白名单误拒只读命令 | 拒绝文案给出切换路径；白名单集中在一处便于补充 |
| 弹窗打断输入 | 仅在有待确认时出现；`Esc` 可立即拒绝；决策后不再重复弹 |
| 会话放行被滥用 | 精确命令匹配、TTL 4h、上限 50 条、切换权限即清空、审计记录 |
| 轮询与 SSE 重复更新 | 统一 `['coding-approvals']` 单一数据源，SSE 只失效 |
| 权限接口被普通用户调用 | 复用 `require_admin`，前端同步隐藏入口 |

回滚：权限字段可回退为仅用 `approval_mode`；弹窗改动集中在新增组件与 `CodingApproval.tsx`，回滚该提交即可恢复内联按钮。

## 13. 开放问题

- 是否需要在弹窗中显示剩余确认时间（后端 300 秒超时）。
- 「本会话内允许」是否需要在界面上展示已放行的命令列表（当前只写审计）。
- 是否需要为只读档提供「临时允许一次」的越权入口（当前按 D1 不提供）。

## 14. 实施记录（2026-11-13）

- 已按本任务书完成：`permission` 三档、旧配置迁移、只读命令白名单、危险命令硬拒绝、`scope=session` 会话放行、权限切换取消待确认、审计字段。
- 前端完成：聊天头部权限 chip、编码面板内联三档、全局审批弹窗（`Enter`/`Esc`/下拉/排队/超时关闭）、内联卡片改为状态摘要。
- 相对任务书的偏差：
  - 弹窗默认焦点改为「允许一次」，与参考图和 `Enter` 语义一致（D4 已同步更新）。
  - 权限切换从「仅管理员」调整为「项目所有者可切换」（D2），新增 `PUT /coding/permission`；其它编码设置仍仅管理员。
  - 面板/API 直接发起、没有 `thread_id` 的审批，`scope=session` 会退化为一次性授权，下拉项在无对话线程时禁用。
  - 危险命令由「弹确认」改为任何档位直接拒绝，与 18.3 的既有文档描述一致。
- 测试结果：后端 `492` 条（单元 + 编码集成）通过；前端 `428` 条测试通过；`tsc -b` 与 `vite build` 通过。全量后端回归中 `13` 条模型 SDK/代理探测用例失败，已在干净 `HEAD` 上复现，属于本机 `httpx` 依赖的 URL 解析问题，与本次改动无关。
