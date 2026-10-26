# ZX2200设计文档

当前为2026年10月26日完成的连续图解版。两册共用产品P1、基板1／基岛2／A点和芯片C1：先走完一轮正常流程，再按需查可选配置、人工操作和异常。

| 分册 | 先看什么 | PDF | 可编辑Word |
|---|---|---|---|
| Transport Unit 第8.1版 | 从P1来料到下料，跟住同一个A点的位置与加工进度 | [阅读PDF](transport-unit/v8.1/TransportUnit设计文档.pdf) | [编辑Word](transport-unit/v8.1/TransportUnit设计文档.docx) |
| 纠偏过程 第4.1版 | 接着同一个A点，看C1怎样找到、取起、拍照并贴准 | [阅读PDF](correction-process/v4.1/纠偏过程设计文档.pdf) | [编辑Word](correction-process/v4.1/纠偏过程设计文档.docx) |

TU册29页、26幅独立插图；纠偏册36页、34幅独立插图，封面各复用一幅路线图。第一次阅读可先看TU第3至14页，再看纠偏第3至13页，完整走完P1和C1的主流程。每页有当前阶段和下一页承接，图旁直接解释动作、位置和状态变化。

需要查细节时，再看[TU阅读索引](transport-unit/v8.1/阅读索引.md)、[纠偏阅读索引](correction-process/v4.1/阅读索引.md)和各册的计算与代码索引。正文数字以便于阅读的精度显示，计算继续使用未舍入值。两册保留Markdown正文、SVG/PNG图源和[共同生成源](authoring/flow-guide/README.md)。

本次重写沿用既有源码核查结论，重验78个与80个依据文件哈希均未变化；源码范围仍为`trunk/AKRS.ZX2200`，原件只读。说明算例独立复算，不作为本机参数或实机验证结果。正文、图像分辨率、目录、字体和页码检查见各册verification.json；本次没有运行设备或整套C#业务。

旧版保留：[TU 8](transport-unit/v8/README.md)、[纠偏4](correction-process/v4/README.md)、[TU 7.2技术版](transport-unit/v7.2/README.md)、[纠偏3.2技术版](correction-process/v3.2/README.md)。更早验收见[历史修订记录](publication-acceptance.md)。
