# 验证脚本

`rich_content_roundtrip.py --live` 使用当前真实供应商，在临时账号、源码、数据库及附件上验证新增富内容块的生成、现有 HTTP/SSE、重连重放、多轮历史及前端引擎渲染；只读正式配置至内存，不复制密钥或业务历史。需要前后端依赖，明确消耗模型额度，结果只写入 `output/`。见[本轮验收](../../docs/verification/rich-content-roundtrip-20261030.md)。

`arks_rich_content.py --live --settings-data <正式配置所在目录> --output output/arks-rich-content/live.json` 使用截图蓝膜案例的问答副本，在独立临时账号与数据库上验证两轮真实经验图文、事实修订、引用、HTTP/SSE重放、历史及前端图形。仅将配置读入内存，不读取正式会话、不向正式知识库写入样例；无历史原图也必须生成有依据的示意图。需要前后端依赖，消耗当前供应商额度，见[专项验收](../../docs/verification/arks-rich-content-20261030.md)。

默认回归分别在 `backend/` 运行 `uv run pytest -q`，在 `frontend/` 运行 `npm test` 和 `npm run build`。这些测试使用隔离数据目录与测试模型。

真实供应商类脚本需要显式执行并消耗 API 额度，不属于默认测试，也不会由启动脚本自动运行。下表区分历史入口、独立配置质量套件和不调用供应商的离线验收。

| 脚本                           | 用途                                                                                                                                                                                                                                                              |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `live_validation.py`           | 在临时数据目录验证真实模型压缩、档案和历史检索                                                                                                                                                                                                                    |
| `answer_style.py`              | `--live` 显式用当前模型验证经验归纳、事实边界、原文保留和长段历史下的阅读结构；仅临时蓝膜案例与合成历史，见[归纳验收](../../docs/verification/grounded-answer-style.md)与[阅读体验验收](../../docs/verification/readable-answer-style.md)                         |
| `answer_quality/`              | `python -m scripts.verification.answer_quality --live --output output/answer-quality-20/run`：当前模型20题，15经验+5流程；固定种子随机排列，隔离数据与源码选区，逐题保存事实核对及视觉评估证据，见[评分约定](../../docs/verification/answer-quality-20-rubric.md) |
| `evaluate_quality.py`          | 既有回答质量验收场景                                                                                                                                                                                                                                              |
| `evaluate_audit.py`            | 既有源码审计验收场景                                                                                                                                                                                                                                              |
| `evaluate_analysis_upgrade.py` | 既有分析能力升级验收场景                                                                                                                                                                                                                                          |
| `data_snapshot.py`             | 历史回答质量验收的数据快照辅助                                                                                                                                                                                                                                    |
| `verify_preservation.py`       | 比对历史质量验收约定的基线快照，依赖其输出文件和接口访问条件                                                                                                                                                                                                      |
| `linux_runtime/`               | 无模型调用的真实 Linux HTTP、Roslyn、持久化和恢复验收                                                                                                                                                                                                             |
| `linux_semantic.py`            | 只使用公开本地权重和临时问题库的断网 Linux 语义检索验收，见 [执行与结果](../../docs/verification/linux-semantic.md)                                                                                                                                               |

以上历史场景的结果不能作为当前版本的自动验收结论。本次工程重构使用的基线、测试日志、路由和数据核对报告保存在项目本机忽略目录 `output/refactoring/`，最终记录见 [重构清单](../../docs/architecture/refactoring.md)。

20题套件须先逐题对照资料、源码和浏览器实际渲染填写 `grades.json`，再运行 `python -m scripts.verification.answer_quality.report 新批次目录 基线目录` 生成全部20题前后变化；题集或数据指纹不同会拒绝比较，不能拼接不同版本的较好答案。最新结果见[筛选、事实核查与排版分离复测](../../docs/verification/answer-quality-split-20261020.md)：准确性改善，阅读均分未提升，保留全部失败与退步题。

`rich_content_ui.py` 默认仅使用隔离数据与可控模型；显式 `--live` 使用当前真实模型和只读 `trunk/`，会消耗额度。`--directory output/<已有隔离目录>` 可保留结果重启，`--live-token-budget` 仅设置临时项目额度，默认2,000,000；不清零已用量。真实模型页使用 `localhost`，正式历史页使用 `127.0.0.1`，避免登录 Cookie 相互覆盖。执行与限制见[Rich Content 真实验收](../../docs/verification/chat-rich-content-live-20261020.md)。
