# AKRS.Galaxy2.RealtimeCurve.TestDemo 隔离构建失败记录

`AKRS.Galaxy2.RealtimeCurve.TestDemo.csproj` 的隔离 MSBuild 试跑已保留为失败证据，退出码为 `1`。项目在 `ResolveAssemblyReferences` 阶段报告 14 组未解析的 DevExpress 图表、打印、编辑器及支持程序集，随后在 `CompileLicxFiles` 阶段因找不到 `LC.exe` 报 `MSB3086`。

日志中没有 `CS1617`。完整日志哈希见 [official-net48-realtimecurve-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-realtimecurve-build-audit.json)，输出目录保留在 `.archify-work/official-net48-build-toolchain/realtimecurve-build`。本轮没有伪造 `LC.exe`、补造缺失程序集或修改生产工程。
