# Transport Unit源码核查发现

源码范围严格限定为trunk/AKRS.ZX2200。

- Mapping按当前配方创建新树，恢复部分结果后替换区段引用，不能表述为恢复旧运行对象。
- IsMirror在构造时复制，Refresh没有重赋；刷新与重建的配置派生字段寿命不同。
- MapBelt的输送配置分支对已有TU的Refresh行为不同；尾段有料状态不保证TU非空。
- 交接报警Ignore仍能继续引用交接、Refresh和成功出口；异常没有统一回滚。
- 相对固晶重排、分段增减、S1/S2 IsProduct条件与DryCycle对象连续性分别保留。

关键结论、方法和复核区间见claim-map.json及source-analysis.json；已发现入口逐项归属见entry-coverage.md。文本发现与关键方法语义核查分别记录，不以文件数量声称全项目理解或形式化可达性证明。
