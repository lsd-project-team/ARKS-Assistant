# 轴补偿数值当前复验

日期：2026-10-06。状态：current-axis-numeric-verified。

按当前源码重新执行五个轴补偿类和 MathNet 拟合链的 37 项隔离检查，覆盖补偿门、区间边界、NaN/Infinity 传播、多项式、分段行为、最小二乘拟合、重复替换及圆拟合退化。

该项使用惰性 Singleton/PathConfig 和数值输入替身，不代表磁盘保存、UI、生产启动、.NET Framework 构建、物理运动或设备验收。
