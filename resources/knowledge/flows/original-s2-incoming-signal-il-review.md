# 原始 S2 来料信号 IL 边界

本轮只读检查 `trunk/AKRS.ZX2200/bin/Debug/AKRS.ZX2200.exe`，程序集 SHA-256 为 `ea7c14767e29420d54f00c2070bb66f833980147156123a77a7925946b0f4ad8`。未启动生产任务、UI、输送、数据库、VM、SDK 或设备。

`BondTask.GetIncomingSignal` 的原始 IL 已记录并通过绑定校验：包含补偿工作直接返回、已配置输送时等待 `TransferToBondFinishedSignal.Wait()`、未配置输送时弹出“未发现载具”提示并按 Yes/No 继续映射或调用 `Machine.Stop()` 的调用与分支边界。该证据只确认原始程序集的静态调用顺序，不证明信号到达、对话框交互、映射成功、任务完成或设备安全。

机器结果见 [original-s2-incoming-signal-il.json](original-s2-incoming-signal-il.json)，校验入口为 `scripts/verify-original-s2-incoming-signal-il.cjs`。
