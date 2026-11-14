# 任务：.NET 8 控制台日志分析工具

在工作区从零实现一个 .NET 8 控制台程序 `LogAnalyzer`：

1. 读取一个文本日志文件，按行解析 `YYYY-MM-DD HH:MM:SS LEVEL message` 格式。
   建议用正则 `^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) ([A-Z]+) (.*)$` 解析，时间用
   `DateTime.TryParseExact(..., "yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture, ...)`；
   不要用宽松解析（`DateTime.Parse` 容易把坏行当有效行）。
   坏行定义为：字段数不足、时间格式非法、等级不在 TRACE/DEBUG/INFO/WARN/ERROR/FATAL 内；
   坏行必须跳过，不计入各等级计数、总行数与首末时间，并单独统计坏行数。
2. 支持 `--level WARN`、`--since 2026-01-01` 过滤；输出统计：总行数、各等级计数、首末时间。
   等级严重度顺序：TRACE < DEBUG < INFO < WARN < ERROR < FATAL。
3. 验收会用下面的样例检查（可作为自测夹具）：

```
2026-01-02 10:00:00 INFO 启动
2026-01-02 10:01:00 WARN 低库存
2026-01-02 10:02:00 ERROR 通信失败
bad line without fields
```

   期望：总行数 3、INFO/WARN/ERROR 各 1、坏行 1、首条 10:00:00、末条 10:02:00；
   `--level WARN` 时 WARN+ERROR 共 2 条；缺文件退出码 2。
3. 无参数或文件不存在时打印用法并返回退出码 2。
4. 写一个控制台自测工程 `tests/LogToolSelfTest`（引用实现源码），至少 6 个 PASS 用例，
   覆盖：基础解析、等级过滤、时间过滤、坏行跳过、空文件、缺文件退出码。
5. 写 README.md（用法与示例）。

完成前运行 `dotnet build` 与 `dotnet run --project tests/LogToolSelfTest/LogToolSelfTest.csproj`，
0 错误 0 警告、自测全部 PASS；不要留 TODO/占位。
