# 原始 S2 点胶气缸前置 IL 边界

本轮只读检查 `trunk/AKRS.ZX2200/bin/Debug/AKRS.ZX2200.exe`，程序集 SHA-256 为 `ea7c14767e29420d54f00c2070bb66f833980147156123a77a7925946b0f4ad8`。未启动动作节点、点胶硬件、UI、数据库、VM、SDK 或设备。

`BondTask.CloseDispenseCylinder` 的原始 IL 已记录并通过绑定校验：读取当前动作的 `IsCloseCylinder`；条件不满足时调用 `S2DispenseController.CloseDispenseHeightMeasurementCylinder()`，满足时直接返回。该证据确认动作执行前的点胶气缸关闭门，不证明真实气缸运动、控制器返回值、任务异常或设备安全。

机器结果见 [original-s2-close-cylinder-il.json](original-s2-close-cylinder-il.json)，校验入口为 `scripts/verify-original-s2-close-cylinder-il.cjs`。
