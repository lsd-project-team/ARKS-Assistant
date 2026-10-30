# 16工程原始编译项核验

16个工程当前声明的1410份原始 C# 编译项均有直接 Roslyn 编译成功记录，源码未改写，产物内没有夹具声明。新增14个工程的188份源码真实编译退出码均为0，重编译14个产物哈希全部一致。此前主程序1137项与PR85项的冻结准备保持。详见[输入与回执](all-project-source-build-test.json)、[来源审计](all-project-source-build-audit.json)与[进度](all-project-source-build-progress.json)。

|项目文件|原Compile项|退出码|警告数|重编译产物|
|---|---:|---:|---:|---|
|AKRS.ZX2200.csproj|1137|0|422|一致|
|AKRS.Galaxy2.PR.csproj|85|0|4|一致|
|AKRS.Calibration.csproj|12|0|1|一致|
|Akrs.ChangeJson.csproj|12|0|1|一致|
|AKRS.Galaxy.SoftKey.csproj|6|0|0|一致|
|AKRS.Galaxy2.AutoFocusing.csproj|4|0|2|一致|
|AKRS.Galaxy2.AxisCompensate.csproj|7|0|0|一致|
|AKRS.Galaxy2.CoordinateSystems.csproj|13|0|0|一致|
|AKRS.Galaxy2.Dispense.csproj|81|0|8|一致|
|AKRS.Galaxy2.LogTest.csproj|6|0|0|一致|
|AKRS.Galaxy2.Machine.csproj|6|0|0|一致|
|AKRS.Galaxy2.MachineSupport.csproj|4|0|0|一致|
|AKRS.Galaxy2.PR.Test.csproj|6|0|0|一致|
|AKRS.Galaxy2.RealtimeCurve.TestDemo.csproj|6|0|0|一致|
|AKRS.Galaxy2.TeachTest.csproj|17|0|45|一致|
|InterpolationMovementTest.csproj|8|0|4|一致|

新增编译输入逐个对照原 csproj 无条件 Compile 项及既有 Debug/AnyCPU MSBuild 求值，完整路径与顺序相同；采用求值后的 PlatformTarget、原程序集名称/输出类型及 DEBUG/TRACE，Roslyn Latest/CSharp14 发射。原声明引用和完整主程序的真实缓存元数据闭包共同供给引用，PR使用此前重新编译的产物。每个程序集排除自身引用。引用解析、工具、原项目文件、188份编译源码、额外依赖、诊断与产物绑定484项新增冻结输入；父准备1465项单独冻结并按哈希绑定，合计1949项冻结绑定。

## 1410与1436的口径

文件系统基准含1436份源码，当前项目 Debug/Release AnyCPU 的编译范围是1410份。26份文件未被原 Compile 项纳入：主程序20份、PR2份、Machine1份、Dispense1份、InterpolationMovementTest2份。完整逐文件列表及原哈希保留在本次输入回执，既有[逐文件影响表](compile-scope-impact.md)继续适用。它们仍是源码分析范围，不作为当前编译成功的源码项。

## 证据边界与后续

这是逐项目独立源码发射，使用已有真实依赖元数据；新增项目引用未统一替换为本次新产物。因此尚未证明16工程互相引用全部新构建产物后的联合构建兼容。下一步建立新的隔离引用组合，核验本次源码产物之间的API与项目依赖一致性，保留本次冻结输入和产物。

仍缺 .NET Framework v4.8 targeting pack 和声明的 Parameters 工程/二进制。本次没有执行完整 MSBuild、包恢复、导入目标、资源/resx/LC、Fody/PostSharp织入、程序集签名或部署。所有新增产物只做编译及重放，未运行其入口、UI或设备；此前主程序/PR的61项非设备检查没有增加，不代表新增14工程运行验收。首次 MVDCalibTrans.Net 原生元数据预读失败及两次既有File.Replace失败记录保持。

原1328/278/119套件、122文件/642条失败诊断与阅读器40专题/3817快照保持。此次编译范围不增加业务断言数、专题数或模块完成状态。16工程源码发射已核验，29组业务闭环、13项整体要求和原生/设备验收仍未完成，生产源码未改。
