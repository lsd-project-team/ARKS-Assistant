# Rich Content UI 升级验收（2026-10-20）

## 结果与范围

已在现有聊天系统中完成基础排版、8 类动态内容块、版本化协议、流式适配、证据关联和源码交互。复用原 Message/Run、SSE、数据库、React Markdown、源码查看器、账号权限和历史恢复，不迁移旧消息，不改变检索排序或 Agent 业务能力。

界面采用 820px 阅读上限、统一标题/段落节奏、中性色和原有主题 Tokens。概览不把没有操作的内容变成按钮；步骤使用纵向时间轴；详情按需展开。已有复制、重新生成、选中文字引用、上下文、共享结论、分支与停止入口保留。原项目没有点赞/点踩，本次不增加。

前置审计及原链路见 [架构审计](../architecture/chat-rich-content.md)。原工作区的运输单元文档改动由其原任务独立提交，本次未覆盖或纳入聊天改造提交。

## 组件清单

| 组件 | 状态 | 行为 |
| --- | --- | --- |
| TextBlock | 完成 | 复用唯一 Markdown 渲染器，保留 GFM、中文参数波浪线和原资料引用插件 |
| OverviewGrid | 完成 | 数据驱动网格、图标白名单、状态、可选已核实源码入口，小屏单列 |
| StepFlow | 完成 | 自动编号、连接线、任意合法步骤数量、源码证据和原生可折叠详情 |
| SourceReference | 完成 | 完整路径/行号/版本/来源/原始标识，核对、预览、复制路径、原查看器定位及错误提示 |
| CodeBlock | 完成 | 复用原代码块，增加现有 Shiki 高亮、语言别名、文件名、可选行号；复制、换行、长代码折叠和横向滚动 |
| DataTable | 完成 | 表头/标题语义、数字对齐、零值、空值、滚动和长内容换行 |
| FlowDiagram | 完成 | 安全节点/边协议、纵向/横向布局、分支和循环、缩放、适配、全屏及文字替代 |
| CollapsibleSection | 完成 | 原生 details/summary，键盘操作，明确展开状态与可选默认展开 |
| BlockBoundary | 完成 | 单块渲染异常时显示解释及原始数据，避免拖垮其余回答 |

项目原来没有动态 Mermaid 渲染器。本次图形使用明确的节点/边数据和 React SVG，不执行模型生成的 HTML/SVG；普通 `mermaid` 代码围栏仍按代码展示，不声称支持任意 Mermaid 语法。

## 协议与扩展

普通回答继续使用 Markdown；需要特殊组织时，在正文中交错加入如下围栏：

````markdown
这里是简短结论。

```rich-content
{"version":1,"blocks":[{"id":"workflow","type":"step_flow","title":"执行步骤","steps":[{"id":"prepare","title":"检查条件","description":"按本题实际内容填写。"}]}]}
```

这里继续解释。
````

此例仅说明协议，不是正式组件中的业务模板。完整共享测试数据见 `frontend/tests/chat/fixtures/rich-content.json`。

- 正式 TypeScript 判别联合位于 `features/chat/rich/types.ts`，包括 text、overview_grid、step_flow、source_reference、code、table、diagram、collapsible。
- TypeScript 运行时校验位于 `schema.ts`；后端对应 Pydantic 模型位于 `modules/chat/rich_content.py`，不增加验证依赖。
- Schema 限制字段白名单、稳定 ID、重复 ID、字符串、数组、总块数、深度、节点连接、表格列数及源码路径范围。每个文档最多 256KiB/128 块/4 层嵌套；代码不超过 60,000 字符；图形最多 60 节点、120 条边；消息至多识别 32 个协议围栏。
- Schema 不允许事件处理器、任意组件名称、内部路由或可执行操作。仅源引用的路径、范围和版本建议可以进入后续证据匹配。
- `parseContent.ts` 只识别显式协议围栏，普通代码中的协议示例保持原样；不按标题、关键词或业务名推测卡片与步骤。
- `RichContentRenderer.tsx` 使用固定类型分派。增加类型时扩展类型、双端校验、分派组件和边界测试，不需要改变 ChatPane、数据库或 SSE。
- 未知版本、未知类型、缺字段、损坏 JSON、超限或不完整围栏显示可解释的降级状态和原文。不会丢掉前后正文。
- Markdown 保持原安全渲染方式，不开启原始 HTML，不执行返回代码；损坏业务引用不退化为任意自定义协议链接。

## 流式与历史

原 token / answer_replace / error / done 传输协议保持不变，无新消息模型或 SSE 链路。

