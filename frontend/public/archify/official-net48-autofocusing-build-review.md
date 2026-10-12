# AKRS.Galaxy2.AutoFocusing 隔离构建复核

`AKRS.Galaxy2.AutoFocusing.csproj` 已在隔离源码镜像中使用官方 Roslyn 4.14.0 和 .NET Framework 4.8 引用程序集构建成功。MSBuild 退出码为 `0`，日志报告 `0 个错误`，没有 `CS1617`；程序集 SHA-256 为 `EA46E8E37930D34DB24EC583A9A5D1D893C283EADD15737DAC86FEB27DAA565A`。完整输入、输出和日志哈希见 [official-net48-autofocusing-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-autofocusing-build-audit.json)。

日志有两个 `CS0219` 警告：`Model.AutoFocusing` 在两处给 `Roi` 赋值但未使用。构建未修改生产源码；结果不覆盖自动对焦运行时、厂商 SDK 行为、UI、SQL、打包、织入或完整解决方案验收。
