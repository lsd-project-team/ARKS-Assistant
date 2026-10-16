# ZX2200 缺失 Parameters 项目引用

项目依赖核验确认 `trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4110` 声明了 `..AKRS.Galaxy2.ParametersAKRS.Galaxy2.Parameters.csproj`，但目标文件和同名项目目录不存在。全 `trunk` 没有任何名称匹配 `*Parameters*.csproj` 的项目文件。

相邻目录 `trunk/AKRS.ZX2200/SupportFeature/Parameters` 有 58 个源码/资源文件，已逐文件登记哈希；进一步核对确认根项目直接包含全部 46 个 C# 文件和 12 个 RESX 文件。缺失的 `ProjectReference` 仍代表一个不存在的工程身份，可能是陈旧或重复引用；本证据不据此臆造独立程序集边界，也不把这些文件当作缺失项目的替代。审计结果见 [missing-parameters-project-audit.json](C:/Users/akrs/Documents/ChatGPT/archify/docs/archify/missing-parameters-project-audit.json)。另在隔离候选中移除该陈旧引用后重跑主闭包，结果仍为程序集缺失 0、两个逻辑 `LC.exe` 前置条件，说明它需要清理但不是当前构建失败根因，详见 [Parameters 引用隔离修复复核](official-net48-zx2200-parameters-repair-review.md)。本轮没有合成项目文件，也没有修改生产工程。
