# 用户端模型切换

日期：2026-10-27。

原输入框的模型下拉框通过 `PUT /api/settings` 修改全局配置，普通用户被管理员权限检查拒绝。现在使用 `GET/PUT /api/model-preference` 读取和保存个人选择，仅接受已有配置的 `profile_id`；模型地址、凭据和系统默认配置仍由管理员维护。

`model_preferences` 表以账号 ID 为主键，迁移 0025 为旧数据库新增空表。选择跨项目、刷新、重新登录和服务重启保留；无选择或配置被删除时回退到系统默认模型。接口只返回 ID、名称和模型名，不返回地址或密钥。

运行开始时按消息保存的发起人读取配置并冻结本轮快照，后台出队不能使用其他任务的账号。继续/重新生成使用当前发起账号的选择。运行中的模型和凭据不会因切换而变化；上下文装配和容量读取也使用个人选择。全局配置变更及个人选择变更会通知其他窗口重读选择和上下文。

验证结果：

- 后端定向 45 项通过：个人选择的真实登录/CSRF/权限、非法输入、持久化、账号隔离、删除配置回退、迁移幂等、运行配置快照、重新生成、上下文和压缩回归。测试数据均位于临时目录。
- 前端 346 项通过，包括模型选择事件的实际请求载荷、成功/失败缓存处理、等待禁用、全局路由和窗口通知；TypeScript 和生产构建通过。
- 隔离的 8766 页面使用普通测试账号，实际展开列表并切换到备用模型，刷新后选中项保留。截图：`output/model-selection-ui/selected-model.png`。未向正式账号写入测试偏好，未发起外部模型调用。
- Ruff 检查通过。本轮未采集覆盖率，未验证供应商服务的连通性或生成质量。

复现命令：在 backend 运行 `.venv/Scripts/python.exe -m pytest tests/integration/settings tests/integration/auth/test_authentication.py tests/integration/agents/test_context_budget.py tests/integration/agents/test_compaction.py tests/integration/test_action_timing_ledger_migration.py -q`；在 frontend 运行 `npm test`、`npm run build`。
