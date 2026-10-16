# 原始 S2 完成后送走载具 IL 边界

本轮只读检查 `trunk/AKRS.ZX2200/bin/Debug/AKRS.ZX2200.exe`，程序集 SHA-256 为 `ea7c14767e29420d54f00c2070bb66f833980147156123a77a7925946b0f4ad8`。未启动生产任务、输送、UI、数据库、VM、SDK 或设备。

`BondTask.SendAway` 的原始 IL 已记录并通过绑定校验：配置输送且机器未停止时设置 `AllowBondTransferToWaitingUnloadSignal`；机器停止时抑制该信号；未配置输送时检查停止状态、按 `AutoSaveMapping` 保存 Mapping，并清理当前 `TransportUnit`。该证据确认调用和分支顺序，不证明真实传送、Mapping 持久化、UI、任务完成或设备安全。

机器结果见 [original-s2-send-away-il.json](original-s2-send-away-il.json)，校验入口为 `scripts/verify-original-s2-send-away-il.cjs`。
