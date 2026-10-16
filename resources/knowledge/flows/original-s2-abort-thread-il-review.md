# 原始 S2 任务关闭入口 IL 边界

本轮只读检查 `trunk/AKRS.ZX2200/bin/Debug/AKRS.ZX2200.exe`，程序集 SHA-256 为 `ea7c14767e29420d54f00c2070bb66f833980147156123a77a7925946b0f4ad8`。未启动任务、停止入口、UI、信号、输送、数据库、VM、SDK 或设备。

`BondTask.AbortThread` 的原始 IL 只有 `nop` 和 `ret` 两条指令，没有调用、字段写入或分支。该入口本身不会取消、Dispose 或改变 `BondWorkTask`，因此不能把调用它当作 Bond 线程已停止。机器结果见 [original-s2-abort-thread-il.json](original-s2-abort-thread-il.json)，校验入口为 `scripts/verify-original-s2-abort-thread-il.cjs`。
