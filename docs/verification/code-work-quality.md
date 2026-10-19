# 代码工作真实模型质量验收

本套件是可显式运行的证据采集和人工评审入口，不代表已完成当前模型质量验收，也不证明已理解全部 C#。本轮只运行临时文件、SQLite、真实 Agent 图和供应商替身；没有调用真实供应商。Windows 执行适配、ZX2200 构建、设备及工艺验收仍需各自完成。

以上为套件实现时的验证范围。2026-10-19 已按用户明确的三类合成案例和无 Token 总预算执行当前供应商，并保留失败、修正及定向复测，见 [当前模型验收](current-model-quality.md)。人工语义评审、命令验证及真实业务验收仍未完成。

## 已有能力与复用范围

历史上已有真实供应商验收，不能概括成只有确定性测试。`scripts/verification/evaluate_quality.py`、`evaluate_audit.py`、`evaluate_analysis_upgrade.py` 复用 AgentRuntime，在隔离数据库内采集回答、源码证据、引用检查、AI 复核与供应商用量。`live_validation.py` 验证压缩档案和原历史检索。

本轮只读核对了旧产物元数据：`output/quality-evaluation/report.json` 标记 DeepSeek-V4-Flash，含五个场景、各自运行 ID、源码版本字段及 21 个用量事件；`output/quality-audit/report.json` 含单次运行、17 个源码证据、19 个用量及两次源码复核事件。这些是历史证据，不能当成当前代码、模型配置和新增代码工作能力的质量结论。旧说明见 [回答质量升级记录](answer-quality-upgrade.md)。

旧脚本包含自动读取本机正式配置、固定输出目录和部分写入配置副本的做法。本套件不复用这部分入口；复用的是应用已有的服务装配、执行图、引用校验、调试库检索和隔离编辑能力，没有另造 Agent。

## 运行边界

- `run` 必须同时给出 `--live`、独立配置、场景清单、源码目录和报告目录。没有 `--live` 时，在读取配置和创建模型前拒绝运行。运行会消耗实际 API 和 Token，时间上限不是金额上限。
- 配置只允许公开模型字段及一个明确命名的环境变量；JSON 中禁止 `api_key` 等额外字段。密钥仅从该环境变量进入内存，不读取正式 SettingsStore，不保存密钥配置。模型、压缩、复核等实际请求共享每场景的项目 Token 账本；没有供应商实报用量时保留预留额度。
- `token_limit` 默认 100000；明确设为 JSON `null` 可取消本次套件的 Token 额度拦截，实际用量、预留和次数仍记录。有限额度范围保持 1000–1000000；无上限不会修改正式项目策略，也不解除模型上下文、回复长度、工具次数或场景超时。
- 每个场景使用一次性数据库、检查点、问题库和隔离副本；MCP、DeepWiki、个人记忆和自动记忆关闭。只允许该场景明确提供的教学或审核过的调试记录，不复制正式对话或问题库。
- 源码、配置、场景和输出位置互相隔离。正式 `data`、应用内部目录、它们的父目录及别名指向均拒绝；`trunk` 仅可作为显式指定的只读源码。源码链接和越界文件由已有副本清单规则拒绝。套件不自动恢复发生外部变化的原件。
- 每个场景先匹配 `expected_sources` 中的实际 SHA256，再创建模型。报告保存整个受扫描源码清单和聚合指纹、场景清单指纹、应用 Python 文件指纹、公开模型配置指纹及每个运行 ID。
- 每次输出到独立随机目录，报告逐场景保存。默认不保存临时数据库；报告内文本按既有敏感值规则脱敏，并去除本次实际 API 密钥。补丁回放使用脱敏前内容；报告中的脱敏补丁不能直接作为可交付代码使用。
- 可选验证配置只接受固定镜像的容器配置，还须显式 `--allow-verification`。它不会静默降级为宿主执行，不自动准备镜像。节点不可用就记录失败或未知，不能伪造验证通过。

## 场景与结果

`python -m scripts.verification.code_work_quality sample <新目录>` 生成小型 C# / Python 教学夹具、真实文件哈希、三个场景和公开配置模板。已有目录拒绝覆盖。这些示例不包含 ZX2200 的业务 ground truth。

