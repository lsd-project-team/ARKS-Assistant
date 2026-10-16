# 原许可证目标与现有Fody包兼容性失败证据

5个声明licenses.licx的原工程实际经 PrepareResourceNames → CompileLicxFiles 调用安装的MSBuild，全部真实退出1，错误MSB3086：任务在SdkToolsPath空值和注册表Windows v8.0A/WinSDK-NetFx40Tools-x86中未找到LC.exe。输入为原licx/项目和已冻结的源码编译引用列表，输出目录隔离，没有生成.licenses。批次记录器退出0仅表示成功保存全部失败记录，不能解释为许可证编译通过。20条控件声明/12个唯一类型已用只读Cecil定位到身份完全一致的DevExpress21.2.7程序集；未调用构造器、LicenseProvider或LicenseManager，也不能据此证明设计时许可证有效。

Main和PR的资源版产物复制到隔离目录，显式导入仓库现有Fody6.0.5.targets。两个兼容性目标均真实退出1，被“MSBuild16及以上”守卫拒绝，副本字节保持不变，没有运行WeavingTask。目标日志中的Current version:15来自该targets的默认属性，不是对本机安装了MSBuild15的确认；未覆盖该属性绕过守卫。这个诊断并非Main既有nuget.g.targets所记录的Fody6.6.4完整原流程，不能把不同包版本混作原工程织入验收。本轮未安装包/SDK，未执行PostSharp。

5个许可证目标和2个兼容性目标复跑同样失败，元数据检查重放相同；日志中的时间允许变化，未宣称日志字节相同。新增37项冻结绑定父3178项，共3215项。见[测试](license-weaving-probe-test.json)、[审计](license-weaving-probe-audit.json)、[进度](license-weaving-probe-progress.json)。

父16工程/1410源码/388资源/1498数据项的序列化、嵌入及回读通过保持；许可证和织入本轮只完成失败证据定位。原124几何/98模型与1328/278/119、旧122文件失败、40专题/3817快照保持，业务断言不增加。生产源码未改，未执行原入口/UI/轴/相机/设备；匹配的MSBuild/SDK工具和厂商运行依赖、完整域/具体动作、PR/校准/测量、IO稳定性、原部署仍待验收。16工程/29组/1436文件/13项整体未完成。
