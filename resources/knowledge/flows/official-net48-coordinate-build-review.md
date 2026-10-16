# AKRS.Galaxy2.CoordinateSystems 隔离构建复核

`AKRS.Galaxy2.CoordinateSystems.csproj` 已在隔离源码镜像中使用官方 Roslyn 4.14.0 和 .NET Framework 4.8 引用程序集构建成功。MSBuild 退出码为 `0`，日志报告 `0 个错误`，没有 `CS1617`；程序集 SHA-256 为 `E6C1D03F25186A32E25E70EC9FB797A8F9420095153D351478A73D88CC7D615C`。输入、输出和日志哈希见 [official-net48-coordinate-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-coordinate-build-audit.json)。

日志有三个 `MSB3270` 警告，均为 MSIL 项目引用 AMD64 的 `AKRS.Galaxy2.Log`、`AKRS.Galaxy2.ModulePublic` 和 `AKRS.Galaxy2.UserManager`。本次没有修改生产源码；结果不覆盖坐标运行时、厂商 SDK ABI、UI、SQL、打包、织入或完整解决方案验收。
