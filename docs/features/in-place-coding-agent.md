# 原地编码 Agent 方案

更新日期：2026-11-12。状态：已实施（文件、快照、命令、审批、前端面板），旧副本与合并流程已移除。

把现有“副本 + 合并 + 管理员审核”的代码修改流程整体替换为原地编码 Agent：项目就是一个目录，会话在目录里直接读写文件、执行命令、用 Git 快照回滚。目标是 Codex 一类编程助手的体验，而不是受控的代码副本审批。

## 1. 目标

1. 新建项目 = 选择或新建一个目录（可以为空），选择后立即可编码，不再有“管理员先配置执行环境”的前置。
2. 会话绑定项目，工具直接作用于项目目录，不做整树复制，不经过合并与写回审批。
3. Agent 能列目录、新建/移动/删除文件与目录、读写文本、搜索内容，能执行构建、测试、安装依赖和启动服务。
4. 每次写入前后可追溯、可撤销：按文件、按轮次、回到基线三级回滚。
5. 多会话共享同一个项目目录时串行写入，避免互相覆盖。

## 2. 非目标

- 不提供操作系统级安全沙箱；对不可信仓库或不可信账号仍需虚拟机/容器隔离（后续可接）。
- 不在本轮支持远程仓库托管、PR、CI 集成。
- 不保留旧的副本、合并预览、候选验证、需求断言、桌面流程和固定 C# 验证宿主。

## 3. 模型与术语

| 术语 | 含义 |
| --- | --- |
| 项目 | 一个本机目录（`Project.source_root`），编码的唯一工作区 |
| 会话 | 一个对话（Thread），属于某个项目，共享该项目工作区 |
| 轮次 | 一次用户请求对应的运行（Run） |
| 检查点 | 一轮结束时的 Git 提交，带会话与轮次标签 |
| 审批规则 | 命令是否放行的判断，按项目、按命令模式保存 |

## 4. 总体架构

```
前端（聊天 / 变更面板 / 审批弹窗 / 运行面板）
        │  SSE：工具事件、命令输出、检查点
        ▼
coding 模块
  ├─ tools.py       文件与命令工具（模型调用入口）
  ├─ files.py       路径校验、编码、原子写、二进制判断
  ├─ executor.py    命令执行、超时、进程树、后台任务
  ├─ approvals.py   审批策略、白名单、危险模式
  ├─ snapshots.py   Git 快照、diff、回滚、清理
  └─ router.py      /api/p/{project}/coding/*
        │
        ├─ 项目目录（原地读写）
        └─ data/coding/snapshots/{project}/repo.git（工作区外）
```

现有 `app/modules/code_work/` 整体退役，新模块放在 `app/modules/coding/`。`Project` 表继续承载目录和归属；编码相关配置放新表，避免改动核心表。

## 5. 项目与目录

- 创建项目：`POST /api/projects` 接受 `source_root`；普通账号可以填本机绝对路径（按本次决定），路径不存在时可选择创建空目录。
- 目录允许为空。主工程、语言、构建方式改为“尽量识别”，识别失败不阻塞编码，只影响默认构建命令建议。
- 项目编辑可更换目录；更换时若旧目录仍有未提交的工作区改动，先建检查点再切换，不自动删除旧目录。
- 删除项目只删项目档案，不删除源码目录；目录清理单独确认。
- 项目级设置：审批档位、命令白名单补充、默认超时、构建/测试命令（可空，由 Agent 提议）。

## 6. 工具集

所有工具只接受项目内相对路径，根为项目目录。工具描述面向模型，中文提示与现有风格一致。

