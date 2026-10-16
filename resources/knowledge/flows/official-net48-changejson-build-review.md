# Akrs.ChangeJson 隔离构建失败记录

`Akrs.ChangeJson.csproj` 的官方工具链试跑已保留为失败证据，MSBuild 退出码为 `1`。失败发生在 `CompileLicxFiles`：当前机器的 .NET Framework MSBuild 找不到 `LC.exe`（`MSB3086`，Windows SDK v8.0A 的 `WinSDK-NetFx40Tools-x86` 缺失）。解析引用时还缺少 `DevExpress.Dialogs.v21.2.Core` 和 `DevExpress.XtraDialogs.v21.2`（两个 `MSB3245`）。

这次运行没有出现 `CS1617`，所以已确认旧 C# 语言版本阻塞不是当前首个失败点；但由于资源许可编译在 `CoreCompile` 前失败，不能据此判断 C# 源码最终能否编译。完整日志与哈希记录在 [official-net48-changejson-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-changejson-build-audit.json)，输出目录保留在 `.archify-work/official-net48-build-toolchain/changejson-build-with-vendor`。
