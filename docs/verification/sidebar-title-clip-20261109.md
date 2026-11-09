# 左栏对话标题裁切验收

日期：2026-11-09。

## 范围

按用户对左栏对话标题末尾三个点的标注，在 `sidebar-navigation.css` 中仅增加 `.legacy-visual .app-navigation .sidebar .thread-title { text-overflow: clip; }`。

项目内、最近及回收站列表共用该展示规则：长标题仍单行裁切，不再由 CSS 绘制省略号。保存的标题、按钮 `title` 悬停提示、短标题、字号、行高、列宽、操作按钮及菜单保持。品牌、项目名和导航外的标题截断规则不变。未修改组件、后端、提示词或数据库。

## 自动检查

- 82 个既有前端测试文件，**453 passed、0 failed、0 skipped**，日志 `output/sidebar-title-clip-20261109/tests.log`。
- 完整 `npm run build -- --outDir ../output/sidebar-title-clip-release --logLevel warn` 通过，包含源码/模块资料核对、索引、TypeScript 及生产构建，日志 `build.log`。
- CSS、功能说明及本文通过 Prettier，提交前执行 Git 空白检查。
- 不新增镜像式 CSS 单测；未采集覆盖率，未运行后端、模型或设备测试。

## 浏览器与发布

Windows、Chrome 156.0.8078.74，隔离页面使用真实 `WorkspaceNavigation`、`ThreadItem` 和 `AnswerMarkdown`，会话数据固定、API 使用替身。加载发布前/候选入口 CSS 和后加载的 ProjectShell CSS，不连接正式会话或模型。

- 纯白、深色、灰绿 × 220px、290px、360px，共 9 组前后对照。基线可复现 `ellipsis`，候选长标题为 `clip`、`nowrap`、`overflow: hidden`，仍保持单行裁切。
- 对话标题的完整 DOM 文本和按钮 `title` 与基线逐项一致。除对话标题的 `text-overflow` 外，导航文字样式、字号、布局位置和尺寸完全一致，无整体横向溢出。
- 导航外的 AI 回复、代码及输入框标本与基线一致；品牌和项目名未改规则。
- 会话菜单仍可打开，Escape 关闭后焦点恢复到操作按钮；导航收起为 68px、展开恢复 290px，导航/设置回调正常。
- 已目视检查纯白与深色截图；独立浏览器和临时服务在验收后关闭。结果和截图位于 `output/sidebar-title-clip-20261109/ui-results.json`、`white.png`、`dark.png`。

仅热更新前端资源，保留旧哈希文件并最后替换首页。前后后端 PID 均为 **31540**，未重启服务或撤销登录；121 项公开资源 HEAD 检查通过。发布首页与候选 SHA256 一致，HTTP 首页和入口 CSS 的摘要也与候选一致。记录位于 `final-release.json`、`live-verification.json`。未写入正式库测试数据，`trunk/` 保持只读。
