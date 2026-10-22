<p align="center">
  <img src="frontend/public/brand/arks-assistant-icon.png" width="88" alt="ARKS 智能助手图标" />
</p>

<h1 align="center">ARKS 智能助手</h1>

<p align="center">
  <strong>面向源码阅读、问题排查与调试经验复用的 AI 工作区</strong>
</p>

<p align="center">Windows 本机运行 · 浏览器访问 · 自选模型服务</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="docs/features/user-guide.md">使用指南</a> ·
  <a href="docs/development/local-development.md">开发指南</a> ·
  <a href="https://github.com/lsd-project-team/ARKS-Assistant/issues">问题反馈</a>
</p>

ARKS 将源码、项目资料和历史调试记录放在同一个工作区。你可以一边阅读代码，一边让助手分析实现、梳理调用关系、提出修改建议，再把排查过程和处理办法保存下来，供后续检索和交接。

## 核心功能

- **结合源码分析问题**：搜索文件与符号，选中代码直接提问；C# 项目支持基于 Roslyn 的调用关系分析。
- **查看回答依据**：从回答跳转到源码位置或资料的固定版本，核对分析所依据的原文。
- **复用调试经验**：通过页面或 `/记录问题` 保存现场描述、排查过程与处理结果，后续按设备、版本和工况检索。
- **按项目组织工作**：集中管理对话、源码目录、资料和回答指令；个人项目与对话按账号隔离。
- **持续进行长对话**：支持历史搜索、跨会话记忆、上下文压缩，以及中断后的继续运行。
- **持续阅读与尝试实现**：按快照阅读项目并维护成果，在隔离副本中修改、检查差异、运行已配置测试并导出补丁。
- **整理资料与交接**：在交接工作台维护共享资料、任务进度和调试问题，生成交接包并保留版本历史。
- **查看动作耗时**：直接按 ZX2200 源码模拟逻辑计算，以表格展示各动作的耗时和简短说明，源码依据按需展开，支持工位筛选、名称搜索和表格导出，见[源码耗时分析说明](docs/features/action-timing.md)。

> 原源码工作区保持只读。“项目 → 代码工作”支持独立副本修改与配置命令验证；测试通过不代表设备验收。项目阅读会调用配置的模型，具体边界见[代码工作说明](docs/features/code-work.md)。

## 快速开始

### 1. 准备环境

使用 Windows 和 PowerShell，并安装 **Git、Node.js 22.12+、uv**。后端要求 Python 3.12 或 3.13，依赖由 uv 管理。

### 2. 安装并启动

```powershell
git clone https://github.com/lsd-project-team/ARKS-Assistant.git
cd ARKS-Assistant
.\Setup.ps1
.\Start.ps1
```

`Setup.ps1` 安装依赖、准备本地检索模型与 C# 分析器，并构建前端；首次运行需要联网下载相关依赖。

启动后浏览器会打开 **[http://127.0.0.1:8765](http://127.0.0.1:8765/)**。以后可直接双击 `Start.cmd`；停止服务运行 `.\Stop.ps1`。

### 3. 登录并连接模型

1. 在本机 `data/auth.initial-accounts.json` 查看首次生成的 `admin`、`user` 账号密码。
2. 使用 `admin` 登录，在“系统配置”中填写模型服务地址、模型名称和 API 密钥。支持 **OpenAI Chat Completions** 与 **Anthropic Messages** 协议。
3. 通过右上角账号菜单退出，使用普通用户账号进入日常工作区。管理员负责系统配置、账号和数据维护。

安装、端口或启动遇到问题，参见[本地运行与开发](docs/development/local-development.md)。

## 开始使用

1. **打开项目**：选择已有项目，或新建项目并关联源码目录；暂时不需要项目时，也可以直接开始独立对话。
2. **围绕代码提问**：在右侧文件树打开文件，选中代码并点击“将选区加入对话”，描述要分析的问题。
3. **保留有用经验**：在交接工作台登记调试问题，或在对话中输入 `/记录问题`，保存原始描述与处理过程。

你可以这样提问：

> 这个方法由哪些入口调用？请结合当前源码说明执行过程，并标出关键位置。
>
> 历史调试记录里有没有相同报警？请核对设备、版本和发生条件是否一致。

文件阅读、资料导入、知识来源、记忆和常用快捷键，详见[使用指南](docs/features/user-guide.md)。

## 数据与模型服务

应用默认仅监听本机地址，对话、资料、记忆和设置保存在 `data/`。模型问答与 DeepWiki 查询会访问配置的服务；发送给外部模型的内容取决于本轮使用的源码、资料和上下文。

API 密钥保存在本机 `data/settings.private.json`，Git 和应用导出的备份均排除该文件。备份与恢复操作见[本地备份与恢复](docs/development/backup-and-restore.md)。

## 文档导航

| 想了解什么                   | 从这里开始                                                                                                                       |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 日常操作、知识问答与调试记录 | [使用指南](docs/features/user-guide.md)                                                                                          |
| 安装选项、启动排查与开发检查 | [本地运行与开发](docs/development/local-development.md)                                                                          |
| 项目、源码目录与资料管理     | [项目功能](docs/features/projects.md)                                                                                            |
| 项目阅读、隔离修改与测试验证 | [代码工作](docs/features/code-work.md)                                                                                           |
| 账号角色与数据访问范围       | [账号与访问控制](docs/features/accounts-and-handover-access.md) · [项目与对话隔离](docs/features/account-workspace-isolation.md) |
| 本地数据备份与停服恢复       | [备份与恢复](docs/development/backup-and-restore.md)                                                                             |
| 公司 Linux 部署与迁移边界    | [Linux 部署](docs/development/linux-deployment.md)                                                                               |
| 代码结构与模块依赖           | [工程结构](docs/architecture/overview.md)                                                                                        |

## 参与开发

项目采用 **React + TypeScript + Vite** 前端、**Python + FastAPI** 后端，基于 **Deep Agents** 编排问答与工具调用，使用 **SQLite** 持久化业务数据。

应用代码位于 `frontend/` 和 `backend/`，知识资源位于 `resources/knowledge/`。详细目录和依赖方向见[工程结构](docs/architecture/overview.md)；`trunk/` 为被分析的只读业务源码，`data/` 为本机运行数据。

开始修改前请阅读[项目协作说明](agent.md)、[开发规范](skills/project-development/SKILL.md)、[项目结构规范](skills/project-structure/SKILL.md)和[测试规范](skills/project-testing/SKILL.md)。开发命令见[开发指南](docs/development/local-development.md#开发与检查)，历史重构与验收记录见[重构清单](docs/architecture/refactoring.md)。