| 工具 | 参数 | 行为 | 默认审批 |
| --- | --- | --- | --- |
| `list_files` | `path="."`、`depth=2`、`pattern=""` | 列目录树，忽略构建产物与版本库目录 | 自动 |
| `read_file` | `path`、`start_line`、`end_line` | 读文本，返回行号、编码、哈希 | 自动 |
| `view_image` | `path` | 直接查看项目内图片（截图、设计图），作为用户消息交给支持视觉的模型 | 自动 |
| `search_files` | `query`、`path="."`、`glob=""` | 按内容搜索，返回路径与行 | 自动 |
| `write_file` | `path`、`content`、`expected_hash=""` | 新建或覆盖文本；已有文件必须带哈希 | 自动（有快照） |
| `create_directory` | `path` | 建目录（含父级） | 自动 |
| `move_path` | `from`、`to` | 移动/重命名文件或目录 | 自动（有快照） |
| `delete_path` | `path`、`recursive=false` | 删除；目录必须显式 recursive | 确认 |
| `run_command` | `command`、`cwd="."`、`timeout=120` | 前台执行，返回退出码与输出摘要 | 按审批档 |
| `start_process` | `command`、`cwd="."`、`name` | 后台常驻，返回 job id | 确认 |
| `read_process` | `job_id`、`lines=100` | 读取后台输出尾部 | 自动 |
| `stop_process` | `job_id` | 结束进程树 | 自动 |
| `list_checkpoints` | `limit=20` | 列检查点（轮次、时间、文件数） | 自动 |
| `diff_checkpoint` | `from`、`to`、`path=""` | 返回差异摘要与文本差异 | 自动 |
| `restore` | `checkpoint`、`paths=[]` | 回滚到检查点；为空表示整个项目 | 确认 |

约束：

- 单文件读写上限 2 MB；二进制文件拒绝读取，返回大小与类型。
- `view_image` 读取项目内 PNG/JPG/GIF/WebP（按文件内容判断，单边 ≤8192 像素、单文件 ≤32 MB）；超过 2048 像素或 4 MB 时先在本机压缩。图片块只在该次模型请求时展开，检查点保存文本标记；同一项目后续轮次会重新带上历史图片。
- 写入使用临时文件 + 原子替换，保留原换行与 BOM（复用现有 `encode_text` 逻辑）。
- 删除、移动前自动建检查点；同一轮内多次写只建一个轮次检查点。
- 读取超过 500 行时分页，提示模型继续读取。
- 工具调用统一发 `coding` 事件给前端，记录参数摘要、耗时与结果状态。

## 7. 命令执行

### 7.1 执行器

- 每个命令新起进程，`cwd` 解析到项目内（`Path.resolve()` 后必须 `is_relative_to(project)`）。
- Windows 默认用 `powershell.exe -NoProfile -NonInteractive -Command`，启动前设置 UTF-8 输出；`cmd` 通过显式 `cmd /c` 使用。
- 超时与取消使用 `taskkill /PID <pid> /T /F` 结束整棵进程树；不给父进程留孤儿。
- 输出写入 `data/coding/logs/{project}/{job_id}.log`，流式推送尾部到前端；模型只接收截断后的摘要（最后 200 行或 8 KB），需要更多时使用 `read_process` 或读日志。
- 退出码、耗时、命令、cwd、会话、轮次写入审计表。

### 7.2 审批档位（项目级，会话可临时提升）

| 档位 | 行为 |
| --- | --- |
| 白名单（默认） | 白名单内自动执行，其他逐条确认 |
| 全部确认 | 所有命令逐条确认 |
| 全部放行 | 不确认，但硬禁清单仍然拦截 |

默认档位即“白名单”：读取类、构建测试类自动；写文件、删目录、安装依赖、网络访问、启动常驻服务、修改系统配置一律确认。

### 7.3 白名单与危险模式

自动放行示例：`ls`、`dir`、`cat`、`rg`、`git status/diff/log`、`dotnet build/test`、`npm test`、`pytest`、`python -m unittest`。

强制确认：`rm`/`del`、`rmdir`、`move`、`copy` 覆盖、`npm install`/`pip install`、`curl`/`wget`/`Invoke-WebRequest`、`git clean/reset --hard`、`reg`、`sc`、`schtasks`、`net`、`shutdown`、`diskpart`、`format`。

硬禁（任何档位都拒绝）：格式化为空、删除盘符根、修改系统目录、写入项目外路径、`curl | bash` 类管道执行。

命令解析采用“按 token 前缀 + 风险关键字”的保守策略，宁可多问；确认弹窗展示完整命令、cwd 与命中的风险原因。

### 7.4 后台常驻

- `start_process` 返回 job id，日志独立文件，可 tail、可停止；同一项目限制并发后台任务数（默认 5）。
- 项目切换、会话删除、服务重启时结束该项目全部后台进程，并把状态标记为 interrupted。
- 常驻进程不占用前台命令锁，但仍计入项目并发上限。

### 7.5 环境与边界

