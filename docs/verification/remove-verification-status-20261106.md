# 移除变更状态栏的验证状态按钮

日期：2026-11-06。

用户在了解“查看验证详情”图标用途后要求移除。本轮删除该独立入口、`VerificationSummary.tsx`、专用提示、隐藏文本及样式，当前副本状态栏从 5 个操作减至 4 个：差异切换、合并、执行/停止验证、关闭。

保留验证请求和停止接口。为继续呈现执行结果，点击 ▶ 提交验证请求成功后进入已有结果页，日志、过期提示、需求断言与测试编辑继续使用原组件；提交失败仍在当前页显示错误。验证运行期间的编辑互斥、恢复保护、历史只读和管理员合并确认不变。没有修改后端、正式业务数据或历史报告。

## 检查

`code-work.test.mjs`、`code-diff-view.test.mjs`、`code-change-summary.test.mjs`、`code-work-panel.test.mjs` 共 4 文件、28 项通过，0 失败、0 跳过。复用并调整原状态用例，验证按钮消失、顶部操作数、提交验证后进入结果页、停止与过期结果、基础回归范围说明、失败日志、需求用例版本保护，以及原有撤销、历史快照和合并保护。

完整生产构建通过，包含源码说明、资料、Agent 索引、TypeScript 和 Vite。修改文件的 Prettier 和 Git 差异检查通过。实际页面刷新后保留登录，变更状态栏仅有对照切换、合并、执行验证、关闭四个按钮，“查看验证详情”按钮数量为 0。未在正式页面启动验证或修改代码；结果页自动打开行为通过测试替身验证。页面状态记录为 `output/remove-verification-status/ui-state.json`，完整页面截图为同目录的 `statusbar.jpg`。

## 发布

候选 `output/remove-verification-status-release/` 已热更新到 `frontend/dist/`，保留旧哈希资产，先复制资源和清单、最后原子替换首页。前后后端 PID 均为 31540，无服务重启；首页与候选一致，121 项公开资源匿名 HEAD 均为 200，变更业务分包匿名返回 401，健康接口正常。原首页与清单保存在 `output/remove-verification-status/production-before/`，发布记录为 `output/remove-verification-status/deployment.json`。

覆盖率未采集，没有执行真实模型、C# 编译、设备验证或整仓后端回归。质量判断为中：入口移除有实际页面核对，保留的验证与保护流程有定向回归，未穷举全部主题、窗口尺寸和辅助技术组合。
