# 原始在线监控故障线程身份与独立重放

两个独立 CLR 宿主均执行未改写的 `Machine.StartBackGroundThread`。采用原始 `NormalWork/Working` 状态、安全门配置打开、空硬件仓库，故障前每个进程完成四项守卫检查。图像消费者、统计消费者和数据库 Lazy 均未创建。

原始 `AppDomain.UnhandledException` 回调只记录证据，不拦截或主动退出。两次回执字节相同，并确认：

- 当前线程与 `Machine.BackGroundThreadThread` 的对象引用相同，名称为“后台监控线程”，且为后台线程。
- `System.NullReferenceException` 的完整栈依次包含 `IsSafeDoorClosed`、安全门 getter、`StartCheckSafeDoorTask` 和原始监控 lambda。
- `IsTerminating=true`；状态仍为 Working，公开 ThreadFlag 仍为 true，硬件仓库为空。
- 图像与统计消费者均不存在，数据库 Lazy 未创建，统计队列为空。
- 16 个源/资源程序集的实际位置与运行时映射一致；审计绑定它们及 SDK 文件的 SHA256。

宿主调用监控入口后无限等待，父记录器观察到两个子进程自然终止；未执行强制终止或主动 Environment.Exit。两个子进程均返回非零码 3221225477（0xC0000005）。这是观察到的原生进程结果，不能将它当作 NullReferenceException 的固定退出码。CLR 标准错误的 Exception.ToString 失败提示及该原生退出码的底层原因尚未定位；托管异常类型、栈和线程身份以终止回执为准。

此前单次运行记录保留在 `native-online-monitor-fault`，本轮使用新目录 `native-online-monitor-fault-replay`，没有覆写旧证据。新宿主避免了旧宿主 500ms 后返回并格式化输出与终止回调并发的观测问题。仍然没有实际门控传感器、报警模态 UI、生产业务循环、SQL 持久化或现场设备验收。

见[审计](native-online-monitor-fault-replay-audit.json)和[进度](native-online-monitor-fault-replay-progress.json)。独立核验：`node .archify-work/verify-online-monitor-fault-replay.cjs`。本证据与正式 1328 项检查独立，整体任务仍未完成。
