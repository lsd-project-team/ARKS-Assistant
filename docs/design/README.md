# ZX2200设计文档

两册按设备动作说明：板子怎样点胶、芯片怎样取起并贴到A点。每页用大图和短句讲一件事。

| 分册 | 先看什么 | PDF | 可编辑Word |
|---|---|---|---|
| Transport Unit 第8.2版 | 板子走到哪里，哪些点做过，软件怎样记住 | [阅读PDF](transport-unit/v8.2/TransportUnit设计文档.pdf) | [编辑Word](transport-unit/v8.2/TransportUnit设计文档.docx) |
| 纠偏过程 第4.2版 | 找到芯片、取起来、拍照、对准A点贴下 | [阅读PDF](correction-process/v4.2/纠偏过程设计文档.pdf) | [编辑Word](correction-process/v4.2/纠偏过程设计文档.docx) |

TU册15页，纠偏册16页。正文每页约百字，用蓝圈表示同一个A点。已移除分部名称、阶段导航、重复过渡句和正文算式。

坐标、公式、接口和配置细节由[TU配套资料](transport-unit/v8.2/配套资料.md)与[纠偏配套资料](correction-process/v4.2/配套资料.md)查阅，旧版完整内容继续保留。两册有Markdown正文、SVG/PNG图源和[共同生成源](authoring/simple-guide/README.md)。

本次重写沿用既有源码核查结论，重验78个与80个依据文件哈希均未变化；源码范围仍为`trunk/AKRS.ZX2200`，原件只读。说明算例独立复算，不作为本机参数或实机验证结果。正文、图像分辨率、目录、字体和页码检查见各册verification.json；本次没有运行设备或整套C#业务。

旧版保留：[TU 8.1](transport-unit/v8.1/README.md)、[纠偏4.1](correction-process/v4.1/README.md)、[TU 7.2技术版](transport-unit/v7.2/README.md)、[纠偏3.2技术版](correction-process/v3.2/README.md)。更早验收见[历史修订记录](publication-acceptance.md)。
