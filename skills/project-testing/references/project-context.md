# 本项目测试约定

本文件补充项目的实际配置、命令和数据边界。Python 测试方法以 [用户提供的新版规范](python-testing-standard.md) 为准。

## 先检查当前配置

- 后端配置为 `backend/pyproject.toml`；目前使用 pytest、pytest-asyncio，`asyncio_mode = "auto"`，测试发现目录为 `tests`。
- 先复用 `backend/tests/conftest.py`、`backend/tests/helpers/` 和相关业务测试，不把模块私有 fixture 全部上提为全局 fixture。
- 当前依赖文件未声明 pytest-cov、Hypothesis、mutmut。需要相应验证时先确认环境和任务范围，不直接假定插件可用或为文档任务安装依赖。
- 前端使用 `node:test`，通过 `frontend/scripts/test.mjs` 递归发现 `*.test.mjs`；不因 Python 规范引入另一套前端测试框架。
- 修改或移动代码后，patch 实际查找对象的位置。例如交接候选生成使用的 `create_model` 位于 `app.modules.handover.infrastructure.ai`，不能继续 patch 迁移前的位置。

## 测试归属

```text
backend/tests/
├─ unit/                    # 规则、算法、独立业务逻辑
├─ integration/             # 按业务组织的 API、数据库和流程测试
├─ architecture/            # 依赖与分层契约
├─ helpers/                 # 测试模型、登录与 API 路径辅助
└─ fixtures/                # 固定资料和依赖替身

frontend/tests/<业务>/      # 前端规则、状态与交互辅助测试
scripts/verification/       # 显式模型与专项验收
output/                     # 临时产物和报告
```

已有端到端流程测试可沿用既有归属；需要独立 E2E 层时再建立，不为空建目录，也不把所有测试变成 E2E。新增或迁移测试时核对它确实被收集。

## 现有命令

在 `backend/` 中使用项目虚拟环境，或等价的 `uv run` 命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/unit/handover
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check app tests migrations
.\.venv\Scripts\ruff.exe format --check app tests migrations
```

首条仅示范按范围选择测试，不是所有任务的固定入口。先跑相关用例；涉及公共能力、权限、迁移或大范围重构时，再跑相应集成与全量回归。

需要覆盖率且已具备 pytest-cov 时，可在 `backend/` 中执行：

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-branch --cov-report=term-missing
```

在 `frontend/` 中：

```powershell
npm test
npx tsc -b
npm run build
npx prettier --check src tests scripts vite.config.ts
```

涉及知识资源增加 `npm run knowledge:check`。真实供应商专项见 [验证脚本说明](../../../scripts/verification/README.md)。仅文档修改检查内容、格式和链接即可，不重跑整套应用测试。

## 数据与外部依赖

- 单元测试隔离外部依赖，真实执行目标逻辑。数据库和文件集成测试使用临时 SQLite、`tmp_path` 和真实事务，不用全套 Mock 冒充集成结果。
- 不向正式 `data/` 写入测试账号、对话、资料或记忆；不修改只读 `trunk/`，不为通过测试改变正式模型配置。
- 认证测试通过真实登录流程操作隔离账号，不绕过权限读取正式凭据。检查角色、账号和项目隔离，以及越权读写与固定版本引用。
- 默认使用测试模型和本地依赖替身，不自动连接真实供应商、远程 MCP 或设备；相关验收有明确任务范围时单独执行和报告。
- 服务生命周期测试使用独立数据目录与端口，只清理本测试创建的资源。跟踪仍在运行的原进程或会话，不把观察超时当作进程结束并重复启动。
- 反例或实际变异验证不覆盖用户未提交修改，优先使用隔离副本。设备案例不构成执行 `trunk/` 设备程序的授权。

## 报告边界

按新版规范第 32 节报告文件与用例数、Passed/Failed/Skipped、覆盖率、已测范围、缺陷、限制、未测风险和质量判断。未采集覆盖率写“未采集”，质量等级说明依据。

分别记录静态检查、编译、状态测试、API 集成、真实供应商调用、浏览器操作和设备验证的实际范围。历史报告不代替本轮执行证据；没有执行就不能报告通过。
