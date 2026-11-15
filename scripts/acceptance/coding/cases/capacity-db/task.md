# 任务：真实 .NET Framework 项目增加故障名称规范化

工作区是真实产能统计项目的数据库层 `AKRS.Capacity.DB`（.NET Framework 4.8，老式 csproj，使用 MSBuild 构建）。

要求（不得改变现有行为）：

1. 在 `FaultClassification` 中新增：

   ```csharp
   public static string NormalizeName(string raw)
   ```

   - `null`、空串或纯空白 → 返回 `""`；
   - 去掉首尾空白；
   - 中间连续空白（空格、制表符、换行）压缩成一个空格；
   - 其他字符保持不变。
2. README 补充该方法说明；不要留 TODO/占位。
3. 构建必须 0 错误 0 警告（编码工具的 `verify build` 会自动识别老式工程并走 MSBuild）。

隐藏验收会引用 `AKRS.Capacity.DB.dll` 直接调用 `FaultClassification.NormalizeName`，验证上述边界。
