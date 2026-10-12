# 白色界面视觉调整与功能验收

2026-10-11。保留旧版的导航与阅读布局，在下午版本中统一边框、图标、字体和表面层次。正式入口为 <http://127.0.0.1:8765/#graphs>。

## 设计依据与结果

- 参考 [Linear 的界面调整说明](https://linear.app/now/behind-the-latest-design-refresh)：减轻导航的视觉重量，减少装饰性图标，软化分隔线，让主要内容更突出。
- 参考 [Vercel Geist Materials](https://vercel.com/geist/materials)：按卡片、菜单、弹窗的层级统一圆角、细描边与阴影，保持键盘焦点可见；同时检查浅色和深色。
- 字体采用本地 Geist / Geist Mono 与 Noto Sans SC Variable。版本均固定为 5.3.0，使用 Fontsource 的 WOFF2 和 Unicode 分片；不依赖浏览器访问字体 CDN。字体版权与 OFL 原文位于 `frontend/public/font-licenses/`，随构建保留。[Geist 字体说明](https://vercel.com/font)
- 默认白色，侧栏极浅灰，正文深灰，少量灰紫用于选中与阅读入口。白色模式的小字颜色 `#6b7280`，对白色与侧栏背景的计算对比度分别为 4.83 和 4.59。
- 图标统一为 Lucide 细线图标，导航、按钮、卡片、输入框、菜单和弹窗共用一致的圆角与表面规则。聊天、只读源码、设置、记忆、图谱、专题、模块和方法页面均覆盖。
- 纯白、柔和灰绿、深色三种外观继续可切换并在刷新后保持。图内经典 / 蓝图等风格保留。

实现入口：`frontend/src/styles/refined-interface.css`、`frontend/src/styles/legacy-visual.css`、`frontend/src/components/WorkspaceNavigation.tsx`、`frontend/src/knowledge/UiIcon.tsx`、`frontend/src/main.tsx`。图内字体与工具栏处理位于 `KnowledgePages.tsx` / `diagramChrome.css`。

## 验收发现并修复的问题

1. Markdown 的内联渲染组件在页面更新时被重新创建，导致代码块展开 / 换行状态复位。改为稳定的组件身份；浏览器核验展开与换行在打开源码、切换页面状态后保持。
2. 更新后，旧窗口引用已替换的图谱动态资源会使整页白屏。采用共享 `WorkspaceLoadBoundary` 隔离图谱与源码加载失败；显示中文提示和重载入口，导航、问答与持久化草稿保留。实际阻断两类资源分别验证，并解除阻断后恢复。
3. 只读源码区域自身覆盖了上层字体变量。改为直接在 `.source-code-view` 设置，核验实际行节点使用 Geist Mono / Noto Sans SC；16px / 32px 的字号和行高设置正常。

## 自动检查

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 前端 `npm run test` | 44 通过，0 失败 | `output/design-refresh-frontend-tests.log` |
| 后端全量 pytest | 120 通过，1 跳过 | `output/design-refresh-backend-tests.log` |
| 知识核对 API 定向回归 | 3 通过 | `backend/tests/test_knowledge.py`；原编码哈希、变化 / 缺失、工作区边界 |
| 工作区定向检查 `pytest tests/test_workspace.py -q -rs` | 13 通过，1 跳过 | `output/design-refresh-workspace-tests.log` |
| 资料 `npm run knowledge:check` | 1667 项资源链接通过 | `output/design-refresh-resources.log` |
| TypeScript + Vite `npm run build` | 通过 | `output/design-refresh-build.log` |
| Ruff `ruff check app tests` | 通过 | `output/design-refresh-ruff.log` |
| 改动文件 Prettier 检查 | 通过 | 本轮命令结果；样式与渲染组件已格式化 |

唯一跳过项是 `test_symlink_cannot_escape`：本机 Windows 未启用创建符号链接权限。常规路径越界、编码、二进制拒绝、只读限制的测试通过；不将跳过项记为通过。

资料检查覆盖 64 项图谱 / 补充资料、29 个模块、1455 个文件与 256 份方法分片。用户图谱目录仍为 61 张：8 条生产主流程与 53 张深入阅读图。

## 功能范围与证据

以下映射对应 [体验清单 01–36](experience-upgrade.md)，结合本轮浏览器操作与当前自动测试。自动测试使用实际数据库、检查点、框架、SDK 协议或独立进程；浏览器操作使用独立验收数据。

| 范围 | 本轮证据与回归覆盖 |
| --- | --- |
| 01–05 会话删除 / 撤销 / 回收站、归档、置顶、首次发送 | 浏览器重命名、置顶、归档恢复、删除撤销，草稿保持；`test_conversation_management.py`、`test_api.py` |
| 06–07 标题、正文 / 选区 / 路径搜索 | 浏览器 Enter 保存标题；`test_conversation_management.py`、`test_conversation_history.py` |
| 08–09 编辑问题、原版本、提交 / 取消与失败输入 | 浏览器原问题归档、重新回答且独立草稿保持；`test_conversation_workflows.py`、前端会话工作流测试 |
| 10–12 分页 / 阅读位置、菜单、分组与运行状态 | 浏览器菜单和运行状态；`test_conversation_history.py`、前端导航 / 工作区 / 跨窗口测试 |
| 13–15 代码块、回复版本、引用提问 | 40 行代码与完整回复复制、展开 / 换行；修复状态复位；1/2 与 2/2 版本切换；浏览器选中文字追加原草稿且未自动发送，前端 Markdown 原文选区与会话回归 |
| 16–18 输入、选区快照、源码引用 | 浏览器流式输入、停止、选区预览；真实源码 L16–21 六行高亮，完整路径与原文；前端源码选区 / 命令测试、`test_stale_selection.py` |
| 19–21 全文搜索、标签与阅读偏好 | EnableVisualStyles 在当前 trunk 命中 L19 并定位；关闭其他标签；字号 / 行高 / 行号跳转；前端文件导航和工作区测试 |
| 22–23 阶段、耗时、停止与错误分类 | 实际 Agent 图读取源码和 stdio MCP；停止保留部分回答；401 错误显示处理入口；`test_conversation_workflows.py`、`test_recovery.py` |
| 24 保存 / 删除 / 恢复等轻提示 | 浏览器记忆、备份、会话操作显示中文反馈 |
| 25–28 模型 / MCP 配置、能力检测、未保存与冲突 | 浏览器未保存保护、配置切换、stdio MCP；正式配置真实模型四项检测与 DeepWiki 工具发现；`test_settings_profiles.py`、`test_model_probe.py`、`test_mcp.py`、前端设置草稿测试 |
| 29–31 记忆、历史还原、源码过期 | 浏览器创建 / 编辑 / 恢复历史 / 可恢复删除；`test_memory_management.py`、`test_conversation_history.py`、`test_stale_selection.py` |
| 32 完整上下文预算与原生压缩 | 浏览器 `/compact` 归纳 12 条历史消息，显示中文摘要与系统 / 工具 / 记忆预算；`test_context_budget.py`、`test_compaction.py` |
| 33–34 队列和消息分支 | 浏览器入队、停止后暂停、编辑 / 取消、模型切换、创建分支与来源入口；`test_conversation_workflows.py` |
| 35–36 备份 / 恢复、存储和连续回归 | 下载 ZIP 后选择同一文件，校验版本、哈希与统计；实际恢复、回滚、Windows 中文路径由 `test_backup_restore.py` 覆盖；跨窗口由前端测试覆盖 |
| 图谱与功能说明 | 筛选、工作流 / 时序 / 数据流 / 架构四类原图、缩放、查找、图内风格、节点联动、专题、模块依赖 / 复核、完整源码、85 处静态调用的方法页；资源检查验证全目录；知识路由 / 版本失效测试通过 |
| 资料与下午问答融合 | 方法讨论追加原草稿，未自动发送；当前源码与选区使用只读工作区；旧资料和当前核对状态继续区分 |
| 加载失败恢复 | 实际阻断图谱和源码动态模块，错误隔离、草稿保持、重载恢复；核对 API 失败时明确警告，61 张旧图继续可读 |
| 外观与尺寸 | 白 / 灰绿 / 深色与刷新保持；默认 1280、900、430 像素下检查图谱、功能说明、设置和问答 / 源码切换，无页面横向溢出；手机文件树浮层可关闭 |

浏览器记录：`output/design-browser-proof.json`，36 项检查通过。最终 1280 × 720 白色页面的首排卡片底部为 696.875px，说明文字为 13px，小字颜色为 `#6b7280`。它记录实际观察结果；不是替代自动测试的实现镜像测试。

## 实际外部连接与隔离方式

- 正式 `8765` 的已有 DeepSeek-V4-Flash / Anthropic 配置：普通回复、流式输出、工具调用及结果返回、压缩模型四项均通过；检测时间 2026-10-11 11:33:52。仅短验收请求，截图 `output/design-real-model.jpg`。
- 正式 DeepWiki Streamable HTTP：实际连接并发现 `ask_wiki_question`、`read_wiki_contents`、`read_wiki_structure`，截图 `output/design-real-mcp.jpg`。
- 会话编辑、删除、队列、压缩、记忆和备份操作运行在 `8766` / `output/design-acceptance-data`。使用本地确定性流式模型，真实 Agent / DeepAgents 图、SQLite、检查点、源码工具和 stdio MCP；不把本地模型行为当作远程模型回答质量的证明。
- 正式用户会话和记忆未参与这些写入 / 删除测试。模型 / MCP 配置未点击保存；源码目录只读，旧版 `8775` 保持独立运行。
- 本轮验收对象是网页和 Agent 工作区功能；图谱中设备业务的“部分复核 / 待确认”标记继续保留，不将静态阅读验收称为设备实机验收。

## 截图与交付

- `output/design-final-white.jpg`：正式白色图谱页。
- `output/design-functions-white.jpg`：功能说明。
- `output/design-chat-source-white.jpg`：聊天与只读源码。
- `output/design-module-dark.jpg`：深色模块页。
- `output/design-context.jpg`、`output/design-backup-preview.jpg`：上下文、备份校验。
- `output/design-responsive-900.jpg`、`output/design-responsive-430-graphs.jpg`、`output/design-responsive-430-settings.jpg`、`output/design-responsive-430-chat.jpg`、`output/design-responsive-430-source.jpg`：屏幕适配。
- `output/design-knowledge-load-error.jpg`、`output/design-source-load-error.jpg`、`output/design-baseline-failure.jpg`：故障反馈。

临时屏幕尺寸与网络阻断在验收后恢复，独立验收服务停止。正式 `8765` 与旧版 `8775` 继续运行。最终服务状态记录在 `output/design-final-service-proof.json`。
