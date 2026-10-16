# AKRS.Galaxy.SoftKey 隔离构建复核

`AKRS.Galaxy.SoftKey.csproj` 已在隔离源码镜像中使用官方 Roslyn 4.14.0 和 .NET Framework 4.8 引用程序集构建成功。MSBuild 退出码为 `0`，日志报告 `0 个错误`，没有 `CS1617`；生成的 EXE SHA-256 为 `730D88F7CD7B5AEA26C1C905807C9ABB511F6A7A49A53CDC2FB9823329C13471`。完整哈希见 [official-net48-softkey-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-softkey-build-audit.json)。

日志有一个 `MSB3247` 依赖程序集版本冲突。项目的 Authenticator、log4net、SunnyUI、SunnyUI.Common 和 USL3 HintPath 均来自隔离源码镜像；未修改生产源码。结果不覆盖软键运行时、UI、许可、打包、织入或完整解决方案验收。
