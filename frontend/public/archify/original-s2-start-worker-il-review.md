# 原始 S2 任务工作线程 IL 边界

本轮只读检查 `trunk/AKRS.ZX2200/bin/Debug/AKRS.ZX2200.exe`，程序集 SHA-256 为 `ea7c14767e29420d54f00c2070bb66f833980147156123a77a7925946b0f4ad8`。未启动任务、UI、信号、输送、数据库、VM、SDK 或设备。

`BondTask.<Start>b__20_0` 的原始 IL 已记录并通过绑定校验：工作线程先调用 `CommonUtil.SetCurrentThreadName("固晶工作线程")`，随后调用当前对象的 `DoWork()`，没有额外分支。该证据确认 `Start` 创建的委托目标，不证明线程调度成功、异常监督、停止回收或生产任务完成。

机器结果见 [original-s2-start-worker-il.json](original-s2-start-worker-il.json)，校验入口为 `scripts/verify-original-s2-start-worker-il.cjs`。
