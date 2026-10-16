# InterpolationMovementTest 原始工程依赖声明审计

原始 `.csproj` 声明了 `..\AKRS.ZX2200\AKRS.ZX2200.csproj` 的 `ProjectReference`。隔离源码发射准备没有重新生成该 ProjectReference，而是选择了 `trunk/InterpolationMovementTest/bin/Debug/AKRS.ZX2200.exe` 这一已有仓库二进制；其 AssemblyRef 为 v1.2.0.0。当前主程序独立发射物为 v1.5.0.0，因此产生版本身份冲突。

[版本修复候选](original-source-artifact-reference-closure-repair-progress.json)已证明将当前主程序元数据用于隔离重编可消除冲突；原始 csproj、Compile 输入和生产源码均未修改。
