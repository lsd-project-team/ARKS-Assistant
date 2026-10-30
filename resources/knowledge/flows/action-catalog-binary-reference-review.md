# 原动作目录源码候选与原程序集依赖闭包

日期：2026-10-06。状态：`isolated-source-candidate-compile-and-init-passed`。机器可读结果：[action-catalog-binary-reference-audit.json](action-catalog-binary-reference-audit.json)。准备、编译和运行脚本位于 `.archify-work`，候选目录为 `.archify-work/action-catalog-source-on-original-binary`。

本轮把原始 `DispenseActionNodes.cs`、`BondActionNodeRepository.cs` 和 51 个实际动作节点/分部源文件放入隔离候选，并引用未修改的原 ZX2200 源码构建产物及其真实引用闭包。Roslyn 使用 54 个源文件和 162 个引用成功发射，错误数为 0；由于候选源类型与原程序集中的同名类型并存，产生 118 个警告，其中 109 个是 `CS0436` 类型遮蔽警告。这是源码闭包探针，不是可部署的主项目产物。

候选 Probe 两轮运行一致：`DispenseActionNodes.Init()` 注册 15 个 S1 动作，`BondActionNodeRepository.Init()` 注册 19 个 S2 动作。另用只引用原程序集的独立顺序探针读取原二进制目录，候选的 S1 15 项和 S2 19 项类型序列均逐项完全相同。再以反射方式分别加载候选和原二进制，执行继承自 `ActionNode` 基类的 `InteractiveAction.IsDoWork()`；两边均返回 `True`，输出完全一致。运行没有进入动作节点 `DoWork`、生产 Task、VM、UI、SQL、视觉、运动、力控或设备 I/O。

这项结果把动作目录源码闭包从此前的 1,585 个编译错误推进到可发射、可初始化的隔离候选，同时保留类型遮蔽风险。它不能替代原工程联合 MSBuild、Fody/LC、部署或现场验收，也没有修改 `trunk` 生产源码或项目文件。下一步可在同一候选上执行有明确非设备前置条件的 `IsDoWork` 分支。