- 子进程只继承最小环境：`PATH`、`SystemRoot`、`TEMP`、`USERPROFILE`、语言与编码变量；不注入模型密钥、数据库路径和助手配置。
- 每次执行前记录项目目录哈希与 Git 状态，便于事后定位。
- 明确写入文档：这是防误操作，不是安全沙箱。

### 7.6 并发与锁

- 每个项目一把可重入锁：写文件、删改路径、Git 操作、前台命令串行；读操作并发。
- 锁被占用时，前端显示“另一个会话正在执行”，用户可等待或取消。
- 锁持有超时（默认 10 分钟）自动释放并记录异常。

### 7.7 审计

`coding_commands` 表：`id`、`project_id`、`thread_id`、`run_id`、`command`、`cwd`、`mode`、`approved_by`、`exit_code`、`duration_ms`、`output_digest`、`created_at`。管理员可查。

## 8. 快照与回滚

### 8.1 Git 布局

- 快照仓库位于 `data/coding/snapshots/{project_id}/repo`，**不在项目目录放 `.git`**。
- 所有 Git 调用使用 `git --git-dir=<repo> --work-tree=<project>`，项目目录保持原样。
- 首次编码前初始化并提交基线；仓库与项目目录的对应关系写入项目配置，目录变更时新建仓库并保留旧仓库。

### 8.2 排除规则

写在仓库 `info/exclude`，不修改项目内文件：`bin/`、`obj/`、`packages/`、`node_modules/`、`.vs/`、`*.user`、`*.suo`、`*.log`、`.git/`、`.svn/`。

### 8.3 检查点时机

| 时机 | 行为 |
| --- | --- |
| 项目首次编码 | 建基线提交 |
| 每轮结束（有写入） | 提交检查点，消息带 `run:<id>` 与 `thread:<id>` |
| 删除/移动前 | 立即提交“pre-destructive”检查点 |
| 回滚后 | 提交“restore”检查点，历史不丢 |

### 8.4 回滚

| 操作 | 实现 |
| --- | --- |
| 撤销单文件 | `git checkout <checkpoint> -- <path>` |
| 撤销单轮 | 计算该轮 diff 后反向应用并提交，历史保留 |
| 回到基线 | 预览新增/修改/删除清单，确认后恢复内容并删除该轮后新增的文件 |
| 恢复被删文件 | 从检查点 checkout |

回滚前若工作区有未提交改动，先自动建检查点；回滚操作需要用户确认，并展示将影响的文件列表。

### 8.5 清理与失败

- 保留基线、最近 100 个检查点以及所有手动标记的检查点；其余提交由每日任务 `git gc` 清理。
- 仓库损坏时提示并重建基线，历史丢失需明确告知；项目目录不受影响。
- Git 不可用时退化为逐文件备份（写入前保存旧内容），仅支持单文件与单轮回滚。

### 8.6 大仓库

首次基线提交可能较慢。排除构建产物后按文件数分级：超过 2 万文件时首次建仓库改为后台任务并显示进度；模型在此期间可以读写文件，但检查点延后。

## 9. 数据模型

新表（Alembic 迁移）：

| 表 | 主要字段 |
| --- | --- |
| `coding_settings` | `project_id` PK、`approval_mode`、`timeout_seconds`、`build_command`、`test_command`、`snapshot_state`、`snapshot_repo` |
| `coding_rules` | `id`、`project_id`、`pattern`、`decision`、`scope`、`created_by`、`created_at` |
| `coding_commands` | 审计字段见 7.7 |
| `coding_jobs` | `id`、`project_id`、`thread_id`、`command`、`pid`、`status`、`log_path`、`started_at`、`ended_at` |
| `coding_checkpoints` | `id`、`project_id`、`commit`、`run_id`、`thread_id`、`label`、`files`、`created_at` |

旧表 `code_work_policies`、`code_work_usage`、`code_work_reservations` 迁移时保留只读后删除。

## 10. API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST | `/api/p/{project}/coding/settings` | 审批档、超时、构建/测试命令 |
| GET | `/api/p/{project}/coding/tree` | 目录树 |
| GET | `/api/p/{project}/coding/file` | 读取文件 |
| POST | `/api/p/{project}/coding/search` | 内容搜索 |
| POST | `/api/p/{project}/coding/command` | 前台命令（带审批 token） |
| POST | `/api/p/{project}/coding/command/{id}/approve` | 审批通过/拒绝 |
| POST | `/api/p/{project}/coding/process` | 启动后台 |
| GET/DELETE | `/api/p/{project}/coding/process/{id}` | 读取/停止 |
| GET | `/api/p/{project}/coding/checkpoints` | 检查点列表 |
| GET | `/api/p/{project}/coding/diff` | 检查点或工作区差异 |
| POST | `/api/p/{project}/coding/restore` | 回滚 |
| GET | `/api/p/{project}/coding/audit` | 管理员审计 |

