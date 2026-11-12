# 参数复用命令验收

2026-11-12，参数复用改为显式 `/参数复用` 命令。

- 后端单元测试 `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_parameter_migration_mcp.py` 通过，13 项通过，覆盖命令前缀识别、误匹配拦截、参数规则判断、重名字段、模块筛选和工作簿指纹校验。
- 前端命令测试 `node --test tests/chat/composer-commands.test.mjs` 通过，2 项通过，确认菜单包含“参数复用”，旧的 `/修改代码` 命令不再识别。
- 普通问题不会加载 `parameter_reuse` MCP，只有显式 `/参数复用` 前缀才进入参数复用流程。
