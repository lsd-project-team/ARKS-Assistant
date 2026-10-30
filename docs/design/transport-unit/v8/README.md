# Transport Unit设计文档 第8版

2026年10月26日。按“来料、点胶、交接、固晶、下料”重写。先看设备动作，再看软件怎样记住同一块产品和A点；共31页，37幅独立插图，封面复用路线图。

- [阅读PDF](TransportUnit设计文档.pdf)
- [可编辑Word](TransportUnit设计文档.docx)
- [Markdown正文](TransportUnit设计文档.md)
- [阅读索引与旧版章节对照](阅读索引.md)
- [生成与维护](../../authoring/plain-language/README.md)

每页解释一个具体问题，包括产品层级、坐标和90度旋转、工位偏移、测高、点胶记录、交接刷新、分段、Mapping、清空、异常与保存。图片保留PNG与SVG，文字和数字同正文对应。

沿用7.2版源码核查，78个依据文件哈希重验未变。详细接口及其余边界仍可由阅读索引查上版，未把现有实现改写成理想行为。source-continuity.json记录范围，verification.json记录正文和排版核对，image-resolution.json记录每次图像放置的原始分辨率。

本次没有运行设备或整套C#业务，数字为明确给定条件下的说明例。全页视觉校样记录另见visual-review.json，代理校样不等于独立真人试读或用户签收。

旧版保留：[7.2版](../v7.2/README.md)。[两册入口](../../README.md)。
