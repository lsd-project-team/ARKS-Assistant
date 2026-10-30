# 主提示词精简与专项规则按需追加

2026-10-30，按用户确认调整 ARKS 的 `SYSTEM_PROMPT`，供用户实际问答测试。

## 实现

- `SYSTEM_PROMPT` 从修改前工作区的 1750 字符精简为 694 字符，保留回答方式、事实边界和信任规则。
- 将详细源码核查规则独立为 `SOURCE_GUIDANCE`。源码意图、选区、恢复的已读证据及深度分析会在首次主模型请求前带入；其他问法实际选择源码工具后，在下一次请求前追加。
- 每轮使用独立的 `TaskGuidance` 实例；规则只追加到模型请求，不写入聊天历史，不增加模型分类调用。
- 流程规则合并至现有展示协议，仅在源码相关的流程问题中追加；项目分析报告规则仅在深度分析中追加。
- 保留源码读取、主工程优先、真实路径与行号引用、本地源码优先于 Wiki、硬件状态和外部库参数不得猜测等要求。源码证据核查、经验事实核查、检索工具和固定版本引用机制不改。
- 本次不修改正式业务记录、图片、历史版本、模型配置或用户的全局指令。

## 检查

工作区使用项目虚拟环境运行以下 9 个文件，共 **129 passed**：

- `tests/unit/agents/test_task_guidance.py`
- `tests/integration/agents/test_task_guidance.py`
- `tests/integration/agents/test_prompt_composition.py`
- `tests/integration/agents/test_device_business.py`
- `tests/unit/agents/test_answer_draft.py`
- `tests/integration/agents/test_knowledge_answer.py`
- `tests/integration/agents/test_model_privacy_budget.py`
- `tests/integration/chat/test_source_flow_with_knowledge.py`
- `tests/integration/chat/test_general_with_knowledge.py`

新增反例覆盖普通问答不带设备规则、首次源码请求、工具选择后的追加、选区与恢复证据、非源码工具与临时文件读取、跨轮隔离、深度任务及请求内容与元数据保留。集成测试实际编译并运行 Agent 图，模型使用确定性替身。

本次修改的 Python 文件通过 Ruff 检查与格式检查。初次新增集成用例遗漏运行结束保存步骤，导致创建下一轮时触发忙碌保护；补齐测试生命周期后通过，未削弱保护或修改业务状态规则。

另外从 Git 基线建立独立候选快照，只叠加本次修改，执行新增规则、实际图调用、提示词装配和设备业务 4 个文件，共 **36 passed**，确认本次提交不依赖工作区中其他任务尚未提交的改动。

## 限制

未采集覆盖率；未调用真实模型、远程 MCP 或设备。自动化结果验证规则装配和既有核查链路，不能证明回答质量已经提升，实际表达和相关性由用户继续测试。质量判断为中等：行为及边界有回归，真实模型效果尚未验收。
