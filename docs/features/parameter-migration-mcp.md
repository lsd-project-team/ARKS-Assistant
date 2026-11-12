# ZX2200 参数复用 MCP

在 ARKS 聊天中使用 `/参数复用` 加参数或模块文本，例如 `/参数复用 点胶针偏移`。MCP 返回结论、核对条件，以及工作表和行号依据。回答统一显示为“ZX2200 参数复用 MCP”，不显示工作簿文件名。重名字段可用 `库.字段名` 指定，例如 `Dispenser.EditState`。

## 在 ARKS 中登记

管理员在“设置 → MCP”添加本地 stdio 服务。服务 ID 填 `parameter_reuse`，命令填 ARKS 的 Python 解释器绝对路径。依次添加以下三个参数，每项各占一行。

```text
<仓库绝对路径>/backend/app/modules/parameter_migration/mcp_server.py
--workbook
<数据目录绝对路径>/parameter-migration/传输字段保护默认状态工艺确认表.xlsx
```

把原工作簿复制到上述数据目录，再使用设置页的“测试连接”确认 `lookup` 工具可用。服务启动时核对工作簿 SHA-256、表头、行数和库名与字段名组合，按只读模式使用 `工艺确认清单!A4:H538`。部署时通过本机数据目录提供工作簿。

## 复用结论

| MCP 依据 | 回答 |
|---|---|
| 配方共用、默认不保护、程序登记一致 | 按 MCP 规则可随配方跨设备下发。指定目标机时核对产品、工艺或配置的适用性。 |
| 默认保护、程序登记一致 | 按 MCP 规则保留目标机值，结合类别说明坐标、标定、示教、硬件或运行状态的核对事项。 |
| 程序未登记、工艺与程序冲突、程序未找到字段，或规则证据不足 | 暂不能确认直接复用，给出待核对的依据。MCP 默认保护计划要求保护时，注明应保留目标机值。 |

点胶模块按 MCP 规则中的 `Dispenser`、`EpoxyApplication` 两个库及其他库中文说明含“点胶”的字段查询。`decision_summary` 统计全部匹配项的复用结论，`default_protection_counts` 统计默认保护值，`next_offset` 用于继续查询明细。

## 真实模型验收

从仓库根目录运行以下命令。脚本读取已登记的 MCP 和当前模型配置，使用独立账号、数据目录和聊天会话，通过 ARKS 的 API 实际提问并记录工具调用与答复。

```powershell
.\backend\.venv\Scripts\python.exe -X utf8 .\scripts\verification\parameter_migration_mcp.py --live --output .\output\parameter-migration-mcp\live.json
```
