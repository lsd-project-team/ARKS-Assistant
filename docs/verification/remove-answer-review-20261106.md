# 移除回答生成后的来源检查

日期：2026-11-06。

## 行为变化

按用户要求，新问答不再装配 `SourceEvidenceGuard`、`KnowledgeAnswerGuard` 和 `AnswerReviewNote`：回答完成后不再检查源码引用的路径、行号、版本和目录，不再调用历史经验事实复核模型，不自动追加“注意”说明。结束时的经验引用归一化也不再调用，避免继续把未登记的引用改成“资料引用未核对”。

执行器移除等待来源检查完成才发布正文的分支，源码和经验回答正常发送 token。按实际已展示文本决定是否同步最终正文，避免完整度中间件已经发布后又重复发送相同替换事件。回答、富内容、模型输出的引用和历史均继续按原存储及展示协议处理。

新运行不再产生回答后的 `answer_validation`、`knowledge_answer_check`、`knowledge_answer_review`、`source_review`、`answer_review_note` 事件，不登记已验证引用或语义复核快照。历史运行记录和独立校验接口仍兼容；这些校验中间件不进入新问答图。

保留检索前的相关性筛选、所选原文片段和固定快照、有效分支历史及记忆筛选、输入预算、输出完整度与富内容语法修复。源码读取和附件接口的路径、版本、账号及项目边界，副本编辑/编译/仿真的约束继续生效。现有 `checking_sources` 阶段用于相关性筛选，界面名称改为“筛选相关资料”。

经验结果充足的回归模型现在只经过“主模型 → 资料筛选 → 主模型”，不会再进入回答后的 verification 调用。这里不表示所有问答只调用一次模型：工具、历史/记忆筛选、上下文压缩和格式修复仍按实际需要发生。

## 测试结果

修改前选源、普通问题和经验检索专项基线：**49 passed**。

最终后端在 **64 个测试文件**中收集 **660 项**：**659 passed、0 failed、1 skipped**。跳过原因为本机 Windows 未启用创建符号链接权限；既有重复 ZIP 文件名反例构造时产生 1 条 `Duplicate name` 警告，对应拒绝行为通过。

范围为 `tests/integration/agents`、`tests/integration/chat`、`tests/integration/source_analysis`、`tests/unit/agents`、`tests/unit/chat` 和 `tests/architecture`。其中覆盖经验、混合来源、重生成、流式输出及图装配的定向组合先完成 **92 passed**，最终扩展回归包含其全部用例及新增引用反例，不累加重叠执行数量。

关键反例与保留断言：

- 图装配明确排除三个已移除的检查中间件，来源开关、指令、检索工具、预算及副本工具继续按原配置生效。
- 经验主模型只接收被选片段；无关候选、未选片段和筛选失败的候选仍不进入正文上下文。模拟主模型把42写成43时，确认没有另一个复核请求或自动补句，不把未执行的核查记为通过。
- 源码、经验和混合路径均实际走 Agent 图；禁止调用回答后的 `SourceEvidence.check`，同时验证实际来源读取、工具顺序、原文及 token 输出。
- 未登记经验引用和不存在的源码引用按模型原样保存，不再被末尾检查改写。缺行号、错版本、异目录及重生成场景不追加说明，生成前恢复历史读取时仍排除异版本和异目录证据。
- 原图/表格/流程图、分页读取、HTTP/SSE 重放、历史保存、取消/恢复、长回答续写、来源权限、上下文不可压缩拒绝和副本流程继续回归。

旧的自动补句、最终复核和等待完成才出正文断言按用户的新行为更新，保留原文、引用、来源记录、调用次数和持久化断言，没有通过隐藏生产失败获得通过结果。

测试中还发现16K上下文夹具已不足以容纳当前完整工具定义及源码规则。使用独立测试进程重新装载修改前 HEAD 的图和执行器，复现原快照用例的15071 token请求超过15052输入预算。配置快照和结构化回答用例改用32K，快照检查仍在之后改配置至64K并断言原32K配置保留；8K不可压缩请求的拒绝反例继续执行。没有调整正式模型配置或生产预算限制。

前端全部 **450 passed、0 failed、0 skipped**；改动文件 Prettier、TypeScript、源码/模块资料检查、Agent 知识索引和生产构建通过。候选构建位于 `output/remove-answer-review-release/`。后端改动文件及相关测试的 Ruff 规则与格式检查通过。

未采集覆盖率。质量判断：在新问答调用链、输出/事件、来源筛选与生命周期范围内为高，有真实 Agent 图、工具、临时数据库和具体反例；模型使用确定性替身，未调用真实供应商，也未据此评估真实模型回答准确率或设备行为。历史校验辅助函数的单独回归不代表新问答仍会执行它们。

## 复现命令

在 `backend/`：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q tests/integration/agents tests/integration/chat tests/integration/source_analysis tests/unit/agents tests/unit/chat tests/architecture --tb=short --junitxml=../output/remove-answer-review-final.xml
```

在 `frontend/`：

```powershell
npm test
npx prettier --check src/features/chat/lib/runFeedback.ts
npm run build -- --outDir ../output/remove-answer-review-release --logLevel warn
```

最终 XML、前端测试日志和修改前图的隔离复现材料在忽略目录 `output/`。当前使用说明见[查询路由](../features/query-routing.md)。

## 本机更新与数据保护

更新前确认活动运行和待发问题均为0，完整备份为 `data/backups/trunk-agent-20261106-135115-720010.zip`。保留旧前端哈希资源，先复制候选资源与清单、最后原子替换首页；121项公开资源文件指纹核对通过。

通过既有脚本核对服务身份并重启本机8765后端，PID由53404变为31540。更新后健康检查通过，实际首页与本轮候选构建一致。前后3个项目、30个对话、159条消息、81次运行、14732条运行事件、13个附件、87条交接记录和3个账号的数量及完整行内容摘要全部一致，没有重写历史回答或核查记录。

后端重启沿用原有会话撤销规则，使用前需要刷新并重新登录。发布前后证据及旧首页/清单保存在 `output/remove-answer-review-deployment/`。
