# Transport Unit设计分册

第3版修订1，2026年10月20日。面向软件研发、技术评审及设备调试人员的修订稿，供内容验收。

- `TransportUnit设计文档.pdf`：阅读与打印稿，带目录跳转和书签。
- `TransportUnit设计文档.docx`：可编辑稿，保留原生目录、标题层级、公式及引用。
- `TransportUnit设计文档.md`、`figures/`：正文维护源和插图；工程图同时提供SVG。
- `source-baseline.json`、`claim-map.json`：源码文件基线与主要结论定位。
- `editorial-review.md`、`verification.json`：编校经过及实际检查范围。
- `acceptance-audit.md`：原要求逐项对照及尚待完成的验收。
- `illustration-provenance.json`、`image-resolution.json`：生成插图提示词与PDF插图分辨率。

正文以同一产品实例解释结构、坐标和跨工位记录。第3.6节集中列出关键字段读写规则，第6章说明正常生产主链，第7、8章说明接口与边界，第9章可用于复算和核对理解。附录B提供术语和带页码图表索引。源码保持只读；文中数据不是设备实测，静态复核不替代实机试验。

本修订更正了上一版的查询语义：TU查询方法只按Index，动作控制器才按WorkIndex解析。新增字段表、接口输入输出、区段状态表、身份标记有效期和S2缓存未命中行为说明。

本轮只修订Transport Unit分册。纠偏过程分册按约定等待本册确认。
