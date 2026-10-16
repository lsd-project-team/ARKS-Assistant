# AKRS.Galaxy2.MachineSupport 隔离构建记录

`AKRS.Galaxy2.MachineSupport.csproj` 已使用官方 Roslyn/.NET 4.8 引用程序集在隔离源码镜像中独立构建成功，MSBuild 退出码为 `0`，日志显示 3 个架构警告、0 个错误。输出包含 `AKRS.Galaxy2.MachineSupport.dll` 及其 PDB，程序集 SHA-256 为 `904D53A7BC087E65EFB49E68101B4C801E5CF1EF832CE302D5741B82219B3BE0`。

完整输出清单和日志哈希见 [official-net48-machinesupport-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-machinesupport-build-audit.json)，输出目录保留在 `.archify-work/official-net48-build-toolchain/machinesupport-build`。该结果只覆盖隔离编译，不代表硬件、运行时、SQL、UI、打包或完整解决方案验收。
