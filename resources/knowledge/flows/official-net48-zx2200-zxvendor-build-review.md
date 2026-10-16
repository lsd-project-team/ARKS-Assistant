# ZX2200 官方 .NET 4.8 厂商输入隔离构建复核

## 结论

在隔离源码镜像中，以官方 Roslyn 4.14.0、.NET Framework 4.8 reference assemblies 和原工程已有的 23 个厂商输入 DLL 作为 `ReferencePath`，直接构建 `AKRS.ZX2200.csproj`。构建退出码为 1，但 16 工程闭包中的程序集缺失警告已为 0；剩余失败是 `AKRS.Galaxy2.Dispense` 和 `AKRS.Galaxy2.PR` 资源许可证编译各自缺少真实 `LC.exe`，共两个 `MSB3086`。

## 可复核证据

- 执行脚本：[run-zx2200-zxvendor.ps1](../../.archify-work/official-net48-build-toolchain/run-zx2200-zxvendor.ps1)
- 构建日志：[build.log](../../.archify-work/official-net48-build-toolchain/zx2200-build-zxvendor/build.log)
- 机器审计：[official-net48-zx2200-zxvendor-build-audit.json](official-net48-zx2200-zxvendor-build-audit.json)
- 输入审计：[official-net48-zxvendor-input-review.md](official-net48-zxvendor-input-review.md)

## 边界

厂商 DLL 全部从原 `trunk/AKRS.ZX2200/bin/Debug` 或 `trunk/AKRS.ZX2200/libs` 复制并逐文件哈希一致；没有生成替代 DLL，也没有修改生产源码或工程文件。该结果只证明在现有输入下缺失程序集边界已消除，不能替代完整解决方案构建、许可证资源产出、部署或运行时验收。
