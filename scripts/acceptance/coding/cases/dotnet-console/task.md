# 任务：.NET 8 控制台日志分析工具

在工作区从零实现一个 .NET 8 控制台程序 `LogAnalyzer`：

1. 读取一个文本日志文件，按行解析 `YYYY-MM-DD HH:MM:SS LEVEL message` 格式。
   坏行定义为：字段数不足、时间格式非法、等级不在 TRACE/DEBUG/INFO/WARN/ERROR/FATAL 内；
   坏行必须跳过，不计入各等级计数、总行数与首末时间，并单独统计坏行数。
2. 支持 `--level WARN`、`--since 2026-01-01` 过滤；输出统计：总行数、各等级计数、首末时间。
3. 无参数或文件不存在时打印用法并返回退出码 2。
4. 写一个控制台自测工程 `tests/LogToolSelfTest`（引用实现源码），至少 6 个 PASS 用例，
   覆盖：基础解析、等级过滤、时间过滤、坏行跳过、空文件、缺文件退出码。
5. 写 README.md（用法与示例）。

完成前运行 `dotnet build` 与 `dotnet run --project tests/LogToolSelfTest/LogToolSelfTest.csproj`，
0 错误 0 警告、自测全部 PASS；不要留 TODO/占位。
