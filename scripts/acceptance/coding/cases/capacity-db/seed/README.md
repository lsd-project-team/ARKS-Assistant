# AKRS.Capacity.DB（产能统计数据库层）

来自真实产能统计项目的数据库访问层，.NET Framework 4.8，老式 csproj。

```
msbuild Capacity.DB.sln /p:Configuration=Debug
```

依赖：`refs/System.Data.SQLite.dll`。

当前提供容量/故障分类等数据库访问能力。
