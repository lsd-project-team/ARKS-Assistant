# Task 状态谓词与 Dispose 语义隔离复现

复核日期：2026-10-06。状态：`isolated-runtime-confirmed`。运行证据见 [task-lifecycle-probe-audit.json](task-lifecycle-probe-audit.json)。夹具使用官方 .NET Framework 4.8 目标编译器，仅创建托管 Task，不引用生产程序集。

## 复现结果

夹具创建了已完成、异常、取消和等待中的四个 Task，并使用与生产 `IsAllowTaskClosed` 相同的谓词：只有 `task != null && task.Status == TaskStatus.Running` 才阻挡。结果为：

| Task 状态 | 生产形状谓词结果 |
|---|---:|
| `RanToCompletion` | `false` |
| `Faulted` | `false` |
| `Canceled` | `false` |
| `Running` | `true` |

夹具还在 Task 仍为 Running 时调用 `Dispose`，观察到 .NET 4.8 抛出 `InvalidOperationException`；释放等待闸门并让 Task 完成后，`Dispose` 才成功。`Dispose` 没有取消或等待正在执行的 Task。

## 与源码审计的关系

这组运行证据加强了 [machine-task-lifecycle-review.md](machine-task-lifecycle-review.md) 中两个边界：`IsAllowTaskClosed` 的 Running-only 判断确实会把 Faulted/Canceled 视为不阻挡，而直接 Dispose 不能替代取消或 Join。它仍然没有执行生产的 `Machine`、Worker、Stop、Abort 或 EmergencyStop，所以不能把夹具结果升级为生产集成验收。

## 可复跑文件

- [TaskLifecycleProbe.cs](../../.archify-work/task-lifecycle-probe/TaskLifecycleProbe.cs)
- [run-task-lifecycle-probe.ps1](../../.archify-work/run-task-lifecycle-probe.ps1)
- [register-task-lifecycle-probe.cjs](../../.archify-work/register-task-lifecycle-probe.cjs)
