# AI 回答 Rich Content 改造

## Phase 0 审计（2026-10-20）

当前前端为 React 19、TypeScript、Vite、Zustand、React Query，样式使用既有 CSS Tokens，图标使用 lucide-react。聊天支持 white/classic/dark 外观。没有可复用的动态 Mermaid 渲染器；知识图谱页面展示的是既有 HTML 资料，不能执行模型返回的 HTML 来复用它。

### 原有链路与核心文件

- `frontend/src/features/chat/components/ChatPane.tsx`：发送、新会话、取消、重试、恢复、重新生成、分页和版本切换。
- `features/chat/components/MessageBubble.tsx`：历史消息、复制、选中文字引用、共享结论和分支。
- `features/chat/components/AnswerMarkdown.tsx` → `app/components/Markdown.tsx`：助手的记录展示插件、唯一正文 Markdown 渲染入口、GFM、源码和资料引用。
- `shared/ui/markdown/CodeBlock.tsx`：代码复制、换行、长代码折叠；此前无语法高亮。
- `features/chat/hooks/useRunStream.ts`：EventSource 订阅 token、answer_replace、引用、工具、状态、error、done，按事件序号去重，断线自动重连。
- `features/chat/hooks/useConversation.ts`：原始历史分页、消息合并和恢复；`useChatScroll.ts` 保留锚点与用户主动停止跟随的状态。
- `features/source_reader/hooks/useSourceCitation.ts`：权限内获取源码、范围核对、版本变化反馈、原查看器定位及历史来源对话框。
- `backend/app/modules/chat/{router,runs,repository,history}.py`：请求授权、后台运行、事件持久化重放和历史分页。

当前 Message 的主体是 `id/role/content:string/selections/source_workspace_id`；Run 保存 `answer:string/status/message_id/response_message_id`。token 实时追加到 Run.answer，answer_replace 替换全文，完成后写入原 Message 表；取消和失败保留 Run.answer。SSE 断线不会取消任务，事件按 sequence 重放，不需要另建传输或消息存储。

源码文本链接为 `source:path#Lstart-Lend`。本轮 `source_evidence` 包含 path、version、起止行、来源工作区，`/runs/{id}/context` 返回证据。既有引用会核对版本和范围，但缺少证据时仍允许查看当前文件并警告；结构化引用将更严格：缺少匹配证据时不可执行定位。

### 问题、复用与兼容策略

标题层级接近正文、间距分散于多层样式、正文宽度 720px，缺少动态概览和步骤展示。流式回答未传 runId，引用上下文不足。代码和表格已有基础容器，可扩展；聊天历史、消息操作、阅读锚点、版本查看、资料引用全部保留。

新增能力放入聊天业务模块：版本化判别联合协议、运行时校验、轻量组件注册表、内容分段和证据匹配。TextBlock 复用原 Markdown，CodeBlock 扩展原组件。普通 Markdown 不按标题或业务关键词猜测为卡片。

协议采用可选的 `rich-content` 围栏，封装 `{version:1, blocks:[...]}`，允许与正文交错。原文本存储和 SSE token/answer_replace/done 保持不变，旧历史无需迁移。只有完整围栏和通过校验的块才可交互；未知版本、类型、损坏或中断内容显示解释及原文。模型仅提出展示数据，不能指定路由、HTML、事件处理器或任意组件。引用必须匹配真实证据。

### 阶段计划

1. Phase 1：统一阅读宽度、Markdown 排版、表格与消息操作。
2. Phase 2：概览、步骤、代码、表格、图形、折叠和引用组件及组件测试。
3. Phase 3：协议校验、分段、白名单映射、后端对应验证与可选展示指令；不改变检索和事实核查业务。
4. Phase 4：真实 SSE 分段渲染、中断降级、重放健壮性和阅读跟随。
5. Phase 5：本轮证据匹配、引用预览和源码查看器联动。
6. Phase 6：自动化回归、生产构建、隔离真实页面视觉验证与交付记录。

测试沿用 node:test/esbuild/React server rendering 和 pytest。真实页面检查使用隔离测试数据，不向正式库写入样例，不执行设备源码。没有现成点赞/点踩，无需新增。按阶段提交并推送，仅包含本次文件；保留已有运输单元文档改动。
