# 左栏中文字体验收

日期：2026-11-09。

## 修改范围

仅在 `sidebar-navigation.css` 的 `.legacy-visual .app-navigation` 中覆盖 `--font-ui` 并设置 `font-family`：保留系统英文界面字体，将 `Microsoft YaHei UI`、`Microsoft YaHei` 放在通用回退之前。导航按钮、项目/对话列表及使用 `font` 简写的底部外观、设置按钮共用该局部变量；导航外字体变量不变。

主文字 16px、辅助文字 13px，以及既有行高、字重、列宽、布局、长标题省略、滚动、折叠及深浅色阶保留。未修改组件、事件、AI 回复、代码、后端或正式数据；未分发微软字体文件，缺少对应字体的平台继续按系统回退。

## 检查结果

- 前端 82 个既有测试文件，**453 passed、0 failed、0 skipped**；日志 `output/sidebar-font-20261109/tests.log`。
- 完整 `npm run build -- --outDir ../output/sidebar-font-release --logLevel warn` 通过，包含源码/模块资料核对、资料索引、TypeScript 和生产构建；日志 `build.log`。
- CSS、功能说明及本文通过 Prettier，提交前执行 Git 空白检查。未新增镜像式 CSS 单测；未采集覆盖率，未运行后端、真实模型或设备测试。

## 浏览器对照

Windows、Chrome 156.0.8078.74，隔离页面使用真实 `WorkspaceNavigation`、`AnswerMarkdown` 及固定示例会话列表，加载基线/候选的入口 CSS 和后加载的 ProjectShell CSS。API 使用替身，不连接正式资料或模型。

- 纯白、深色、灰绿 × 220px、290px、360px，共 9 组前后对照；主辅文字的字号、行高、字重、间距、颜色等非字体属性完全一致。
- 导航容器、品牌区、主功能、会话分组、项目行、会话行及底栏的边界位置与尺寸一致，无整体横向溢出，长标题保留省略。
- `CSS.getPlatformFontsForNode` 确认主导航、项目分组标题、中文对话标题、工作区说明、外观和设置文字实际使用 `Microsoft YaHei UI`，不是根据 CSS 栈推断。外观按钮的空格及分隔符继续使用 Segoe UI。
- 导航外的工具栏、AI 回复、代码及输入框标本计算样式与基线一致。
- 真实导航收起为 68px、展开恢复 290px，键盘焦点分别移至展开/收起按钮；新对话和设置回调正常。
- 已目视检查纯白与深色截图。独立浏览器和临时服务在检查结束后关闭。

数据：`output/sidebar-font-20261109/ui-results.json`；截图：`white.png`、`dark.png`。固定会话列表及回调标本不作为正式会话 API 的新验收。

## 发布

仅热更新前端，保留旧哈希资源并最后替换首页。发布前后后端 PID 均为 **31540**，未重启服务或撤销登录；121 项公开资源 HEAD 检查通过，候选与发布首页 SHA256 一致。另通过 HTTP 获取首页及入口 CSS，确认与候选文件摘要一致。记录位于 `output/sidebar-font-20261109/final-release.json` 和 `live-verification.json`。未写入正式库测试资料，`trunk/` 保持只读。
