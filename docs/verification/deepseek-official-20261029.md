# DeepSeek 官方 4.1 Flash 配置与验证

日期：2026-10-29。

## 配置结果

按用户要求，将本机现有 `default` 模型配置切换为 `DeepSeek 4.1 Flash（官方）`，保留配置 ID，使已选择该配置的账号继续使用同一入口。

| 项目 | 当前值 |
| --- | --- |
| API 模型名 | `deepseek-flash` |
| 接口协议 | Anthropic 兼容协议 |
| 接口地址 | `https://api.deepseek.com/anthropic` |
| 上下文配置 | 1,048,576 token |
| 单次输出上限 | 保留 4,096 token |
| 摘要模型 | 与主模型相同 |
| 思考模式 | 显式关闭，兼容强制工具调用 |

官方模型列表接口实际返回 `deepseek-flash`，名称为 `DeepSeek-V4.1-Flash`，上下文窗口为 1,048,576 token。官方文档说明该模型名当前由 DeepSeek-V4.1-Flash-1017 提供服务，见[首次调用说明](https://api-docs.deepseek.com/)和[模型列表接口](https://api-docs.deepseek.com/api/list-models/)。

密钥只写入本机被 Git 忽略的 `data/settings.private.json`，能力检测结果写入 `data/model-probes.json`。本文及提交内容不含真实密钥。配置通过 `SettingsStore.save` 的版本校验保存，并再次读取确认模型、地址、密钥匹配及检测缓存。

## 兼容修复

第一次真实检测的普通回复、流式输出、摘要通过，工具往返返回 400：`Thinking mode does not support this tool_choice`。

官方默认思考模式不接受强制工具选择，并要求工具上下文完整传回思考内容，见[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)和[Chat Completions 参数说明](https://api-docs.deepseek.com/api/create-chat-completion/)。当前程序没有思考模式配置入口，因此仅对主机名严格等于 `api.deepseek.com` 的请求显式关闭思考模式。OpenAI 和 Anthropic 两种适配均覆盖；其他供应商、相似域名和路径中出现该域名的代理不受影响。

修改文件：

- `backend/app/infrastructure/providers/models.py`
- `backend/tests/integration/settings/test_model_probe.py`

## 测试结果

| 验证范围 | 结果 |
| --- | --- |
| 官方模型列表 | 真实密钥认证通过，目标模型存在 |
| Anthropic：普通回复、流式输出、工具调用及结果回传、摘要 | 4 项通过 |
| OpenAI：普通回复、流式输出、工具调用及结果回传、摘要 | 4 项通过 |
| 设置、个人模型选择、模型连接生命周期和隐私预算回归 | 5 个测试文件，66 Passed / 0 Failed / 0 Skipped |
| 修改文件 Ruff 检查及格式检查 | 通过 |
| 本机服务 | 确认无活动对话后重启，`/api/health` 正常 |

回归命令，在 `backend/` 执行：

```powershell
.venv/Scripts/python.exe -m pytest -q tests/integration/settings tests/integration/agents/test_model_privacy_budget.py
.venv/Scripts/ruff.exe check app/infrastructure/providers/models.py tests/integration/settings/test_model_probe.py
.venv/Scripts/ruff.exe format --check app/infrastructure/providers/models.py tests/integration/settings/test_model_probe.py
```

测试使用真实 SDK，回归中的 HTTP 传输使用替身，覆盖两种协议、独立摘要模型、强制工具往返、相似域名、代理路径、失败脱敏与连接释放。真实供应商检测单独执行，使用固定短提示及无副作用的 `connection_check` 工具。

覆盖率未采集。测试质量判断为中等：SDK 请求序列化和两种协议的短请求均有确定性回归及真实调用证据；没有据此验证完整 1M 上下文、长时间高并发、设备业务回答质量或供应商长期稳定性。没有创建正式测试对话、账号或资料，也没有向供应商发送正式业务内容。
