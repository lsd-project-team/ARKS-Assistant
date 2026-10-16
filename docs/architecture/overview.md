# 工程结构与依赖约定

项目采用模块化单体。React 前端和 FastAPI 后端独立组织，保留 SQLite、现有 API 和 Windows 启动入口。业务源码 `trunk/` 及正式运行数据 `data/` 不随代码目录迁移。

## 后端

- `app/main.py`：ASGI 入口。
- `app/bootstrap.py`：应用装配、依赖创建与生命周期。
- `app/core/`：配置、日志、身份标识等基础约定。
- `app/modules/`：账号、聊天、项目、源码分析、隔离代码修改、知识、记忆、交接、设置与管理业务。
- `app/agents/`：模型运行编排、工具、上下文与分析控制。
- `app/infrastructure/`：数据库、模型协议、MCP、存储和通用缓存。

各业务模块拥有自己的 ORM 模型。`infrastructure/database/base.py` 保留唯一元数据基类，`registry.py` 统一注册所有表。表名、索引和迁移历史不因代码归属变化而改变。

交接模块分为 `domain`、`application`、`infrastructure` 和 `interfaces`。领域规则不导入 FastAPI、SQLAlchemy、供应商 SDK 或应用启动代码。HTTP 接收请求后调用应用用例，持久化实现调用领域规则保护版本与状态。

交接应用层通过 `application/ports.py` 接收仓储、文档解析、交接包导出和候选生成接口。Word/PDF/ZIP 解析位于 `infrastructure/parsers/`，OOXML/ZIP 导出位于 `infrastructure/exporters/`，模型连接与输出适配位于 `infrastructure/ai.py`。应用层不创建 SQLAlchemy 会话或具体仓储，不直接连接模型供应商。请求命令归 `application/commands.py`，业务内容约束归 `domain/`。

`interfaces/http/` 按概览、记录、资料、调试问题、候选、交接包和复核拆分；对外仍使用原来的 `/api/handover` 地址。任务通过通用记录用例处理，统计规则保留在领域层，不为空建一套重复接口。

Agent 的入口、图构建、执行器和提示词分别维护。聊天、源码和调试录入工具按职责分开；运行取消、断线事件重放、检查点恢复与模型连接释放继续沿用原协议。

项目阅读任务及成果位于 `source_analysis/reading/`；隔离副本、补丁与验证命令档案位于 `code_changes/`。模型适配与工具回填归 `agents/`，项目与调试经验的关联由显式项目服务协调。原件只读；聊天临时产物按会话隔离，不与代码修改副本共享文件工具根目录。功能和边界见[代码工作](../features/code-work.md)。

## 前端

- `src/app/`：入口组装、布局、路由和跨业务状态装配。
- `src/features/`：按业务归属组织组件、请求、状态、规则和样式。
- `src/shared/`：通用 UI、请求封装、基础类型与主题。

聊天、项目、源码阅读和布局状态分别维护，通过应用层组合。原持久化键、账号隔离、草稿及文件阅读恢复行为继续保留。

交接前端的资料、任务、调试问题、候选、交接包和复核分别归类。记录查看与编辑由 `records/` 协调，共用卡片放在交接模块内部的 `shared/`。全应用的 `src/shared/` 不导入 `app/` 或 `features/`；带源码引用等业务交互的 Markdown 组合组件归应用层。

## 资源与脚本

- `resources/knowledge/flows/`：原 `/archify/` 图谱与复核资源。
- `resources/knowledge/modules/`：原 `/engineering/` 索引与源码说明资源。
- `resources/knowledge/generated/`：Agent 使用的生成索引。
- `frontend/scripts/knowledge/`：资源映射、校验、生成与构建发布。
- `scripts/dev/`：本机环境和服务管理。
- `scripts/maintenance/`：账号与数据维护。
- `scripts/verification/`：显式模型验收和数据保护检查。

Vite 开发与构建使用同一资源映射，公开 URL 保持不变。正式服务读取构建结果，后端知识检索读取统一生成索引。根目录启动脚本及原备份恢复命令保留为薄入口。

构建产物和验收产物写入 `output/`；正式前端发布目录为 `frontend/dist/`，旧哈希资源按发布兼容要求保留。

## 测试

后端测试分为 `tests/unit/`、`tests/integration/` 和 `tests/architecture/`，再按业务归类。共享测试模型、账号登录和 API 路径辅助位于 `tests/helpers/`。默认测试只使用隔离目录和可确定复现的测试模型。

前端测试位于 `frontend/tests/` 的业务子目录，`npm test` 通过 `scripts/test.mjs` 递归发现全部测试，避免移动文件后遗漏用例。TypeScript 检查和 Vite 生产构建使用同一套源码及知识资源映射。

实际供应商验收脚本位于 `scripts/verification/`，需要显式执行；默认回归不会自动消耗真实模型 API。

## 依赖边界

1. 业务模块不依赖应用启动装配。
2. 领域规则不依赖 HTTP、数据库和模型连接。
3. 通用 UI 与基础请求代码不承担具体业务流程。
4. 跨业务协调集中在应用装配或显式服务接口。
5. 构建产物、正式数据和被分析源码不能成为开发时的代码导入目录。

当前迁移进度及验收结果见 [重构清单](refactoring.md)。
