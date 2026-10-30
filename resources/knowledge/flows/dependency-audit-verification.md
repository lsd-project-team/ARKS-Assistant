# 项目依赖审计脚本核验

2026-10-06 修复了两个审计脚本缺少 UTF-8 BOM 导致 Windows PowerShell 5 按本地代码页解析的问题；脚本正文口径未改，仅补充 BOM。验证使用本机 `pwsh 7.6.5`：

- `build-project-dependencies.ps1 -Check` 退出码为 0，核对 16 个项目、13 个 `ProjectReference`，其中 1 个声明目标缺失。
- `build-external-dependencies.ps1 -Check` 退出码为 0，核对 16 个项目、806 条声明：438 条字面路径存在、8 条字面路径缺失、335 条需进一步解析、25 条含未求值表达式。

这些是 XML 声明层面的证据；条件、导入、包恢复、ABI、运行时加载和设备行为仍需单独验证。原生成清单与项目源码均未改写。
