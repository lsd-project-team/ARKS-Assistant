# 纠偏过程设计文档 第3.1版

2026年10月21日。适用读者：软件研发/技术评审与设备调试/应用工程师。

- [纠偏过程设计文档.pdf](纠偏过程设计文档.pdf)：34页，21幅图、14张表。
- [纠偏过程设计文档.docx](纠偏过程设计文档.docx)：可编辑正文、原生目录、公式及引用，与PDF使用同一正文和排版源。
- [纠偏过程设计文档.md](纠偏过程设计文档.md)及figures：维护正文与所用SVG/PNG。
- [源码核查发现](source-findings.md)、[入口逐项归属](entry-coverage.md)、[本册验收记录](acceptance-audit.md)。
- source-baseline.json、source-analysis.json、claim-map.json、source-guide.md：源码哈希、实际已读方法范围、关键结论及详细定位。
- scope-syntax-audit.json、coverage-candidates.json：全目录语法扫描、Compile、构造和动作注册的交叉发现；扫描与业务深读分别记录。
- arithmetic-verification.json、revision-verification.json、new-arithmetic-verification.json、arithmetic-examples.json：公式、边界及八入口纯条件组合核对。
- final-qa.json、verification.json、reader-walkthrough.json、acceptance-gates.json：最终全页直接查看、结构验证、角色阅读走查及逐项要求闭环。
- illustration-provenance.json：概念生图提示词、来源和本册最终插图哈希。

正式PDF/Word已清除制作说明页，源码日期/哈希、核查方法、是否执行设备、绘图工具及文件用途均留在配套资料；保留必要的设计条件、单位、参考系和图注。

本轮完成源码静态核查与独立数值计算，未运行C#业务或设备；未开展独立真人试读，代理角色走查不等于用户签收。目录外仅说明接口与前提，不展开内部实现。旧版见[v3](../v3/README.md)，[两册总览](../../README.md)，[维护模板](../../authoring/v7.1/README.md)。
