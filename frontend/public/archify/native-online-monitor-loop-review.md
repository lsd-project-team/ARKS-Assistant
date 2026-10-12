# 原始在线监控循环与消费者启动核验

隔离 CLR 4.0.30319.42000 宿主对原始 `Machine.StartBackGroundThread` 做了两次独立重放，共 15 项检查通过；16 个源/资源程序集从冻结的 bound 路径加载且位置匹配。生产 C#、工程和运行时程序集未修改。

## 实际执行

宿主把 `MachineWorkMode` 设为原始 `NormalWork`，机器保持 `Stop`，硬件仓库为空，安全门、激光干涉尺和输送加热配置均关闭，自动登出关闭，登录用户为空。调用原始 `StartBackGroundThread` 后观察到：

- 原始“后台监控线程”创建为后台线程并进入运行状态。
- 重复调用 `StartBackGroundThread` 时复用仍存活的原始线程，不创建第二个监控线程。\n- 监控循环通过公开 `RuntimeProvider.ThreadFlag=false` 退出，线程在 5 秒内 Join 完成；重新置为 `true` 后再次调用会创建新的原始后台线程，第二次置为 `false` 后也能退出。
- 循环实际到达原始统计保存消费者和图像保存消费者启动，两者均为后台线程。
- 机器仍为停止状态，硬件仓库仍为空。
- `DBService` Lazy 未创建，没有 SQL 写入、硬件动作、UI 调度或生产任务。

## 证据限制

本轮验证的是在线 `NormalWork` 下硬件配置关闭、空仓库时的完整监控入口和消费者启动边界。没有构造真实硬件、没有执行 `Machine.Start`、没有连接 SQL、没有触发报警对话框，也没有验收设备成功或生产任务循环。配置打开但硬件缺失的异常边界另见 [在线监控边界报告](native-online-monitor-boundary-review.md)。

测试输出见 [进度](native-online-monitor-loop-progress.json)、[审计](native-online-monitor-loop-audit.json)；独立核验命令为 `node .archify-work/verify-native-online-monitor-loop.cjs`。

