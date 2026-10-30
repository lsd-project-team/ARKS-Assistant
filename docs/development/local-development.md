# 本地运行与开发

本文说明 Windows 本机安装、启动选项、常见运行问题及开发检查。首次登录和模型连接见[快速开始](../../README.md#快速开始)，日常操作见[使用指南](../features/user-guide.md)。

## 环境与安装

- Windows 与 PowerShell。
- Git、Node.js 22.12+ 和 uv。
- Python 3.12 或 3.13，后端依赖由 uv 按 `backend/uv.lock` 安装。
- 可访问的模型服务、模型名称和相应凭据，由管理员在界面中配置。

在仓库根目录执行：

```powershell
.\Setup.ps1
.\Start.ps1
```

`Setup.ps1` 会安装锁定的后端与前端依赖、准备本地多语言检索模型、下载本地 .NET SDK 并构建 Roslyn 分析器，最后生成前端发布文件。它不会构建 `trunk/` 中的业务项目。

首次安装需要联网。离线环境已经备好应用依赖时，可跳过检索模型和分析器准备：

```powershell
.\Setup.ps1 -SkipSemanticModels
```

该参数不会跳过应用依赖安装；缺少本地检索模型或 C# 分析器时，相关功能会显示降级提示。已有前端构建且只需准备后端时，可使用 `-SkipFrontend`。

## 启动与停止

| 命令或入口               | 用途                           |
| ------------------------ | ------------------------------ |
| `.\Start.ps1`            | 启动后台服务并打开浏览器       |
| `Start.cmd`              | 依赖准备完成后，双击打开工作区 |
| `.\Start.ps1 -NoBrowser` | 启动服务，不自动打开浏览器     |
| `.\Start.ps1 -Port 8766` | 使用其他本机端口               |
| `.\Stop.ps1`             | 停止由启动脚本登记的服务       |

默认地址为 [http://127.0.0.1:8765](http://127.0.0.1:8765/)，健康检查为 `/api/health`，API 文档为 `/docs`。服务只监听本机地址。

启动前先检查已有服务，正常运行时复用现有实例。同一个数据目录只运行一个服务；使用其他端口时，也不要为同一数据目录启动第二个实例。

## 常见运行问题

### 提示先运行 Setup.ps1

启动脚本需要 `backend/.venv/Scripts/python.exe` 和 `frontend/dist/index.html`。在仓库根目录执行 `.\Setup.ps1`，确认安装与构建成功后再启动。

### 安装停在模型或分析器准备

检索模型和 .NET SDK 的首次准备需要下载。检查网络和安装输出；暂时不需要这些能力时，可使用 `-SkipSemanticModels` 完成其余安装。

### PowerShell 阻止脚本运行

先检查组织的脚本执行策略。允许在当前终端临时放行时，可执行以下命令，再重新运行安装或启动脚本：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

该设置仅作用于当前 PowerShell 进程。

### 无法登录或找不到初始密码

首次启动或账号初始化升级后，随机初始密码写入本机 `data/auth.initial-accounts.json`。`admin` 进入管理工作区，`user` 进入日常工作区；已有账号使用当前密码。

### 浏览器无法打开工作区

确认访问的端口与启动参数一致，并检查 `/api/health`。服务启动失败时查看本机 `data/server.stderr.log`；标准输出位于 `data/server.stdout.log`。

### 修改前端后页面没有更新

`Start.ps1` 提供的是 `frontend/dist/` 中的构建文件。修改源码后需重新构建；开发期间可以使用下面的 Vite 开发服务。

## 开发与检查

开发助手本身时修改 `backend/`、`frontend/` 等应用目录。`trunk/` 保持只读，`data/` 保存正式运行数据，测试与临时产物写入独立目录。

如果默认服务已经运行，先复用它或停止后再切换到开发启动方式，不要重复启动后端。后端在独立 PowerShell 终端运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

前端在另一个终端运行，Vite 会将 `/api` 代理至后端：

```powershell
cd frontend
npm run dev
```

按修改范围执行检查。后端命令在 `backend/` 目录运行：

```powershell
uv run pytest -q
uv run ruff check app tests migrations
```

前端命令在 `frontend/` 目录运行：

```powershell
npm test
npm run build
npx prettier --check src vite.config.ts
```

`npm run build` 包含 TypeScript 检查和 Vite 生产构建。仅修改文档时核对内容、路径和差异，无需重启服务或运行全量应用测试。真实供应商验收需要显式执行，不属于默认回归测试。

代码分层与文件归属见[工程结构](../architecture/overview.md)。开发前阅读[项目协作说明](../../agent.md)以及[开发](../../skills/project-development/SKILL.md)、[结构](../../skills/project-structure/SKILL.md)、[测试](../../skills/project-testing/SKILL.md)规范；完成修改后按仓库要求提交并推送到 GitHub。

## 运行数据

| 路径                         | 内容                                           |
| ---------------------------- | ---------------------------------------------- |
| `data/app.sqlite3`           | 对话、代码选区、运行事件、资料及其他业务数据   |
| `data/checkpoints.sqlite3`   | Agent 检查点                                   |
| `data/memories/`             | 跨会话 Markdown 记忆                           |
| `data/scratch/`              | 大工具结果与压缩档案                           |
| `data/settings.private.json` | 本机 API 密钥配置，不进入 Git 或应用导出的备份 |

备份从管理员“数据维护”导出。恢复前停止服务，使用 `scripts/RestoreData.ps1` 校验并应用备份，再启动；现有密钥配置会保留。具体步骤见[本地备份与恢复](backup-and-restore.md)。

[返回项目首页](../../README.md)
