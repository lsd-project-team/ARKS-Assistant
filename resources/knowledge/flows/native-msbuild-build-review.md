# 原工程 MSBuild 实际构建与复跑

两份新的隔离副本各调用16个原csproj的Debug/AnyCPU Build，再调用原解决方案Debug/Release × Any CPU/x64四种Build，共40次实际调用。每轮只有SoftKey工程退出0，其余15工程及4种解决方案构建均退出1；逐项退出码、警告类别和规范化错误内容一致。审计通过仅代表这些结果可核对，完整Build与部署未通过。另两轮使用用户临时目录的40次候选调用完整保留，不计入最终隔离验收。

每份副本含3,023个原输入、529,500,715字节、全部1,436个C#文件与16个csproj，包含packages和安装工程输入；逐文件字节核对，排除既有bin/obj与IDE缓存。实际输出保持原csproj路径，落在副本内；最终两轮子进程TEMP/TMP另设专属目录，框架属性文件也在其中。没有修改原C#/csproj、追加框架/编译器/许可证/织入覆盖参数、还原包或执行产品程序。最初两次预处理记录器把非零结果当成脚本错误而停止，原日志及脚本保留；最终记录器捕获完整16个结果。

本机Framework MSBuild /version为4.8.9221.0，不能等同于现代MSBuild15/16。/pp预处理7个成功、9个因ToolsVersion15.0退出1/MSB4132；实际Build自动将未知工具版本按4.0处理，这个降级来自工具日志，没有显式/tv覆盖。因此预处理失败不能直接推断Build在同一步失败。所有最终Build日志都有MSB3644：缺少.NET4.8引用程序集，工具转用运行时/GAC程序集；它在这里是警告。dotnet --list-sdks退出0且无SDK行。

|原工程|两轮实际退出|错误类别（含引用工程）|首个错误所属工程|
|---|---|---|---|
|AKRS.Calibration|1|CS1617|AKRS.Calibration|
|Akrs.ChangeJson|1|MSB3086|Akrs.ChangeJson|
|AKRS.Galaxy.SoftKey|0，生成 EXE|无错误；3类警告|—|
|AKRS.Galaxy2.AutoFocusing|1|CS1617|AKRS.Galaxy2.AutoFocusing|
|AKRS.Galaxy2.AxisCompensate|1|CS1617|AKRS.Galaxy2.MachineSupport|
|AKRS.Galaxy2.RealtimeCurve.TestDemo|1|MSB3086|AKRS.Galaxy2.RealtimeCurve.TestDemo|
|AKRS.Galaxy2.CoordinateSystems|1|CS1617|AKRS.Galaxy2.CoordinateSystems|
|AKRS.Galaxy2.Dispense|1|MSB3086|AKRS.Galaxy2.Dispense|
|AKRS.Galaxy2.LogTest|1|CS1617|AKRS.Galaxy2.LogTest|
|AKRS.Galaxy2.Machine|1|CS1617|AKRS.Galaxy2.Machine|
|AKRS.Galaxy2.MachineSupport|1|CS1617|AKRS.Galaxy2.MachineSupport|
|AKRS.Galaxy2.PR|1|MSB3103|AKRS.Galaxy2.PR|
|AKRS.Galaxy2.PR.Test|1|MSB3103|AKRS.Galaxy2.PR|
|AKRS.Galaxy2.TeachTest|1|MSB3103|AKRS.Galaxy2.TeachTest|
|AKRS.ZX2200|1|CS1617、MSB3086、MSB3103|AKRS.Calibration|
|InterpolationMovementTest|1|CS1617、MSB3086、MSB3103|AKRS.Calibration|

CS1617是旧csc不接受原LangVersion=latest。MSB3086出现在ChangeJson、Component.TestDemo和Dispense的实际LC任务：SdkToolsPath为空，查询Windows v8.0A/WinSDK-NetFx40Tools-x86未找到LC.exe。PR、PR.Test和TeachTest的MSB3103指向DevExpress.Utils.Svg.SvgImage（DevExpress.Data21.2.7）类型解析；这不是已证明的resx字节损坏。既有DevExpress DLL可在原bin目录找到，而这次干净副本排除bin，原引用解析发出MSB3245；此前388资源/1498项的独立资源编译验证保持。Main和Interpolation的错误包含引用工程，不能据此声称Main自身Csc/LC已完成或失败。

SoftKey两份EXE均14,848字节，Cecil只读确认相同程序集身份、引用、资源、类型/方法元数据及.NETFramework4.8标记，入口为原Program.Main(string[])；I386、Required32Bit/Preferred32Bit。它仍有MSB3644、MSB3247版本冲突、MSB3270架构警告，且输出复制了Framework64的mscorlib.dll。两份MVID和SHA不同，未验收确定性构建、执行或部署。每轮116个副本新输出及专属临时目录记录均保留。

四种解决方案构建均返回CS1617/MSB3103，未完成整个依赖图。Parameters.csproj确实不存在，但此次不能把它冒充已执行到的失败点；原Release/x64主项目映射和缺少对应OutputPath也仍属此前评估证据。SetupZX2200.vdproj存在，却在四种配置均没有Build.0选择，所以解决方案Build本身不能证明安装包已构建。没有执行Publish/MSI安装；没有观察到WeavingTask/PostSharp任务，尚未验证现代PackageReference还原后的Fody/PostSharp原流水线。此前LC/Fody兼容性失败记录不改。

[输入与结果](native-msbuild-build-test.json)、[回执审计](native-msbuild-build-audit.json)、[进度](native-msbuild-build-progress.json)绑定原清单、两轮原始进程回执、UTF-8诊断日志、成功产物和工具哈希。当前来源台账仍19106，正式1328运行检查保持独立，本诊断不增加业务断言。16工程/29组/1436文件/13项整体目标未完成；下一步完整构建需要匹配的现代构建工具/.NET4.8 targeting pack、可重复解析的厂商引用与LC工具、缺失工程及完整包/织入流水线，其他业务与界面验收仍可独立推进。
