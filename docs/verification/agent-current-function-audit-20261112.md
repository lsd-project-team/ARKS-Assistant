# agent.md 当前功能核对

2026-11-12，清理当前功能表中已失效的“代码修改流程已移除”说明，并按现有代码改为独立 Simulation 副本流程。

- 后端单元测试 92 项、代码工作对话集成测试 9 项、提示词组合测试 6 项全部通过，覆盖副本创建、读取、编辑、验证、对话闭环和工具入口。
- 前端 `node --test tests/chat/code-work.test.mjs tests/app/code-work-panel.test.mjs` 22 项全部通过，覆盖代码修改入口和面板行为。
- 当前实现仍保留 `prepare_code_workspace`、`edit_work_file`、`verify_code_workspace` 及代码修改面板，因此不再把代码修改能力描述为已完整移除。
