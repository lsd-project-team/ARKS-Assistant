# AKRS.ZX2200 隔离构建失败记录

`AKRS.ZX2200.csproj` 的隔离 MSBuild 试跑已保留为失败证据，退出码为 `1`。根项目展开到多个项目引用后产生 60 个警告和 40 个错误：包含缺少 DevExpress 引用导致的 `CS0246`、PR 的 `DevExpress.Utils.Svg.SvgImage` 资源反序列化 `MSB3103`，以及 Dispense 的 `LC.exe` 缺失 `MSB3086`。

根项目仍引用不存在的 `AKRS.Galaxy2.Parameters.csproj`；邻近 `SupportFeature/Parameters` 的源文件仅作材料证据，未合成项目。日志中没有 `CS1617`。完整日志哈希见 [official-net48-zx2200-build-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/official-net48-zx2200-build-audit.json)，输出目录保留在 `.archify-work/official-net48-build-toolchain/zx2200-build`。本轮没有伪造许可证工具、补造缺失程序集或修改生产工程。
