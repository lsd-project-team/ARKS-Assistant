# 纠偏过程设计文档 第3.2版

2026年10月21日。面向软件研发与技术评审、设备调试与应用工程两类读者。业务源码检索、读取和追踪严格限定trunk/AKRS.ZX2200，原件只读。

- [阅读PDF](纠偏过程设计文档.pdf)：46页，27幅图、20张表。
- [编辑Word](纠偏过程设计文档.docx)：与PDF同步，保留可编辑正文、原生目录、21组公式和引用。
- [维护正文](纠偏过程设计文档.md)及figures：正文与现用PNG/SVG；[生成与验证源](../../authoring/correction-v3.2/README.md)。
- [源码核查发现](source-findings.md)、[候选入口归属](entry-coverage.md)、[文档验收自检](acceptance-audit.md)。

本次新增第9章设备轴二维补偿、第10章手动两点角度示教、第11章TU区域补偿表自动生成及人工维护。进一步补入主界面可打开的人工导入、3/5点均值平滑、编辑、保存及清空路径。第12章将标定输入和诊断路径分别归属；前八章生产流程保留。

核查资料：

- source-baseline.json、source-analysis.json、claim-map.json、source-guide.md：80个依据文件的哈希与方法锚点、实际已读区段及55条结论，其中25条为本次新增核查。
- scope-discovery.json、entry-coverage.json：1158个C#文件索引、103个候选逐项归属。索引、编译项和业务阅读分别记录，不声称全目录通读。
- calculator-csharp.json、calculator-reference.json、new-arithmetic-verification.json：18项原始纯数值类C#检查与14项独立Python图示和边界核对。
- arithmetic-examples.json、arithmetic-verification.json：既有9组几何公式重新复算。
- verification.json、text-sync.json：67项目录与书签、47项图表索引、127段正文一致性、字体嵌入及至少300dpi图像检查。
- final-qa.json、reader-walkthrough.json、acceptance-gates.json：46页最终校样、两类读者13个问题及逐项要求检查。
- source-immutability.json、release-manifest.json、illustration-provenance.json：源码只读、交付哈希、概念生图来源及新增精确工程图记录。

自动采集窗口的实现和编译项存在，本目录未发现其他代码直接构造或打开该窗口；文档按辅助采集实现说明，没有声称已接入每轮生产。真实入口、外部反射或其他目录调用不能由本次范围确认。

本轮未运行设备或整套C#业务流程；只编译并执行无设备依赖的CompensateCalculator纯数值类。驱动SDK、外部坐标库内部不展开。代理技术及版式自检不替代设备验证、独立真人试读或用户签收。上述制作和核查资料不进入正式PDF/Word正文。

旧版见[v3.1](../v3.1/README.md)，[两册总览](../../README.md)。
