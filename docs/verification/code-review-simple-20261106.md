# 代码变更界面精简验收

日期：2026-11-06。

## Codex REA 静态参考

读取本机 Windows 包 `OpenAI.Codex_26.1029.7803.0_x64` 中的 `app/resources/app.asar`，包内版本 `26.1029.61003`。原 ASAR SHA256：`77ed4ddc5b388ac8b29f5035f9c98f982b095df55aad6fa6c27bb80d763b9691`。本轮只提取以下三个渲染模块，各文件实际哈希均与 ASAR 声明一致：

| ASAR 内路径（webview/assets/async/） | SHA256 | 静态观察 |
| --- | --- | --- |
| `626002.4f067611c3.js` | `6b0053e7f95d28b14399f83655d99fda3691159afb4737319dfba3084c98e01d` | `codex.diffView.filesChanged` 将文件数、增删统计集中在紧凑页头；支持统一、分栏及自动视图 |
| `88640.b8951146ec.js` | `6f1650e8563a35951286d6636676094fdf3264639f8b2bc9d1aa192a06f46af4` | `codex.review.header.moreOptions` 将换行、展开/收起等选项放进 Changes options 菜单 |
| `253790.25bf4df4cb.js` | `76ad11722b8ed4468d17b85ada2143e78071e68e6d7c150ff808623aa34be546` | `codex.diff.fileHeader.actions` 使用文件头图标菜单，包含复制路径、打开编辑器及按条件出现的文件操作 |

REA 目录分析父 Evidence：`ev_65edc199bf157b28a479ce6d4f2597100aa23a1ac575cef2d47c13d088dc809f`；摘要 Evidence：`ev_5e7f74b5e134ea5b42305e31e4e2bc51530ad8e01ed0eef9bad3ea1ec0a1f346`。选定三文件共 168440 字节、53431 AST 节点、零解析失败；目录身份摘要 `d35325032d7cea1802f45cc19443c01e7cdc71c1386afac726eaf6178bc66e63`。

观察仅限所选交付 JavaScript；没有操作 Codex 运行时，也不据此断言 Codex 全应用不存在验证、历史等功能。静态目录覆盖完整，跨模块及动态关系的语义覆盖未知（10857 个保守未解析关系）。“把高频差异留在主区，把次级选项放入菜单”是本项目据此采用的设计判断，单文件铺满及验证摘要是结合本项目需求的实现。第三方源码只保存在忽略目录 `output/codex-review-display-reference/`，没有复制到产品代码；出处与偏移见其中 `provenance.json`，REA 摘要保存为 `output/code-review-simple-rea.json`。

## 展示与行为

- 主区保留文件数量、验证入口、单行验证状态、代码差异及文件撤销。单文件不重复显示列表，多文件保留切换列表；文件名简写，完整路径保留在提示和辅助标签。
- “更多”统一提供验证详情、历史、合并、让 AI 修改、下载修改和工程信息。次级页面有返回按钮，不会仅因打开菜单或切页执行验证、编辑或写回。
- 去掉常驻工程路径、来源指纹、副本版本、四个页签、完整报告及泛用范围说明。它们仍可在工程信息或验证详情查看。恢复冲突与运行中的停止验证继续直接显示。
- 统一差异/左右对照改为一个下拉框；修改块操作默认折叠，选中代码才出现反馈表单。路径、精确版本、历史轮次、撤销确认、验证忙态与管理员合并权限继续沿用。
- 当前没有需求断言的成功显示“基础回归通过”；过期成功显示“需重新验证”。停止及失败保留摘要，日志通过“查看详情”读取。
- 右侧面板与管理员弹窗共用。菜单支持方向键、首尾、外部点击关闭和 Escape 焦点返回；弹窗把菜单内的 Escape 留给菜单，避免同时关闭整窗。

## 验证

| 范围 | 实际结果 |
| --- | --- |
| `frontend/tests/chat/code-work.test.mjs` 与 `code-change-summary.test.mjs` | 18 项通过，0 失败、0 跳过 |
| 前端全部回归 | 447 项通过，0 失败、0 跳过 |
| TypeScript、Vite 候选生产构建、修改文件 Prettier 与 Git 差异检查 | 通过 |
| `backend/tests/integration/auth/test_static_assets.py::test_actual_built_login_dependencies_and_private_knowledge_require_real_session`（实际候选） | 1 项通过 |

新增反例覆盖默认不显示次级内容、单文件铺满、只读切页不产生写入、菜单 Escape 不连带关闭面板、基础回归与需求验证的区别；既有用例继续覆盖精确文件/修改块撤销、版本冲突、忙态、历史只读及管理员写回确认。测试调整中的选择器与短文件名断言错误已修正，未改变原业务预期。

浏览器使用 `output/code-review-panel-ui/` 中的隔离测试账号、最小 C# 文件和明确构造的停止状态；没有写入正式业务数据，也没有将样例状态当作真实编译结果。1280px 视口检查聊天与精简右栏同屏、停止摘要、菜单 Escape、日志详情返回、修改块反馈和左右对照；管理员真实弹窗检查菜单内 Escape 只关闭菜单，再按一次可关闭弹窗，并在用户截图的 1053×892 尺寸保存最终效果。760px 断点确认工作区切换仍保留；展开导航会沿用既有覆盖层，未将该状态作为窄屏完整验收。临时视口已恢复，验收标签已关闭。

截图保存为 `output/code-review-simple-ui/compact-panel.jpg`、`compact-dialog.jpg` 和 `compact-menu.jpg`。覆盖率未采集；本轮只改前端展示，没有执行真实模型、编译或设备验收。质量判断为中：已覆盖关键入口与操作保护，未穷举全部浏览器、主题和辅助技术组合。

## 发布

已热更新本机 8765 服务。候选位于 `output/code-review-simple-release/`，资源与清单先复制、首页最后原子替换，保留所有旧哈希资源。发布前后后端 PID 均为 35024，健康接口正常，实际首页与候选逐字节一致，121 项公开资源指纹校验通过；无需重启后端，现有会话继续沿用。

旧首页和清单保存于 `output/code-review-simple-ui/production-before/`，发布核对为 `output/code-review-simple-deployment.json`；测试与构建日志在 `output/code-review-simple-*.log`。隔离预览服务在验收后停止。
