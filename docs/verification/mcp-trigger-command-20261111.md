# MCP 触发命令验收

日期：2026-11-11。范围：ZX2200 参数复用 MCP 改为 `/参数复用` 命令触发。

## 行为变化

- `McpSettings` 新增可选字段 `trigger`。填写后该服务不参与模型按问题自动选择；只有消息开头的独立命令 `/参数复用` 才会接入，命令必须紧接空白或位于消息末尾。
- 触发一次后在同一对话的后续追问中保持接入，不需要重复输入命令；新对话重新从命令开始。同一对话内是否用过命令，按当前分支此前的用户消息判断。
- 命令只用于选择来源：进入模型的正文和 `question_text`、记忆检索文本都会去掉命令词，消息列表和历史记录仍显示用户输入的原文。
- 只有命令没有正文时直接返回“请在 /参数复用 后输入问题或参数名”，不调用模型；这与 `/记录问题` 的空正文处理一致。
- 接入时在系统提示中说明本轮由 `/命令` 指定该服务，相关问题优先使用它的工具；未接入时提示词不出现该服务的命令说明。
- 留空 `trigger` 的服务（DeepWiki 等）继续按原逻辑自动选择；来源开关仍先生效，关闭 DeepWiki 或未关联仓库时即使没有命令也不会接入。
- 设置页校验命令格式（中文、字母、数字、下划线、短横线，1–20 字符）、重复命令和与内置命令（`context`、`compact`、`记录问题`、`record-issue`）重名；`/参数复用` 形式的输入会去掉前导斜杠后保存。
- 新增 `GET /api/mcp/commands`，只返回已启用且有触发命令的服务名与命令词，供输入框 `/` 菜单提示；凭据和完整配置仍只在设置页接口返回。
- 前端输入框命令菜单合并服务端命令；选中后只填入 `/命令 ` 并聚焦输入框，问题由用户接着写。

## 测试结果

修改后：

- 后端定向用例 **29 passed**：`tests/unit/test_commands.py`、`tests/integration/agents/test_mcp_triggers.py`、`tests/integration/agents/test_source_options.py`、`tests/integration/infrastructure/test_mcp.py`、`tests/integration/settings/test_settings_profiles.py`。
- 后端更广回归 `tests/integration/agents tests/integration/settings tests/unit`：**664 passed、13 failed**。13 项集中在 `test_model_probe`、`test_provider_lifecycle` 和 1 个协议参数用例，均为未改动测试；清空 `HTTP_PROXY`、`HTTPS_PROXY`、`NO_PROXY` 等变量后同一批用例 **25 passed**，与本次改动无关，原因与[通用代码工作区验收](workspace-work-20261111.md)记录的本机代理变量（`NO_PROXY` 含 `[::1]`）一致。
- 前端 `npx tsc -b` 通过；`npm test` **452 passed、0 failed**。
- Ruff 与格式检查通过（`app/core/commands.py`、`app/core/config.py`、`app/agents/runtime/engine.py`、`app/agents/runtime/executor.py`、`app/agents/runtime/graph_builder.py`、`app/modules/settings/router.py`）。

关键反例：

- 不带命令的“点胶针偏移能直接复用吗？”不建立 MCP 连接，`remote_tools` 未被调用。
- `/参数复用` 开头的消息只接入 `parameter_reuse`，其余服务不接入；同一对话的下一问没有命令仍保持接入，新对话恢复不接入。
- 仅 `/参数复用` 的空命令抛错且不进入模型；`/参数复用的用法`、`解释 /参数复用 的用法`、代码块中的命令都不当作触发命令。
- 进入模型的用户消息与 `question_text` 不含命令词，保存的消息保留原文。
- 触发命令格式错误、重复或与内置命令重名时配置校验拒绝；未启用服务不出现在 `/api/mcp/commands` 中。

未采集覆盖率。模型使用确定性替身，没有调用真实供应商或参数复用 MCP 服务；本次验证的是命令选择、工具接入边界和提示词装配，不代表模型一定按提示优先调用 `lookup`，真实问答效果仍需在配置好 `parameter_reuse` 的环境中用 `/参数复用` 实测。

## 复现命令

在 `backend/`：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests/unit/test_commands.py tests/integration/agents/test_mcp_triggers.py tests/integration/agents/test_source_options.py tests/integration/infrastructure/test_mcp.py tests/integration/settings/test_settings_profiles.py -q
```

在 `frontend/`：

```powershell
npx tsc -b
npm test
```

## 使用与边界

在“设置 → MCP”给参数复用服务填写触发命令 `参数复用`，保存后在对话中输入 `/参数复用 点胶针偏移能直接复用吗？`。没有命令时按普通问答处理，不查询该规则库。说明见[参数复用 MCP](../features/parameter-migration-mcp.md)。