工具调用与命令执行通过 SSE 事件推送：`coding_tool`、`coding_output`、`coding_approval`、`coding_checkpoint`。

## 11. 前端

- **新建项目**：名称 + 目录输入（带服务器目录浏览，逐级选择或新建空目录），创建后显示“可编码”。
- **项目卡片**：目录、识别到的语言/构建方式、最后检查点时间。
- **变更面板**：检查点选择、文件列表、逐文件 diff、撤销单文件、回到本轮之前、回到基线。
- **审批弹窗**：命令、cwd、命中的风险原因、允许一次/本会话/本项目/拒绝；等待期间可看到实时输出。
- **运行面板**：后台任务列表、日志 tail、停止。
- **工具事件**：聊天里的工具调用折叠展示，含参数摘要与结果状态。

## 12. 旧流程移除

| 范围 | 处理 |
| --- | --- |
| `code_work/merging.py`、`merge_text.py`、`transactions.py`、`recovery.py`、`checks.py`、`harness/`、`runner.py`、`history.py`、`environment.py`、`files.py` 中的编辑范围规则 | 删除 |
| `code_work/router.py` 的合并、验证、需求、桌面流程、环境接口 | 删除 |
| 前端 `CodeWorkDialog`、合并面板、需求面板、验证报告、环境面板 | 删除 |
| DB 旧表 | 迁移后删除 |
| `data/scratch/cw` 旧副本 | 保留一个版本供查看，提供清理脚本 |
| 工具提示词 | 重写为通用编码指导，删除 C#/Simulation 专用规则 |
| 文档 | `docs/features/code-work.md` 归档，新增本文件为现行说明 |

## 13. 迁移

- 现有项目保留 `source_root`，直接成为可编码项目；默认项目沿用 trunk。
- 现有环境配置中的 `msbuild` 转为项目级“构建命令”默认值（`dotnet build` 或 msbuild 路径），超时沿用。
- 旧副本与合并记录不迁移，保留只读；首次在新流程中操作项目时建立快照基线。
- 旧对话历史不受影响；历史回复里的“查看变更”入口隐藏，避免指向已删除的副本。

## 14. 阶段与验收

| 阶段 | 内容 | 验收 |
| --- | --- | --- |
| P1 项目与文件 | 目录即项目、通用文件工具、原地写、原子写、编码保持 | 空目录建项目；Agent 创建多层目录与文件；读取哈希校验；超限与二进制拒绝 |
| P2 快照 | Git 仓库、基线、轮次检查点、diff、单文件/单轮/基线回滚 | 新建文件后回滚消失；修改后回滚恢复原文；删除后可从检查点恢复 |
| P3 命令 | 前台执行、超时、进程树、审批三档、白名单、审计 | 白名单自动跑测试；非白名单弹出确认；超时结束子进程；审计有记录 |
| P4 后台 | 常驻进程、日志 tail、停止、并发上限、退出清理 | 启动 dev server 后可访问；停止后端口释放；会话删除后进程结束 |
| P5 切换 | 删除旧流程、前端改造、迁移、文档 | 旧接口 404；新建项目到改代码全链路可用；旧数据可读 |

每个阶段都要有对应的单元测试、接口测试和一次真实目录的人工验收；P5 完成后跑全量回归并更新 `agent.md`。

## 15. 测试

- 单元：路径越界、编码（UTF-8/GBK/BOM）、原子写、危险命令识别、审批规则匹配、超时与取消。
- 集成：建项目→写文件→检查点→diff→回滚；命令审批通过/拒绝；后台进程起停；并发会话锁。
- 端到端：空目录 + “做一个通信协议的配置页面”，Agent 自动建结构、写文件、跑构建/起服务，用户能看到 diff 并回滚。
- 回归：现有认证、项目、聊天、备份测试保持通过；备份改为包含 `coding/` 日志与快照元数据（快照仓库可按策略排除）。

## 16. 风险

