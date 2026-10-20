# 纠偏过程设计文档

第2.0版，2026年10月20日。面向研发评审与设备调试两类读者。

- [纠偏过程设计文档.pdf](纠偏过程设计文档.pdf)：24页阅读稿，13幅图、6张表，含目录跳转及章节书签。
- [纠偏过程设计文档.docx](纠偏过程设计文档.docx)：可编辑Word，保留原生目录、公式、引用和图表页码。
- Markdown及figures目录用于维护；工程图同时保存SVG和PNG。
- source-guide.md、source-baseline.json、claim-map.json保存源码入口及主要结论依据。
- illustration-provenance.json保存生图提示词、最终图片绝对路径及哈希。
- verification.json、final-qa.json、editorial-review.md、acceptance-audit.md保存本轮检查依据；arithmetic-verification.json保存独立复算结果。

第2、3、4、5章先解释物理含义，再定义变量、条件和实现边界。3.3节用少量加粗标识算法分支。图5-1改为生图连续场景，图5-2改为精确向量及偏心局部放大图。保留四点角度、两点Atan、S1/S2距离检查、人工OK、温漂返回和两个重试标签的实际行为。

两册入口见[设计文档总览](../../README.md)。源码保持只读；算例不是实机验证结果。