token 在原 Hook 中按约 32ms 合并提交；文本立即逐步显示。完整关闭并校验后的围栏才成为正式组件；接收中显示“正在组织内容”。已确认块通过解析缓存保持对象身份，配合 memo 避免后续 token 重建前面组件。流式 Markdown 代码先按纯文本展示，完成后再异步高亮；高亮加载失败仍显示完整代码。

停止/失败没有最终全文时刷新剩余缓冲，保留已收到内容；不完整块退出接收态后显示原文与解释。answer_replace 和 done 的最终全文会清除旧缓冲，避免旧 token 再次追加。SSE 继续使用原递增 sequence 和 EventSource 重连；重复及倒序旧事件不重复处理，坏 JSON 有提示且不打断后续有效事件。SSE 自身保证传输顺序，这里不声称能重排任意乱序 token；完成事件仍同步服务端最终回答。

旧 Message.content、Run.answer 仍为字符串，历史无需迁移。取消、失败、恢复、重试、重新生成和历史分页仍走原接口。流式与中断消息现在也传递 runId，保证引用可追踪。复制回答和保存共享结论时转换为可读 Markdown；原始存储保留协议全文。

原阅读锚点和用户暂停跟随机制保留。新增 ResizeObserver 仅在仍跟随时补齐异步高度变化；向上阅读不会被强制拉回底部。

## 证据与源码

真实来源为原后端 source_evidence 和 `/runs/{id}/context`，保留 runId、完整路径、行号、版本、source_workspace_id 和当前状态。

结构化引用必须匹配完整路径、覆盖范围、来源身份和版本。多个来源/版本存在歧义时不猜测；文件变化、不可读、无匹配记录或无运行身份时不给出成功定位。点击最终仍通过 `useSourceCitation` 读取当前文件并核对版本/范围，避免检查后文件变化导致错误高亮。原始目录版本变化时可显示当前文件供核对，但返回定位失败。

引用详情可通过点击、键盘展开，完整路径与版本不依赖悬停。预览先读取权限内文件且再次核对版本，随后复用 SelectionPreview；正文内定位复用原源码查看器和返回回答的分栏路径。复制路径无需先获得定位成功。

后端增加展示适配的原因：原核查器把代码围栏作为示例跳过，不能据此漏掉 rich-content 内的引用。`rich_presentation.py` 把通过 Pydantic 校验的展示数据投影为语义文本与原格式引用，交给原 SourceEvidence/语义复核器。模型声明的版本和目录另与本轮证据核对；错误引用、未知结论仍按原机制降为文字和提示。仅追加可选展示协议指令，不修改核心业务提示、工具额度、检索策略或事实核查标准；资料/原文回答继续优先 Markdown。

## 实际文件变更

路径均相对仓库根；本表仅列本任务文件。

