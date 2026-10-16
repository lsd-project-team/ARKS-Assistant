# 权限织入链路复核

复核日期：2026-10-06。状态：`build-blocked-weaving-unverified`。机器可复核证据见 [permission-weaving-audit.json](permission-weaving-audit.json)。本轮只核对项目声明、包文件、生成的 NuGet 导入和官方隔离构建日志，没有启动生产程序或执行登录、数据库、VM、设备与部署操作。

`AKRS.ZX2200/FodyWeavers.xml` 声明了 `PropertyChanged` 和 `MethodBoundaryAspect` 两个织入器；`packages.config` 声明 Fody 6.6.4、MethodBoundaryAspect.Fody 2.0.145 和 PropertyChanged.Fody 4.1.0。`AKRS.Galaxy2.PR` 也声明 MethodBoundaryAspect，但使用 Fody 6.0.5。仓库包目录实际有 Fody 6.0.5 的 `Fody.targets`、两个织入器 DLL；没有 Fody 6.6.4 的目标文件。

ZX2200 的生成文件 `obj/AKRS.ZX2200.csproj.nuget.g.targets:4` 指向 `$(NuGetPackageRoot)fody\6.6.4\build\Fody.targets`，并以 `Exists(...)` 为条件；当前仓库和本机 NuGet 缓存都没有这个目标文件。生成 props 仍列出了 MethodBoundaryAspect 和 PropertyChanged 的 props（分别为第 19、18 行），因此“生成了导入意图”不等于“构建时真正加载了 Fody 目标”。

官方 .NET 4.8 隔离构建日志 [build.log](../../.archify-work/official-net48-build-toolchain/zx2200-build-parameters-repair-zxvendor/build.log) 在第 3326、3332 行记录了两个包名，在第 3579、3599 行记录了运行时引用解析；但全文没有 `FodyTarget`、`Fody.WeavingTask`、`FodyExecutedWeavers` 或织入器执行诊断。该构建还受 Dispense 与 PR 的 `LC.exe` 缺失错误阻塞。仓库已有的 Fody 6.0.5 目标要求 MSBuild 16 或更高，而本次官方日志来自 .NET Framework 4.0 MSBuild；因此不能把这次编译日志当作权限织入已执行的证据。

结论是：源码和包声明证明项目设计上依赖 Fody/MethodBoundaryAspect，隔离构建证明了包/引用评估，但权限属性是否已写入输出程序集仍未验证。当前权限审计的“编辑入口/按钮事件”结论必须继续保持源码部分复核，不能升级为运行时权限保证。

## 可点击证据

- [FodyWeavers.xml](../../trunk/AKRS.ZX2200/FodyWeavers.xml)
- [AKRS.ZX2200.csproj](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4130)
- [packages.config](../../trunk/AKRS.ZX2200/packages.config#L3)
- [生成 NuGet targets](../../trunk/AKRS.ZX2200/obj/AKRS.ZX2200.csproj.nuget.g.targets#L4)
- [Fody.targets](../../trunk/packages/Fody.6.0.5/build/Fody.targets#L30)
- [permission-weaving-audit.json](permission-weaving-audit.json)
