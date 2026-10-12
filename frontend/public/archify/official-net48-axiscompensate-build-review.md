# AKRS.Galaxy2.AxisCompensate 隔离构建复核

`AKRS.Galaxy2.AxisCompensate.csproj` 已在隔离源码镜像中用官方 Roslyn 4.14.0 和 .NET Framework 4.8 引用程序集构建成功。MSBuild 退出码为 `0`，同时构建其 `AKRS.Galaxy2.MachineSupport` 项目引用；日志报告 `0 个错误`，没有 `CS1617`。AxisCompensate 程序集 SHA-256 为 `579ADF360A6E852BDD9046F5BF01BEEAD6A5D4AD2C502A10E795DAF63C179098`，完整哈希见 [official-net48-axiscompensate-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-axiscompensate-build-audit.json)。

日志保留四个警告：MachineSupport 的三个 AMD64 引用被 MSIL 项目消费，以及一个依赖程序集版本冲突。构建输入和输出均在 `.archify-work/official-net48-build-toolchain/axiscompensate-build` 中，未修改生产源码。该结果不覆盖硬件运行、UI、SQL、打包/Fody 或整套解决方案验收。
