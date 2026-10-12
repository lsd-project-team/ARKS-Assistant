# AKRS.Galaxy2.Machine 隔离构建复核

`AKRS.Galaxy2.Machine.csproj` 已在隔离源码镜像中使用官方 Roslyn 4.14.0 和 .NET Framework 4.8 引用程序集构建成功。MSBuild 退出码为 `0`，日志报告 `0 个错误`，没有 `CS1617`；程序集 SHA-256 为 `9B7CCE3DF3ADC52521EB97E42C4A0090DD49E5D248F1289EBD432A51AF72F5B0`。完整哈希见 [official-net48-machine-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-machine-build-audit.json)。

日志只有一个 `MSB3270`：MSIL 项目引用 AMD64 的 `AKRS.Galaxy2.Drive`。构建未修改生产源码；结果不覆盖机器运行时、硬件、UI、SQL、打包、织入或完整解决方案验收。
