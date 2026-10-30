# 完整主程序与 PR SDK 原源码编译准备

主程序的1137个原始 Compile 项和 PR SDK 的85个原始 Compile 项均已直接编译成功，共1222份原始源码、2个工程。源码未筛选、未改写，两个产物内均没有夹具声明。重编译产物与初次成功产物逐字节一致；独立测试 DLL 在原生 CLR 4.0.30319.42000 中通过61项非设备检查，重放名称与顺序一致。来源审计冻结1465项输入。详见[输入与回执](full-original-source-build-test.json)、[审计](full-original-source-build-audit.json)和[进度](full-original-source-build-progress.json)。

## 编译范围与依赖选择

直接读取两个原 csproj 的所有无条件 Compile 项，采用 Roslyn 5.0、Latest/CSharp14、DEBUG/TRACE、X64，分别输出原程序集名 AKRS.ZX2200.exe 与 AKRS.Galaxy2.PR.dll。主程序保留原 Program.Main 入口，但没有执行。主程序161个、PR83个元数据引用使用真实缓存依赖，主程序引用本次重新编译的 PR。引用解析明细、原项目声明、工具、SDK、编译输入、日志和产物均有冻结副本。

主程序三次失败依次保留1015、61、2条编译错误及对应输入，真实退出码均为1。现有 libs、项目 bin 和主程序 bin 内若干 SDK 虽都标记1.0.0.0，实际 API 不同：Machine 工作模式、Dispense 类型、Coordinate 运算符和 PR 方法签名存在差异。最后两条错误来自旧 PR 二进制缺少 PREntity.IsSaveLocateImage 与 SaveLocateImageAction；完整85份 PR 源码重编译后主程序成功。没有修改生产源码或补造同名业务类型。

## 原生非设备分支

61项独立断言覆盖 BaseCarrierConfiguration 构造、Reset 与示教就绪；BondActionService 的 BondOnTU/DipFluxOnTU 和非法枚举数据映射；PickActionService 的 wafer/waffle 和非法枚举数据映射；原机器硬件/软件配置默认值；重新编译 PR 的两项委托字段契约。测试只调用这些不请求设备的分支，未执行具体动作 DoWork、原目录或具体节点构造、主程序入口、设备或 UI。BondActionService 为内部类型，通过反射调用原方法，没有替换它。

原载具构造会将 wafer-map 状态名称覆盖为 Flip to wafer，且 FlipToWafer 保持 null，在辅助列表出现两个空位并拒绝就绪。Reset 补齐状态和名称；非法载具枚举999的 Reset 将状态均设为 ForBidden，从而通过就绪。Wafer 的 IsMapping=true 仍使映射示教处于 ForBidden；Waffle/StaticWaffle 在禁用搜墨点时仍要求墨点示教。上述结论限定于实际受测配置与分支，尚未证明生产触发频率。

第一次全引用原生元数据预读因 MVDCalibTrans.Net 的依赖加载失败，真实退出码1日志已保留。后续按需解析依赖的61项检查通过，不能据此认定完整厂商运行库已可用。

## 未完成范围

本机没有 .NET Framework v4.8 targeting pack，本次使用 Framework 运行时元数据。没有运行完整 MSBuild、恢复包、导入目标、resx/资源/LC 编译或 Fody/PostSharp 织入，产物只用于当前编译与非设备分支核验。缺失的 AKRS.Galaxy2.Parameters 项目及二进制仍待补齐；它未被当前源码使用，因此不阻止直接 Roslyn 发射，但原工程构建门槛未通过。

旧122文件夹具组合的642条错误仍完整保留；新1222原源码编译是不同的更广范围证据，不将旧失败记录改成成功。独立61项不加入1328、278或119计数，既有阅读器40专题/3817快照与冻结基线保持。16工程、29组、1436份C#与13项要求仍未全部完成。下一步核验其余14工程的214份源文件及构建边界，再推进原域/动作、PR/校准/测量、IO稳定性、资源/织入、原生UI与设备运行。