| 风险 | 缓解 |
| --- | --- |
| 任意命令破坏系统 | 项目目录限制、危险命令确认、硬禁清单、审计；还不是沙箱 |
| 模型误删文件 | 删除走工具并先建检查点；shell 删除需确认 |
| 大仓库首次快照慢 | 排除构建产物、后台建库、显示进度 |
| 多会话并发写冲突 | 项目级写锁与串行 Git |
| Git 不可用 | 降级逐文件备份 |
| 旧数据丢失 | 旧表只读保留一版、副本保留清理脚本 |
| 长命令占满模型上下文 | 只回传截断摘要，日志落文件分页读取 |

## 17. 开放问题

- 是否需要“项目允许目录”白名单（当前按决定放开任意本机路径）。
- 是否在后续接入容器或 Windows 受限令牌作为真沙箱。
- 是否需要把检查点仓库纳入备份包（体积与恢复时长的取舍）。

## 18. 2026-11-13 完善

在第一版"能改代码"的基础上补齐审批闭环、编辑体验和安全边界。现行行为以本节为准。

### 18.1 审批闭环

- `run_command` / `start_process` 遇到需要确认的命令时，不再结束本轮：工具在工作线程内等待用户在聊天内联卡片或编码面板中决定，最长 300 秒。
- 用户批准后由同一轮继续执行，模型直接拿到退出码和输出；拒绝、超时、取消都返回明确状态，模型不会反复重试。
- 审批事件 `coding_approval` 通过 SSE 推送，卡片展示命令、目录、一次性/后台类型；批准/拒绝后回填结果。
- `start_process` 的审批按后台常驻执行，不再误当前台命令。
- 运行取消会同时结束等待中的审批和前台命令，不会留下子进程。

### 18.2 编辑与查找

- 新增 `edit_file`（精确替换，必须带读取得到的 version）、`multi_edit`（一次读取、一次原子写回多处替换）和 `write_binary_file`（base64 写入图片等资源）。
- 写入仍保留 UTF-8/UTF-16/GB18030、BOM 和原换行；替换遇到多处匹配要求更长上下文或 `replace_all`。
- 新增 `find_files` 按文件名查找；`search_files` 优先使用 ripgrep，返回同一文件的多个命中，缺少 ripgrep 时回退到剪枝遍历。
- 搜索、列表和快照共同排除 `bin/obj/node_modules/dist/build/out/target/coverage/.venv/__pycache__` 等构建与缓存目录。

### 18.3 命令执行

- 命令输出边执行边写入日志并通过 `coding_output` 推送到前端；结束后仍只向模型返回末尾 24 KB。
- 后台任务在自然退出后自动回收，不再占满 5 个并发额度；删除对话时结束该对话的后台任务。
- 每次执行前对未提交改动建 `before-command` 检查点，shell 删除或覆盖后可以恢复。
- 识别项目外绝对路径、环境变量、`..` 和 Windows 磁盘/分区命令；这类破坏性命令在任何档位都拒绝。
- 同一工具同参数连续三次被拦截；本轮编码工具总数超过 150 次时停止继续探查，要求模型基于已有结果总结。
- 命令启动前统一设置 UTF-8 输出，并让 `Get-Content` 默认按 UTF-8 读取源码，减少中文乱码。

### 18.4 检查点与回滚

- 检查点列表不再因只读项目或打开面板而创建快照；只读项目返回空列表并明确标记。
- 选中检查点显示该检查点自身引出的差异，而不是它到当前工作区的累计差异。
- 面板支持按检查点恢复整个项目或单个文件；回答末尾的"本次修改"新增"撤销本轮"，仅在该轮之后没有新检查点时允许。
- 检查点标签在界面中转换为"本轮开始/本轮完成/命令前存档"等可读文字。

### 18.5 设置与环境

- 编码面板新增管理员设置：权限档位（详见第 19 节）、超时、构建/测试命令、只读项目启用开关。
- 按目录中的 `.sln/.csproj`、`package.json`、`pyproject.toml`、`Cargo.toml`、`go.mod`、`pom.xml`、`build.gradle`、`CMakeLists.txt` 识别语言和默认构建/测试命令；已填写的命令优先。
- 识别结果进入本轮提示词，模型直接使用建议命令，减少重复探测环境。

### 18.6 安全与降级

