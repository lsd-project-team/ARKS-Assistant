# ZX2200 源码覆盖与目标达成审计

本页由当前台账自动生成，替代此前手写的过期覆盖数字。这里只汇总已登记范围，不把图数量、文件数量、测试通过或源码快照数解释为项目完成率。

## 当前结论

项目仍在模块内部链路与证据补齐阶段。自动化主图外层已逐项复核，但全工程业务解析、独立专题统一索引、完整构建和实际设备运行仍未全部完成。已有图可用于理解和交接其明确限定的范围。

## 当前证据数量

| 口径 | 当前数量 | 边界 |
| --- | ---: | --- |
| 源码项目 / 分组 / C#文件 | 16 / 29 / 1436 | 文件系统基准，排除bin/obj/.git，含Designer |
| 模块部分复核 / 待首次复核 | 29 / 0 | 没有模块因本次统计升级为完整验收 |
| 自动化主图章节 / 步骤 / 关系 | 8 / 89 / 101 | 仅主图，不含全部专题 |
| 主图语义复核登记 | 89 | 登记不代表底层和运行验证 |
| 模块代表关系 / 源码快照 | 552 / 940 | 独立专题不自动累计到此台账 |

部分专题采用全trunk扫描，可能包括bin/obj中的生成源码，因此与本页排除这些目录的文件数不同。两者不能混算；例如就绪标志专题使用全trunk扫描；其文件数保存在该专题证据中。

## 对照原始目标逐项验收

| 目标 | 当前状态 | 证据入口 | 尚未证明的部分 |
| --- | --- | --- | --- |
| 导入源码并界定解析范围 | 基准已建立 | [查看](source-module-inventory.md) | 排除bin/obj/.git；含Designer；不等于MSBuild求值后的编译项 |
| 识别项目、外部依赖与缺失项 | 声明级基准已建立 | [查看](project-dependency-baseline.md) | XML声明不代表实际加载版本；条件和imports未求值，缺失项目仍须解决 |
| 模块职责、框架入口和边界清楚 | 部分完成 | [查看](module-review-status.md) | 全部分组均有登记不等于全部文件和方法已复核 |
| 优先理解软件自动工作的真实步骤 | 主图限定外层已复核，内部继续 | [查看](automation-traceability.md) | 主图步骤是聚合业务步骤，不是整个工程所有执行路径 |
| 模块调用关系与业务链路清楚 | 部分完成 | [查看](module-source-explorer.html) | 代表关系、信号握手和控制流不能合并为全量静态调用图 |
| 触发、顺序、条件、重试与异常可溯源 | 主链及多个专题已复核 | [查看](business-branch-coverage.md) | 还需逐项补齐深层分支、动态分派和外部行为 |
| 输入输出、配置、文件、队列和数据库清楚 | 部分完成 | [查看](async-persistence-ingress-review.md) | 仓库源码/随附DLL静态证据不证明现场写入成功或全部数据源已穷尽 |
| Archify交互图和有用的时序图 | 已有主图及专题交付 | [查看](index.html) | 每张图以自己的交付和浏览器收据为准；本审计不替代图形验收 |
| 工程师能从结论直接回看源代码 | 主台账与已登记专题可追溯 | [查看](source-explorer-handoff.md) | 独立专题尚未全部合并到模块阅读器；入口文件存在不代表全部结论均经人工复核 |
| 已完成、当前进度、未完成项清楚 | 本审计由当前台账自动生成 | [查看](project-plan-status.md) | 历史增量保留原范围；模块原始缺口须结合后续专题复核，不能用文件数推算完成百分比 |
| 源码更新后能自动重建和发现漂移 | 有生成器和回归；语义解析部分完成 | [查看](verification-runbook.md) | 已有脚本不是无人值守、任意源码均可用的全量自动理解工具 |
| 构建与真实运行验证边界清楚 | 完整构建及设备闭环未验收 | [查看](project-dependency-baseline.md) | 原方法替身测试仅证明限定场景；不能计作设备或SDK测试 |
| 形成工程师可接手的完整成果 | 可用于已复核范围交接，整体未完成 | [查看](module-review-status.md) | 所有未复核业务与现场依赖仍保留；不宣称全项目完成 |

## 自动工作主链覆盖

| 章节 | 步骤 | 关系 | 外层复核步骤 | 运行状态 |
| --- | ---: | ---: | ---: | --- |
| [01 · 启动、回零与生产放行](startup-workflow.html) | 12 | 10 | 12 | not-tested |
| [02 · 载具输送与上下料](transport-workflow.html) | 11 | 12 | 11 | not-tested |
| [03 · S1 配方、点胶与分段交接](dispense-workflow.html) | 10 | 12 | 10 | not-tested |
| [04 · 晶圆供料、换料与翻转](wafer-supply-workflow.html) | 12 | 15 | 12 | not-tested |
| [05 · S2 配方调度与载具完成](bonding-workflow.html) | 12 | 15 | 12 | not-tested |
| [06 · 取晶动作与漏晶恢复](pickup-workflow.html) | 10 | 13 | 10 | not-tested |
| [07 · 固晶动作与回带恢复](bond-action-workflow.html) | 10 | 11 | 10 | not-tested |
| [08 · 暂停、重试、停止与线程边界](failure-recovery-workflow.html) | 12 | 13 | 12 | not-tested |

