# AKRS.Calibration 隔离构建复核

截至 2026-10-06，`AKRS.Calibration.csproj` 已在隔离源码镜像中用官方工具链完成一次可复核构建：MSBuild 退出码为 `0`，日志包含“已成功生成”和 `0 个错误`，没有 `CS1617` 或其他编译错误。产物程序集的 SHA-256 为 `BA01004A5B4D390686242703216AC4ECEBD52A72F72DCA73839A8364B38F5293`。

构建使用 Windows .NET Framework 4.0.30319 的 MSBuild，Roslyn `Microsoft.Net.Compilers.Toolset 4.14.0` 的 `csc.exe`，以及官方 `Microsoft.NETFramework.ReferenceAssemblies.net48 1.0.3` 引用程序集。源码镜像包含 19 个项目输入文件；从既有 Debug 输出只读复制了 29 个 DevExpress DLL 到隔离 vendor 目录，作为引用身份输入。所有输入、输出、包文件和日志的哈希已写入 [official-net48-calibration-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-calibration-build-audit.json)。

日志仍有两个警告：项目是 MSIL，而 `AKRS.Galaxy2.Drive` 是 AMD64；`FormCalib.mainViewControl` 字段未赋值。这次构建只证明该项目在指定镜像和引用集合下可编译，不代表整套解决方案、Fody 编织、部署打包、硬件/UI 运行或 SQL 集成已经验收。完整清单进度仍记录为未完成，见 [official-net48-calibration-build-progress.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-calibration-build-progress.json)。