| 场景           | 自动采集                                                                   | 人工必须核对                                             |
| -------------- | -------------------------------------------------------------------------- | -------------------------------------------------------- |
| 当前源码问答   | 当前路径、行号、读取覆盖与 SHA256，AI 复核事件单列                         | 条件、调用顺序、未读范围、推断及未知是否正确             |
| 新需求隔离编辑 | 修改 ID、差异、原件哈希；真实 Git 应用及反向回退后的字节清单；可选命令记录 | 是否满足需求、是否存在无关行为、异常与兼容性是否考虑完整 |
| 调试经验复用   | 临时问题 ID、固定修订号、实际注入或检索引用和条件报告                      | 是否混淆设备/版本/工况，是否把未解决记录当成已验证方案   |

自动检查仅产生机械事实的 `pass / failed / unknown`。例如补丁确实可应用，只能证明对应文件变换可回放；它不证明实现满足业务需求。出现引用不符、原件改变或非法补丁时记录失败。没有运行沙箱命令则其状态是 unknown。即使机械检查全部通过，场景语义和整份报告仍是 unknown，不能用回答中出现某个词或模型自称“通过”自动判优。

每个 case 的 `rubric` 由评测设计者预先填写，人工需逐项给出结论、理由和报告内依据位置。语义评审是人工自报记录，不冒充签名认证、需求批准或设备验收。全项目 C# 理解需另有经业务人员审核的模块/调用路径场景与覆盖清单；少数例题、文件数量和索引率都不能替代它。

## 显式运行示例

从仓库根目录运行。以下命令仅展示用法；本轮未执行带 `--live` 的真实供应商调用。

```powershell
backend/.venv/Scripts/python.exe -m scripts.verification.code_work_quality sample C:/Temp/cw-quality-demo
```

先编辑 `provider.example.json` 的公开模型地址和名称，通过独立秘密注入方式设置 `CODE_WORK_QUALITY_API_KEY`，并人工确认场景、源码范围和 Token 上限。不要把密钥放在 JSON、命令参数、日志或场景问题里。

```powershell
backend/.venv/Scripts/python.exe -m scripts.verification.code_work_quality run --cases C:/Temp/cw-quality-demo/cases.json --workspace C:/Temp/cw-quality-demo/workspace --config C:/Temp/cw-quality-demo/provider.example.json --output output/code-work-quality --live
```

报告的 `source_review_context` 事件记录复核器实际收到的资料版本、范围与脱敏输入哈希，`code_change_reference` 只记录工具观察过的修改身份；它们不代替人工 ratings。实际复测见[复核证据验收](source-review-context.md)。

程序输出唯一报告位置和报告 SHA256。保留原始报告，不手改后沿用旧评审。以 `current-source` 的 rubric 为例，另存人工填写的 `ratings.json`：

```json
{
  "branch": {
    "outcome": "unknown",
    "rationale": "尚未人工核对每个分支",
    "evidence": ["cases.current-source.answer"]
  },
  "evidence": {
    "outcome": "unknown",
    "rationale": "尚未复核引用支持的具体结论",
    "evidence": ["cases.current-source.checks.current_citations"]
  }
}
```

```powershell
backend/.venv/Scripts/python.exe -m scripts.verification.code_work_quality review --report <report.json> --report-sha256 <刚审阅的64位哈希> --case-id current-source --reviewer <人工评审标识> --ratings C:/Temp/ratings.json
backend/.venv/Scripts/python.exe -m scripts.verification.code_work_quality verify-review --report <report.json> --review <review.json>
```

评审绑定报告原始字节哈希、运行 ID、源码/模型/应用指纹。报告改动后旧评审失效；机械失败不能被人工填 `pass` 提升为通过；任一必需项 unknown 则仍是 unknown。没有配置沙箱的修改场景，人工语义通过也不表示编译、测试或可交付性通过。

## 本轮验证与未验收项

本节保留评测入口初建时的范围。2026-10-19 的后续真实供应商结果分别见 [三类合成场景](current-model-quality.md)、[合成修改与Linux沙箱](model-sandbox.md)、[首个业务源码案例](calibration-grid-case.md)，不覆盖或合并本节的历史测试统计。

测试使用真实临时应用服务、Agent 图、工具、SQLite 和供应商回调，外部模型为确定性替身。反例覆盖不带 `--live`、源码哈希不符、内部目录、过期引用、非法补丁、报告修改后旧评审失效，以及凭据字段输入。本轮覆盖率未采集。

真实供应商上的当前模型效果、模型间比较、完整 C# 阅读理解、私有依赖构建、Windows 执行、设备现场结果和人工业务验收尚未进行。完成这些工作后应追加新的固定报告及人工评审，不覆盖本记录中的未知边界。
