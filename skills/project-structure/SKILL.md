---
name: project-structure
description: 在 ARKS 智能助手新增模块、放置或移动文件、调整依赖、拆分接口与组件、进行架构审查时使用，维护模块化单体和交接模块的分层边界。
---

# 项目结构规范

## 使用边界

维护本项目已确认的模块化单体结构。先检查相关目录、调用方和未提交改动，再确定代码归属。只讨论结构时不移动文件；用户已授权调整时完成实现和验证，不重复请求确认。

本规范描述当前架构，用户明确要求改变架构时同步更新规范和文档。不要将目录示例变成强制创建空目录、重复接口或额外产品功能的理由。

## 根目录归属

```text
code_agent/
├─ backend/                 # FastAPI、业务模块、Agent 和源码分析工具
├─ frontend/                # React、TypeScript、Vite
├─ resources/knowledge/     # 应用自带知识资源
├─ scripts/                 # 开发、维护、显式验证脚本
├─ skills/                  # 开发、项目结构、测试规范
├─ docs/                    # 架构、功能、开发和验收文档
├─ trunk/                   # 被分析的业务源码，只读
├─ data/                    # 正式数据库、附件、记忆与本机配置
├─ output/                  # 临时产物、测试报告和历史构建
├─ .tools/                  # 本地运行依赖，不作为应用源码
├─ agent.md                 # 项目协作说明
└─ Setup.ps1 / Start.ps1 / Start.cmd / Stop.ps1
```

保持 `trunk/` 只读、`data/` 位置和正式数据不变。测试与生成产物不放入业务源码，不形成 `frontend/frontend/` 一类意外嵌套。

## 后端归属

| 位置 | 职责 |
| --- | --- |
| `backend/app/main.py` | ASGI 入口 |
| `backend/app/bootstrap.py` | 创建服务、装配依赖、注册路由与生命周期 |
| `backend/app/core/` | 配置、日志、标识、服务契约和运行基础约定 |
| `backend/app/modules/` | 按业务组织实现与接口 |
| `backend/app/agents/` | 图构建、执行、工具、上下文、分析策略与提示词 |
| `backend/app/infrastructure/` | 通用数据库、模型协议、MCP、存储和缓存实现 |
| `backend/tools/SourceAnalysis/` | C# / Roslyn 分析工具 |
| `backend/migrations/` | 数据库迁移 |
| `backend/tests/` | 后端测试 |

业务模块包括 `auth`、`projects`、`chat`、`source_analysis`、`knowledge`、`memory`、`handover`、`settings`、`admin`。新增行为先放入所属业务，不重新堆到应用根目录。全项目阅读、项目资料管理和旧代码修改流程已移除；`source_analysis/reading/` 与 `infrastructure/database/legacy_code_work.py` 仅保留历史表兼容。聊天的模型额度归 `settings/model_ledger.py`，临时文件边界归 `infrastructure/storage/files.py`，不再依赖旧修改模块。

- 普通模块按需要使用 `router.py`、`schemas.py`、`service.py`、`models.py` 及职责明确的辅助文件；复杂度不足时不强套 DDD 四层。
- HTTP 接口负责请求、身份与响应，业务规则归服务或用例；统一装配留在 `bootstrap.py`，业务模块不反向导入 `main.py` 或 `bootstrap.py`。
- ORM 模型归所属业务；交接模型位于自身持久化目录。全应用只保留一个数据库 `Base`，由 `infrastructure/database/registry.py` 统一注册。移动类不能顺带改变表名、索引、外键或迁移语义。
- 跨业务调用优先复用已有服务或明确接口，避免新增隐藏的全局状态与循环依赖。

## 交接模块分层

```text
backend/app/modules/handover/
├─ domain/                  # 业务内容、状态、版本与约束
├─ application/             # 记录、资料、调试、候选和交接包用例
│  ├─ commands.py           # 用例输入
│  └─ ports.py              # 仓储、解析器、导出器和生成器接口
├─ infrastructure/
│  ├─ persistence/          # ORM、查询与事务
│  ├─ parsers/              # Word、PDF、ZIP 等解析
│  ├─ exporters/            # Word、ZIP 等导出
│  └─ ai.py                 # 模型连接、输出适配与释放
└─ interfaces/http/         # 概览、记录、资料、调试、候选、交接包、复核接口
```

- `domain` 不导入 FastAPI、SQLAlchemy、模型 SDK、HTTP 接口或启动装配。
- `application` 通过 `ports.py` 接收依赖，不创建数据库会话、具体仓储或供应商客户端，不导入本模块的 HTTP 与基础设施实现。
- 具体适配器实现接口，由 `bootstrap.py` 装配；领域规则和事务责任不能因拆文件而遗漏。
- 原有任务由通用记录用例处理，不仅为目录整齐再建一套相同行为的接口。

## 前端归属

```text
frontend/src/
├─ main.tsx
├─ app/                     # 入口、布局、跨业务协调和状态装配
├─ features/                # auth/projects/chat/source_reader/knowledge/
│                           # memory/settings/admin/handover
└─ shared/                  # 通用 UI、HTTP、基础类型、工具、主题和素材
```

- 功能专用组件、Hook、规则、请求和样式跟随所属 `features`；确有复用需求的基础能力才进入 `shared`。
- `shared` 不导入 `app` 或 `features`。含源码引用等业务交互的 Markdown 组合组件归应用层；交接内部共用卡片和规则留在交接模块内部。
- 全局状态由 `app/state` 装配，业务状态分属聊天、项目、源码阅读和布局。移动状态时保留账号隔离、持久化键、草稿、阅读位置和恢复语义。
- 大组件按行为职责拆分，避免通过大量透传参数、重复状态或无意义包装隐藏原复杂度。

## 资源、脚本和文档

- 知识资源归 `resources/knowledge/{flows,generated}`，生成和校验脚本归 `frontend/scripts/knowledge/`。保持 `/archify/`、`/agent-knowledge.json` 的既有地址与资源映射；历史 `/engineering/` 模块索引和源码快照已按用户要求移除，不再恢复。
- 启动实现归 `scripts/dev/`，维护归 `scripts/maintenance/`，显式验收归 `scripts/verification/`。保留根目录启动入口和既有恢复入口。
- 文档按 `docs/{architecture,development,features,verification,archive}` 归类。当前规范与历史记录分开维护，不把旧报告视为当前验收。
- 报告与历史构建归 `output/`；正式前端发布目录仍是 `frontend/dist/`。有发布任务时保留旧哈希资源并最后替换首页。
- 每个项目 Skill 使用 `skills/<技能名>/SKILL.md`，名称与目录一致；更新规范时同步维护 `agent.md` 和 README 中的引用。

## 调整后的核对

按变更范围核对导入、路由注册、公开 URL、资源解析、CLI 路径、测试发现和文档引用。文件移动不等于职责拆分完成；不要用兼容副本维持两套相同实现。

保持原有 API、权限、数据库契约、源码及资料固定版本引用不变。确需改变行为时，将行为变化单独说明并验证。

进一步说明见 [工程结构与依赖约定](../../docs/architecture/overview.md)。代码质量见 [开发规范](../project-development/SKILL.md)，验证方法见 [测试规范](../project-testing/SKILL.md)。
