# 晶圆变更 Retry 当前复验

日期：2026-10-06。状态：current-wafer-change-retry-verified。

按当前源码重新执行 ChangeTabletAuto 的 16 项隔离检查：有料库、静态适配器和无料库路径的 false 重试、Stop 入口、异常逸出、对话框 Abort，以及缺片取消/重新选层/传感器重置分支均通过。

该项只验证换片控制流和受控替身调用顺序；真实运动、窗口、设备 SDK、完整 worker、停止安全和生产现场仍未验收。
