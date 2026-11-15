# 任务：从零实现产能统计查询 CLI（.NET Framework 4.8）

工作区是空的，只有一个 SQLite 数据库 `data/capacity.db`、本地引用 `refs/System.Data.SQLite.dll` 与 `refs/SQLite.Interop.dll`。

从零创建 .NET Framework 4.8 控制台程序 `CapacityStats`（老式 csproj，MSBuild 构建，PlatformTarget=x86）：

1. 用法：
   - `CapacityStats.exe <db> week <yyyy-MM-dd>`：输出该日期所在周（周一至周日）每天的总产能，再输出总计；
   - `CapacityStats.exe <db> month <yyyy-MM>`：输出该自然月的总产能；
2. 周输出格式（7 行 + 总计）：
   ```
   DAY 2026-01-05 123
   ...
   TOTAL 456
   ```
3. 月输出格式：`TOTAL 789`；
4. 数据来自 `cap` 表：按 `date` 汇总 `count`；周从周一开始，缺失日期按 0 计；
5. 参数缺失、日期非法、数据库不存在：向 stderr 输出错误并返回退出码 2；
6. 引用 `refs/System.Data.SQLite.dll`（相对路径），构建时把 `refs/SQLite.Interop.dll` 复制到输出目录；
7. 写 README（用法/构建）；不要留 TODO/占位。

完成前用 MSBuild 构建，0 错误 0 警告。隐藏验收会运行生成的 exe 并对比数据库计算结果。