| 文件 | 用途 |
| --- | --- |
| `docs/architecture/chat-rich-content.md` | Phase 0 审计与阶段计划 |
| `docs/verification/chat-rich-content.md` | 本验收与交付说明 |
| `frontend/src/main.tsx` | 引入回答及 Rich Content 样式 |
| `frontend/src/features/chat/styles/chat-layout.css` | 阅读宽度上限 |
| `frontend/src/features/chat/styles/answer-content.css` | Markdown、消息、表格与操作的统一排版 |
| `frontend/src/features/chat/styles/rich-content.css` | 结构化块、引用、图形和高亮的主题与响应式样式 |
| `frontend/src/features/chat/rich/types.ts` | 版本化判别联合与源码指针 |
| `frontend/src/features/chat/rich/schema.ts` | 运行时白名单及边界校验 |
| `frontend/src/features/chat/rich/parseContent.ts` | 围栏分段、接收态与已完成块缓存 |
| `frontend/src/features/chat/rich/RichContentRenderer.tsx` | 类型分派、Markdown 复用及降级展示 |
| `frontend/src/features/chat/rich/ContentBlocks.tsx` | 概览、步骤、表格、折叠组件 |
| `frontend/src/features/chat/rich/FlowDiagram.tsx` | 安全 SVG 图形与查看操作 |
| `frontend/src/features/chat/rich/SourceReference.tsx` | 证据查询、引用信息、预览、复制和定位 |
| `frontend/src/features/chat/rich/sourceEvidence.ts` | 来源、范围、版本和歧义匹配规则 |
| `frontend/src/features/chat/rich/contentToMarkdown.ts` | 复制和共享结论的可读文本适配 |
| `frontend/src/features/chat/rich/BlockBoundary.tsx` | 单块错误隔离 |
| `frontend/src/features/chat/lib/streamEvents.ts` | 原 SSE 订阅的健壮处理与文本缓冲 |
| `frontend/src/features/chat/hooks/useRunStream.ts` | 复用原事件并接入缓冲、证据失效通知和清理 |
| `frontend/src/features/chat/hooks/useChatScroll.ts` | 异步内容高度变化时按原跟随状态滚动 |
| `frontend/src/features/chat/components/AnswerMarkdown.tsx` | 原助手正文入口接入 Rich Renderer |
| `frontend/src/features/chat/components/ChatPane.tsx` | 流式/中断 runId、接收态及输入框/队列的独立 Key |
| `frontend/src/features/chat/components/MessageBubble.tsx` | 复制/共享结论保留可读内容 |
| `frontend/src/features/chat/components/RunArchive.tsx` | 旧中断运行传递引用身份 |
| `frontend/src/features/chat/components/SelectionPreview.tsx` | 允许区分原选区快照与本轮引用预览说明 |
| `frontend/src/app/components/Markdown.tsx` | 统一代码块接收态及损坏业务引用的安全展示 |
| `frontend/src/shared/ui/markdown/CodeBlock.tsx` | 文件名、行号、高亮、折叠语义及加载失败降级 |
| `frontend/src/shared/ui/markdown/CodeSyntax.tsx` | 复用现有 Pierre/Shiki 的异步双主题高亮 |
| `frontend/src/features/source_reader/hooks/useSourceCitation.ts` | 复用源码读取与目录解析；原目录不匹配时不返回成功 |
| `backend/app/modules/chat/rich_content.py` | Pydantic 协议模型及结构限制 |
| `backend/app/modules/chat/rich_presentation.py` | 可选展示指导、语义投影和引用元数据遍历 |
| `backend/app/modules/source_analysis/evidence.py` | 让结构化引用进入原覆盖核查，核对声明来源/版本 |
| `backend/app/modules/source_analysis/review.py` | 原语义复核接收展示投影，排除排版元数据 |
| `backend/app/agents/runtime/graph_builder.py` | 追加可选展示协议，不替换原业务提示 |
| `frontend/tests/chat/rich-components.test.mjs` | 组件语义、空数据、长流程、表格和图形 |
| `frontend/tests/chat/rich-protocol.test.mjs` | 协议、围栏、边界、注入和异常数据 |
| `frontend/tests/chat/rich-renderer.test.mjs` | 真实 Renderer/Markdown 兼容与安全渲染 |
| `frontend/tests/chat/rich-stream.test.mjs` | 分片、身份稳定、取消降级、重放和缓冲 |
| `frontend/tests/chat/rich-source.test.mjs` | 证据身份/歧义/状态及可读复制 |
| `frontend/tests/chat/fixtures/rich-content.json` | 双端共享的 8 类测试数据，仅测试使用 |
| `frontend/tests/source_reader/source-citation.test.mjs` | 原查看器回归及原始目录版本变化的失败语义 |
| `backend/tests/unit/chat/__init__.py` | 测试包入口 |
| `backend/tests/unit/chat/test_rich_content.py` | 双端协议数据、投影及伪造来源/版本反例 |
| `backend/tests/integration/chat/test_rich_stream.py` | 原运行生命周期/持久化/重放及真实 Agent 图的结构化回答 |
| `scripts/verification/rich_content_ui.py` | 隔离真实聊天页面验收服务，可控模型且不调用真实供应商 |

## 自动化结果

| 检查 | 结果 |
| --- | --- |
| 前端全套 `node scripts/test.mjs` | 55 个测试文件，297 passed / 0 failed / 0 skipped |
| 后端相关回归（命令见下） | 20 个测试文件，168 passed / 0 failed / 0 skipped |
| TypeScript `tsc -b` | 通过；同时包含于最终生产构建 |
| 生产构建 | 通过，28.26s；产物在 `output/rich-content-dist/`，未替换正式 dist |
| 源码说明检查 | 6 个专题、107 条流程、403 个节点、658 条说明；72 个文件、540 段依据一致 |
| Ruff check / format --check（修改 Python 文件） | 通过 |
| Prettier --check（修改前端文件） | 通过 |
| `git diff --check` | 通过 |
| 覆盖率 | 未采集 |

前端在 `frontend/` 执行：

```powershell
node scripts/test.mjs
node node_modules/typescript/bin/tsc -b
npm.cmd run build -- --outDir ../output/rich-content-dist
```

