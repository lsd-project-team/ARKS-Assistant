# 晶圆相机间隙当前复验

日期：2026-10-06。状态：current-wafer-camera-clearance-verified。

按当前源码重新执行晶圆相机间隙与 Bond 邻近度链的 174 项隔离检查，覆盖配置选择、精确边界、非有限值、getter 异常、严格容差、消费者模式以及 Stop/Pause 门。

该项使用运动、视觉、坐标、存储和机器状态替身，不代表相机 SDK、标定、轴到位、到达信号、Machine.Stop、UI、持久化或设备验收。
