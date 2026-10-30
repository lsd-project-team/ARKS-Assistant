# 纠偏过程设计文档

第3版，2026年10月21日。面向研发评审与设备调试两类读者。

- [纠偏过程设计文档.pdf](纠偏过程设计文档.pdf)：30页，18幅图、9张表。
- [纠偏过程设计文档.docx](纠偏过程设计文档.docx)：正文、原生目录、公式及引用可编辑，与PDF来自同一排版源。
- [纠偏过程设计文档.md](纠偏过程设计文档.md)及figures：正文与所用图源。
- [源码发现](source-findings.md)、[入口归属](entry-coverage.md)：本轮新增与修正的设计结论。
- source-baseline.json、source-analysis.json、claim-map.json、source-guide.md：限定目录源码哈希、关键方法区间、结论和详细定位。
- arithmetic-verification.json、new-arithmetic-verification.json、arithmetic-examples.json：独立算例与边界计算。
- verification.json、final-qa.json：[本册验收记录](acceptance-audit.md)，最终全部页面直接查看。
- illustration-provenance.json：生图精确提示词、工具、保存位置与图像哈希。

正式PDF和Word已去除独立制作说明页，源码日期/哈希、核查方法、工具与交付用途移至上述配套记录。正式文档保留必要的适用范围、公式条件、单位、参考系和图注。

本轮为源码静态核查、独立数值计算和代理编校，没有运行设备或C#业务流程，没有把算例用作设备精度证据。目录外依赖只按接口及前提说明。旧版保留；两册入口见[总览](../../README.md)。生成模板见[维护说明](../../authoring/v7/README.md)。
