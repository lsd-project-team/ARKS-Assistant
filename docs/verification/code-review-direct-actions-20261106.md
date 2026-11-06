# 变更状态栏操作精简

日期：2026-11-06。

用户明确要求只保留菜单中的左右对照切换与合并，并放到状态栏，移除该菜单。本轮将两项操作改为顶部状态栏的直接按钮，带中文提示、按钮名称和状态；删除顶部“更多”按钮与菜单，清理换行、全部展开/收起、历史列表、下载修改和工程信息入口及专用状态、请求、组件和样式。

文件自己的复制路径、撤销菜单继续使用原键盘与焦点行为。范围选择仍可读取历史快照，当前验证状态与日志、执行/停止和关闭继续可用。合并只进入现有预览流程，不直接写回；管理员确认、版本检查、运行与恢复保护不变。全局环境设置仍由管理员系统配置维护。没有修改后端接口、历史档案或正式业务数据。

## 验证

`code-work.test.mjs`、`code-diff-view.test.mjs`、`code-change-summary.test.mjs` 和 `code-work-panel.test.mjs` 共 4 文件、28 项通过，0 失败、0 跳过。原菜单用例改为断言顶部直接入口和其他菜单项消失，方向键、Escape 与外部关闭回归转到保留的文件菜单；多个文件通过各自标题展开收起，顶部切换同时影响所有展开差异。现有历史只读、精确版本撤销、验证互斥、选区反馈、普通用户合并只读与管理员确认回归继续通过。

完整生产构建通过，包括源码说明、资料、Agent 索引、TypeScript 和 Vite；修改文件的 Prettier 与 Git 差异检查通过。删除无调用的 `WorkHistory.tsx`、`WorkspaceInfo.tsx`，管理员配置仍正常引用 `CodeEnvironmentPanel`。

实际 8765 页面刷新后继续登录。顶部状态栏直接显示“切换为左右对照”和“合并”，其 `aria-haspopup=menu` 数量为 0；点击前者确认差异变为 split，再次点击恢复 single；点击合并进入原有合并页面，返回后仍为单栏。没有生成合并候选、执行验证或写回。最终状态记录为 `output/code-review-direct-actions/ui-state.json`，截图为同目录的 `statusbar.jpg`。

## 发布

候选 `output/code-review-direct-actions-release/` 已热更新至 `frontend/dist/`，保留旧哈希资源，先复制资源和清单，再原子替换首页。前后后端 PID 均为 31540，服务未重启；首页与候选一致，121 项公开资源匿名 HEAD 均为 200，变更业务分包匿名返回 401，健康接口正常。旧首页和清单位于 `output/code-review-direct-actions/production-before/`，发布记录为 `output/code-review-direct-actions/deployment.json`。

覆盖率未采集；未运行真实模型、C# 编译、设备验证或整仓后端回归。质量判断为中：入口移除、直接切换与导航已做回归和实际页面检查，未穷举所有主题、窗口尺寸和辅助技术组合。
