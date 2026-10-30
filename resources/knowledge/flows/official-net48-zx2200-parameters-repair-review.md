# ZX2200 Parameters 项目引用隔离修复复核

在源码隔离镜像中复制主项目文件，移除指向不存在的 `AKRS.Galaxy2.Parameters.csproj` 的陈旧 `ProjectReference`，并使用同一批 23 个原工程厂商 DLL 重新构建。候选构建没有再触达该引用，程序集缺失警告仍为 0，最终仍只剩 Dispense/PR 的两个逻辑 `LC.exe` 许可证编译前置条件，退出码为 1。

这说明陈旧 Parameters 项目引用需要清理，但它不是当前主闭包失败的根因；相邻 46 个 C# 与 12 个 RESX 已由主项目直接编译输入覆盖。候选文件和构建结果均在隔离目录，生产工程未改。

- 候选构建脚本：[run-zx2200-parameters-repair-zxvendor.ps1](../../.archify-work/official-net48-build-toolchain/run-zx2200-parameters-repair-zxvendor.ps1)
- 构建日志：[build.log](../../.archify-work/official-net48-build-toolchain/zx2200-build-parameters-repair-zxvendor/build.log)
- 机器审计：[official-net48-zx2200-parameters-repair-audit.json](official-net48-zx2200-parameters-repair-audit.json)