后端在 `backend/` 执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/unit/chat tests/unit/agents tests/integration/chat tests/integration/source_analysis/test_source_evidence.py tests/integration/source_analysis/test_source_review.py tests/integration/auth/test_authentication.py tests/architecture
```

最终另针对语义投影复核执行 `test_rich_stream.py`、`test_source_review.py`、`test_review_context.py`，15 passed / 0 failed / 0 skipped（与前述回归部分重叠，不相加作为独立用例总数）。关键反例包括：非当前版本、另一源码目录、未知节点、重复 ID、错列表格、非法路径、HTML/脚本、损坏事件、未关闭 JSON、重放旧事件与旧缓冲串入新回答。真实 Agent 图测试实际调用源码工具和原核查器，仅模型回复由替身控制。

## 真实页面检查

使用 `scripts/verification/rich_content_ui.py`，后端端口 8876、Vite 端口 5179，测试账号/数据位于本次创建的 `output/rich-ui-*/`。未读写正式对话数据库、未使用真实供应商密钥、未执行设备程序。该服务使用真实认证、请求、SSE、原消息存储和原源码查看器；与只渲染示例组件的页面不同，回答通过原聊天链路到达 UI。

实际操作完成：新建会话、发送、流式正文、接收中占位、完成、停止、失败提示、继续/重试入口、重新生成、版本切换入口、历史恢复、复制回复、引用详情、键盘空格展开/收起、预览匹配版本、定位 Program.cs 第 2 行、图形缩放/适配/全屏、旧 Markdown 与未知版本降级。真实供应商调用不在本轮浏览器验收内。

视口检查：1440×900、1280×800、390×844；纯白、柔和灰绿和深色。390px 下网格为单列，文档总宽度仍为 390px，无整页横向溢出；图形在自身容器滚动并可适配。用户在流式期间向上阅读时，完成前后 scrollTop 均为 871，保留“回到最新”入口。

浏览器发现并修复了原输入框/队列组件的重复 Key；修复重新载入后没有新增该警告。源码预览说明区分“发送时保存的选区”与“本轮核对版本的片段”。

本地截图：

- `output/rich-content-desktop.jpg`：浅色概览、步骤与阅读层级。
- `output/rich-content-dark.jpg`：同一内容的深色主题。
- `output/rich-content-mobile.jpg`：390px 下步骤与代码区。
- `output/rich-content-stopped.jpg`：停止后的部分内容与不完整块解释。

复现方式：在仓库根运行 `backend/.venv/Scripts/python.exe scripts/verification/rich_content_ui.py`，使用其打印的 Vite 配置，在 `frontend/` 执行 `node node_modules/vite/bin/vite.js --config <配置路径>`。测试账号 `rich-test`、密码 `local-rich-ui-test` 仅由该独立测试服务创建，不能用于正式服务。测试服务只监听 127.0.0.1。

## 阶段提交

| 阶段 | Git 提交 |
| --- | --- |
| Phase 0 审计 | `2bbe032` |
| Phase 1 视觉与 Markdown | `289b5b8` |
| Phase 2 通用组件 | `5bd6716` |
| Phase 3 协议与动态渲染 | `24f7653` |
| Phase 4 流式兼容 | `a24b5d6` |
| Phase 5 证据和源码交互 | `662359b` |
| Phase 6 回归与视觉验收 | 本文所在提交；最终聊天交付给出哈希 |

按仓库要求，每阶段验证后独立提交并推送 origin/master。

## 未验证范围与后续工作

以下为最初工程验收时的边界。2026-10-20 已补做真实模型、实际源码检索和当前登录账号的真实历史抽查，含发现问题、修复及未通过项，详见[真实验收补充记录](chat-rich-content-live-20261020.md)。不能继续用本节的历史“未调用”描述代表最新状态。

- 未调用真实供应商评估它对可选协议的选择率、格式成功率与真实设备业务回答质量；模型输出普通 Markdown 仍是合法结果。
- 浏览器使用隔离数据和可控模型；没有抽查正式账号的私人历史，也没有将新构建发布到正式服务。
- 未进行大型长文/大量组件的压力基准、读屏软件专项验收或多浏览器矩阵；本轮无卡死现象不等于完整性能认证。
- 不支持任意 Mermaid 文本渲染。若后续真实回答确实大量返回 Mermaid，可在当前 diagram 类型下增加经过安全限制的解析器，不需要重建聊天系统。
- 自动化质量判断：关键协议、安全、流式状态、证据边界及真实组件渲染有正常与反例覆盖，适合本次工程回归；不能替代真实供应商和设备业务验收。
