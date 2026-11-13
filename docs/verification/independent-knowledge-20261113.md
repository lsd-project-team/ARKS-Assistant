# 流程图谱与功能说明独立化验收

2026-11-13 按用户确认执行：流程图谱和功能说明改为应用自带的独立资料，页面不依赖项目或源码；构建不再读取或校验 `trunk`；读者可见说明改成业务语言。

## 行为变化

- 「功能与流程」不再请求 `/api/projects/{scope}/source-context`，也不再用 `knowledge_available` 决定是否显示。任何账号、任何项目或独立对话都可以直接打开；空项目不再显示“此项目还没有流程与功能资料”。
- 删除构建期源码依赖：`knowledge:source-check`、`source-evidence.json`、`source-guide-validation.mjs`、`check-atlas.mjs`、`manual-review.json` 和 `agent-knowledge.json` 生成均移除。`build` 只运行自带资源检查、模块资料检查、TypeScript 和 Vite。
- 删除后端未使用的源码核对入口：`/api/knowledge/check`、`ProjectKnowledge` 及其索引。聊天原本就没有接入流程图谱、功能说明和交接资料，本次不改变问答来源。
- 发布阅读版图谱继续隐藏历史源码依据卡片；知识页不再展示源码文件名、行号、类名、方法名、状态枚举和代码片段。

## 内容范围

- 19 个专题的流程、步骤、分支和复核边界改成业务说明，保留条件、分支、失败处理和未确认边界。
- 8 张内置图谱的节点说明、卡片和连线文字改成业务说明。
- 23 个功能专题和 46 张模块交互图的摘要、条件与异常文案改成业务说明。
- 保留 S1、S2、G0、Bond、PR、BMC、ETEL、LVDT、TU、XY/XYZ 等行业术语和专有名词。
- 42 篇模块分章文档仍保留原有技术底稿，当前阅读页不默认展示，也不参与源码校验；后续如需要可单独做业务化整理。

## 验证

- 前端 `node --test tests/knowledge/*.test.mjs`：111 项通过。
- 前端全量 `npm test`：419 项通过，失败 0。
- `npx tsc -b`：通过。
- `npm run build`：通过（含 `knowledge:check`、`knowledge:manual-check`、TypeScript、Vite；构建耗时约 1 分 28 秒）。
- 后端相关测试（knowledge、source-context、static-assets）：32 项通过，1 项按环境跳过。
- 后端全量：1197 项通过，13 项失败均出现在模型探针/供应商网络用例，报错为本机代理地址 `Invalid port: ':1]'`，与本次改动无关；清除代理环境后仍复现，属于运行环境问题。
- 源码依赖核对：`frontend/scripts` 中已无 `trunk` 引用；`knowledge:check` 只校验 `resources/knowledge/flows` 下的自带资源。

## 已知边界

- 说明文字不再可追溯到具体源码行；准确性由资料本身负责，旧验收中“与 trunk 一致”的结论不再适用。
- 图谱 HTML 原文件仍保留历史源码依据数据，但阅读版在服务时移除，页面不可见；原始文件不作为构建或页面依赖。
- 本次没有接入 AI 问答检索；如需让聊天直接读这些资料，需要另建与源码无关的知识来源。
