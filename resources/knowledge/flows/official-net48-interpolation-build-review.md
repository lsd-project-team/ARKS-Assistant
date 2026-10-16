# InterpolationMovementTest 隔离构建失败记录

`InterpolationMovementTest.csproj` 的隔离 MSBuild 试跑已保留为失败证据，退出码为 `1`。该项目展开到 ZX2200、Dispense 和 PR 项目引用后，在两个 `CompileLicxFiles` 目标处因找不到 `LC.exe` 报 `MSB3086`；同时 PR 引用缺少 `AKRS.Galaxy2.HardwareEditor`、`MWArray`、`System.Threading.Tasks.Extensions` 以及三个 DevExpress 对话框程序集（`MSB3245`）。

日志中没有 `CS1617`。完整日志哈希见 [official-net48-interpolation-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-interpolation-build-audit.json)，输出目录保留在 `.archify-work/official-net48-build-toolchain/interpolation-build-with-vendor`。本轮没有伪造 `LC.exe`、补造缺失程序集或修改生产工程。
