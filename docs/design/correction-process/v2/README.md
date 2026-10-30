# 纠偏过程设计文档

第2.1版，2026年10月21日。面向研发评审与设备调试两类读者。

- [阅读PDF](纠偏过程设计文档.pdf)：24页，13幅图、6张表，含目录跳转及章节书签。
- [编辑Word](纠偏过程设计文档.docx)：保留原生目录、公式、引用和图表页码。
- Markdown及figures目录用于维护；工程图同时保存SVG和PNG。
- source-guide.md、source-baseline.json、source-analysis.json及claim-map.json保存源码依据。
- illustration-provenance.json保存生图提示词、所用图片路径及哈希。
- verification.json、final-qa.json、editorial-review.md、acceptance-audit.md保存检查依据；arithmetic-verification.json保存独立复算结果。

本次校订补齐TU、PR、IPT及S1/S2术语，说明吸嘴偏心接口中的AlignAngle约定，并把硬角度补偿记为h，避免与特征中心向量c混用。公式6-1同时明确a_off的含义。图源与章节结构沿用第2版，旧稿可从Git历史追溯。

最终24页中6页直接查看，18页全页像素与上一轮已核对校样一致；源码基线、目录、图表、原生公式、字体与分辨率检查通过，9个独立算例复算通过。源码保持只读；未执行设备试验或独立读者验收。

两册入口见[设计文档总览](../../README.md)。
