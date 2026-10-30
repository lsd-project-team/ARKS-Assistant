# 原始 S2 任务入口 IL 边界

本轮只读检查 `trunk/AKRS.ZX2200/bin/Debug/AKRS.ZX2200.exe`，程序集 SHA-256 为 `ea7c14767e29420d54f00c2070bb66f833980147156123a77a7925946b0f4ad8`。未启动任务、UI、信号、输送、数据库、VM、SDK 或设备。

`BondTask.Start` 的原始 IL 已记录并通过绑定校验：仅在 `BondWorkTask` 为空或状态不是 `Running` 时调用 `Task.Factory.StartNew`，使用 `CancellationToken.None`、`TaskCreationOptions.LongRunning` 和 `TaskScheduler.Default`，随后返回 `true`。该证据只确认入口调度结构，不证明线程真正运行、异常监督、停止回收、并发竞态或生产任务成功。

机器结果见 [original-s2-start-il.json](original-s2-start-il.json)，校验入口为 `scripts/verify-original-s2-start-il.cjs`。
