# 晶圆消费者暂停当前复验

日期：2026-10-06。状态：current-wafer-consumer-pause-verified。

按当前源码重新执行晶圆消费者 Dowork 的 212 项隔离检查，覆盖入口与等待内 Pause/Stop、信号消费、四类载具、换片/视觉 Retry、异常传播以及取料信号发布和重置边界。

该项仍使用动作、视觉、运动、对话框、数据库和 Excel 替身，不代表原 Stop 集成、驱动、UI、持久化或设备验收。