- 只读分析目录（`trunk`）仍保留编码工具以保证解释与读取一致，但写入、删除、命令和回滚会被工作区统一拒绝，提示词也会明确告知模型当前只读；启用编码后才允许写入。
- `git` 不可用时不再让写入失败：禁用快照、保留文件读写，检查点相关操作返回不可用状态。
- 项目锁等待超过 10 分钟返回"另一个会话正在执行项目命令"，不再无限阻塞。

### 18.7 API 变化

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| PATCH | `/api/p/{project}/coding/file` | 精确编辑，body 含 `path`、`edits`、`expected_hash` |
| PUT | `/api/p/{project}/coding/binary` | base64 写入二进制资源 |
| GET | `/api/p/{project}/coding/find` | 按文件名查找 |
| GET | `/api/p/{project}/coding/diff?commit=` | 查看某个检查点自身的差异 |
| POST | `/api/p/{project}/coding/restore-run` | 撤销本轮修改 |
| GET | `/api/p/{project}/coding/approvals?recent=true` | 待确认和最近审批 |
| GET | `/api/p/{project}/coding/audit` | 管理员查看命令记录 |
| GET | `/api/runs/{run_id}/coding` | 只返回本轮修改，不再读取完整运行上下文 |

## 19. 2026-11-13 权限三档与审批弹窗

### 19.1 权限三档

- 聊天输入框工具栏（加号右侧）与编码面板提供三档权限：仅可查看（`read-only`）、工作区内修改（`workspace-write`）、完全权限（`full-access`）；项目所有者可切换，超时/构建命令等其它编码设置仍仅管理员可改。
- 仅可查看：写入、删除、移动、回滚、启动后台进程全部拒绝；命令只允许只读白名单（`ls/cat/rg/git status|diff|log`、`node --version` 等），包含 `; | & > <`、反引号或 `$(` 的命令直接拒绝，不进入审批。
- 工作区内修改：项目内可写（`trunk` 只读目录仍需显式启用）；安全命令自动执行，未知命令弹确认，破坏性命令拒绝。
- 完全权限：项目内可写；除危险命令外全部直接执行，不再弹确认。
- 危险命令（磁盘/分区/`git clean -f`/`git reset --hard`/访问项目外路径等）在任何档位都直接拒绝。
- 旧配置没有 `permission` 时自动推导：`approval_mode=full` → 完全权限；可写 → 工作区内修改；`trunk` 未启用 → 仅可查看；下次保存时落盘。旧的 `approval_mode=confirm` 归入工作区内修改。
- 切换权限会取消所有待确认请求并清空会话放行，同时写入审计（`action=permission`）。

### 19.2 审批确认弹窗

- 命令需要确认时不再只在聊天里显示内联按钮，而是弹出全局模态框，离开聊天页也会出现；`Esc` 拒绝、`Enter` 允许一次。
- 弹窗展示工具类型（终端/后台进程）、命令代码块、目录与类型；右下角为「拒绝」与「允许一次」，主按钮带下拉。
- 同一时刻只显示一条，其余显示「还有 N 条待确认」；待确认超时、取消或在别处处理完时弹窗自动关闭。
- 聊天内联卡片保留为状态摘要（等待确认/已批准/已拒绝/超时），不再提供决策按钮；编码面板的待确认列表仍可兜底处理。
- 数据源统一为 `GET /coding/approvals`（3 秒轮询 + `coding_approval` SSE 失效），面板与弹窗不会出现状态不一致。

### 19.3 会话内允许

- 弹窗下拉支持「本会话内允许这条命令」：按对话线程 + 完整命令精确匹配，4 小时过期，单线程最多 50 条，不落盘；切换权限或重启服务即失效。
- 没有对话线程的命令（面板/API 直接发起）只支持一次性授权；审批结果写入审计（`action=approve`，含 `scope`）。

### 19.4 API 变化

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| PUT | `/api/p/{project}/coding/settings` | 新增 `permission`：`read-only` / `workspace-write` / `full-access`（该接口仍仅管理员） |
| PUT | `/api/p/{project}/coding/permission` | 项目所有者切换权限档位，只接受 `permission` |
| POST | `/api/p/{project}/coding/approvals/{id}` | 请求体新增 `scope`：`once`（默认）/ `session` |

`GET /coding/settings` 与审批响应会返回 `permission`、`scope`；旧的 `approval_mode` 仍保留并自动同步。