章节顺序用于理解调度和握手，不意味着所有机械动作串行完成。分支、异步、回调及失败恢复按各章源码解释阅读。

## 模块与缺失项的阅读方式

| 分组 | 当前登记状态 | 登记文件 / 分组文件 | 代表关系 | 职责及缺口 |
| --- | --- | ---: | ---: | --- |
| AKRS.Calibration | partial | 7 / 12 | 44 | [源码复核](calibration-tool-module-review.md) |
| Akrs.ChangeJson | partial | 7 / 12 | 8 | [源码复核](change-json-module-review.md) |
| AKRS.Galaxy.SoftKey | partial | 3 / 6 | 7 | [源码复核](authorization-background-source-review.md) |
| AKRS.Galaxy2.AutoFocusing | partial | 1 / 4 | 8 | [源码复核](autofocus-module-review.md) |
| AKRS.Galaxy2.AxisCompensate | partial | 5 / 7 | 4 | [源码复核](axis-compensate-module-review.md) |
| AKRS.Galaxy2.Component.TestDemo | partial | 3 / 6 | 6 | [源码复核](component-demo-module-review.md) |
| AKRS.Galaxy2.CoordinateSystems | partial | 6 / 13 | 6 | [源码复核](coordinate-system-module-review.md) |
| AKRS.Galaxy2.Dispense | partial | 3 / 82 | 4 | [源码复核](dispense-pattern-editor-source-review.md) |
| AKRS.Galaxy2.LogTest | partial | 4 / 6 | 6 | [源码复核](log-test-module-review.md) |
| AKRS.Galaxy2.Machine | partial | 7 / 7 | 6 | [源码复核](machine-framework-module-review.md) |
| AKRS.Galaxy2.MachineSupport | partial | 4 / 4 | 6 | [源码复核](machine-framework-module-review.md) |
| AKRS.Galaxy2.PR | partial | 5 / 87 | 14 | [源码复核](vision-recipe-module-review.md) |
| AKRS.Galaxy2.PR.Test | partial | 3 / 6 | 10 | [源码复核](pr-test-module-review.md) |
| AKRS.Galaxy2.TeachTest | partial | 4 / 17 | 8 | [源码复核](teach-test-module-review.md) |
| AKRS.ZX2200/BondSystem | partial | 26 / 227 | 46 | [源码复核](bond-system-module-review.md) |
| AKRS.ZX2200/CalibSystem | partial | 8 / 65 | 71 | [源码复核](calibration-module-review.md) |
| AKRS.ZX2200/Common.cs | partial | 1 / 1 | 0 | [源码复核](common-types-module-review.md) |
| AKRS.ZX2200/DispenseSystem | partial | 17 / 75 | 31 | [源码复核](dispense-system-module-review.md) |
| AKRS.ZX2200/Experiment | partial | 2 / 68 | 2 | [源码复核](axis-compensate-module-review.md) |
| AKRS.ZX2200/Infrastructure | partial | 13 / 126 | 18 | [源码复核](vision-runtime-module-review.md) |
| AKRS.ZX2200/Localization | partial | 4 / 4 | 9 | [源码复核](localization-module-review.md) |
| AKRS.ZX2200/Main | partial | 14 / 76 | 88 | [源码复核](main-module-review.md) |
| AKRS.ZX2200/Program.cs | partial | 1 / 1 | 10 | [源码复核](application-entry-module-review.md) |
| AKRS.ZX2200/Properties | partial | 3 / 3 | 3 | [源码复核](properties-module-review.md) |
| AKRS.ZX2200/SupportFeature | partial | 8 / 160 | 20 | [源码复核](statistics-data-module-review.md) |
| AKRS.ZX2200/TransportSystem | partial | 24 / 73 | 61 | [源码复核](transport-system-module-review.md) |
| AKRS.ZX2200/TransportUnitSystem | partial | 24 / 104 | 25 | [源码复核](transport-unit-module-review.md) |
| AKRS.ZX2200/WaferSubSystem | partial | 16 / 174 | 23 | [源码复核](wafer-rebuild-module-review.md) |
| InterpolationMovementTest | partial | 5 / 10 | 8 | [源码复核](interpolation-test-module-review.md) |

模块原报告中的缺口可能已被后续独立专题部分推进；请同时查看[项目最新增量](project-plan-status.md)。本次不靠关键词自动关闭缺口。机器可读审计保留原始登记缺口，便于后续逐条合并。

## 后续推进顺序

1. 继续补齐生产主链的内部调用与失败恢复；每个结论先取源码证据，再更新图。
2. 将独立专题的已验证结论回链到统一模块索引，并逐条核销已被后续证据解决的旧缺口。
3. 对尚未解析的业务路径做源码分析；外部实现不可得时明确保留边界，不填造行为。
4. 完成构建条件、真实配置与SDK核对；隔离测试和设备验收分开登记。
5. 做工程师交接复核：从入口定位模块、步骤、源码和未完成项。

[整合入口](index.html) · [机器可读审计](source-coverage-audit.json) · [计划清单](project-plan-status.md) · [模块源码阅读器](module-source-explorer.html)

更新命令：`node scripts/build-source-coverage-audit.cjs`；校验命令：`node scripts/build-source-coverage-audit.cjs --check`。输入文件哈希随审计保存；生成只更新覆盖描述，不自动认定语义已经复核。
