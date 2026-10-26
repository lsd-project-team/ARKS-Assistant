# ZX2200设计文档

当前为2026年10月26日改写的图解版本。按设备实际流程讲，每页一个问题，图旁直接解释设备动作、位置和记录怎样改变。

| 分册 | 先看什么 | PDF | 可编辑Word |
|---|---|---|---|
| Transport Unit 第8版 | 跟着同一块产品和A点，经过来料、点胶、交接、固晶和下料 | [阅读PDF](transport-unit/v8/TransportUnit设计文档.pdf) | [编辑Word](transport-unit/v8/TransportUnit设计文档.docx) |
| 纠偏过程 第4版 | 跟着芯片经过供料定位、取片、拍照纠偏和贴装，再解释各种补偿 | [阅读PDF](correction-process/v4/纠偏过程设计文档.pdf) | [编辑Word](correction-process/v4/纠偏过程设计文档.docx) |

TU册31页、37幅独立插图；纠偏册37页、45幅独立插图。封面另复用本册路线图。连续位置例子、前后状态、拍照次数和实际动作放在对应页讲解，术语在使用时解释。

需要查代码时，再看[TU阅读索引](transport-unit/v8/阅读索引.md)和[纠偏阅读索引](correction-process/v4/阅读索引.md)。两册均保留Markdown正文、SVG/PNG图源和[共同生成源](authoring/plain-language/README.md)。

本次重写沿用既有源码核查结论，重验78个与80个依据文件哈希均未变化；源码范围仍为`trunk/AKRS.ZX2200`，原件只读。说明算例独立复算，不作为本机参数或实机验证结果。正文、图像分辨率、目录、字体和页码检查见各册verification.json；本次没有运行设备或整套C#业务。

旧版保留：[TU 7.2](transport-unit/v7.2/README.md)、[纠偏3.2](correction-process/v3.2/README.md)。上轮验收见[历史修订记录](publication-acceptance.md)。
