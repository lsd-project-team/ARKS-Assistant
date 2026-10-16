# 验证脚本

默认回归分别在 `backend/` 运行 `uv run pytest -q`，在 `frontend/` 运行 `npm test` 和 `npm run build`。这些测试使用隔离数据目录与测试模型。

本目录中的模型验收脚本需要显式执行，会读取本机模型配置并请求供应商；它们不属于默认测试，也不会由启动脚本自动运行。

| 脚本 | 用途 |
| --- | --- |
| `live_validation.py` | 在临时数据目录验证真实模型压缩、档案和历史检索 |
| `evaluate_quality.py` | 既有回答质量验收场景 |
| `evaluate_audit.py` | 既有源码审计验收场景 |
| `evaluate_analysis_upgrade.py` | 既有分析能力升级验收场景 |
| `data_snapshot.py` | 历史回答质量验收的数据快照辅助 |
| `verify_preservation.py` | 比对历史质量验收约定的基线快照，依赖其输出文件和接口访问条件 |

以上历史场景的结果不能作为当前版本的自动验收结论。本次工程重构使用的基线、测试日志、路由和数据核对报告保存在项目本机忽略目录 `output/refactoring/`，最终记录见 [重构清单](../../docs/architecture/refactoring.md)。
