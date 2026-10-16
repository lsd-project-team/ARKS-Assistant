# 手动换片初始化、提交和关闭失败边界

完成InitControl、BtnOK_Click、Save、BtnAbort_Click、FormClosing五个原方法的24项隔离检查。控件、消息框、保存服务、映射控件和硬件调用均为替身；关闭处理单独调用，没有模拟WinForms事件生命周期。编译运行使用内置PowerShell的.NET，不是设备或现场Framework验收。

## 初始化与取消后的状态

[构造函数](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L112)在手动模式深拷贝当前料片、绑定数据后调用[InitControl](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L134)。本轮不执行构造和深拷贝，而直接验证InitControl原方法。

|出口|已经发生的变化|
|---|---|
|初次换料提示Cancel|设Abort并Close；还未请求顶针返回等硬件方法|
|取走旧料提示Cancel|此前已请求顶针返回、扩膜下降、夹具/台面移动等；尚未把CurrentTablet写NullTablet|
|放新料提示Cancel|CurrentTablet已经写NullTablet并调用Save；取消不在此方法恢复旧对象|
|可选夹持气缸询问Cancel|只跳过该气缸下降，后续换料仍继续|
|新料传感器false|重复放料提示；没有在此循环直接检查Stop|

正常路径最终ShowDialog。非Working条件下仍可执行正常初始化；不能把IsWorking理解为入口门禁。InitControl只有在catch里调用IsWorking：为true时抛一个只含原Message的新Exception（没有InnerException）；为false时提示错误并正常返回，该catch没有显式设置Abort。返回时的DialogResult仍可能为None，不能自动解释成成功或取消。

失败注入覆盖顶针返回与Save。Save失败发生在CurrentTablet变成NullTablet之后，当前引用保留该变化。此结论是内存及调用顺序，不表示真实文件成功写入或物理料片已移走。

## 完成按钮先提交再请求动作

[BtnOK_Click](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L242)在选择为空时提示并返回；非空后依次Save、移动提示、夹持气缸上升、晶圆特有的准备位/扩膜上升、检查并开启真空，最后设置DialogResult.OK并Close。

[Save](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L396)先把tempTablet直接赋给共享CurrentTablet，再调用参数Save，最后刷新映射。不是副本提交，也没有本地回滚。对保存、刷新、提示、气缸、准备位、扩膜和真空检查七处注入异常，均确认保留已赋的共享引用，后续调用截断，尚未设置OK或执行Close。真实持久化和硬件返回语义未验证。

晶圆和适配器各有一项成功路径检查，后者跳过晶圆专有准备位/扩膜调用。选择校验仅验证null分支，未证明任意非空名称与真实配置一致；Load和EditValueChanged不在这24项执行范围。

## Abort与关闭清理

[Abort](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L275)只写Abort再Close。测试在一次刷新失败、共享引用已发布之后调用Abort，确认没有恢复旧料片；这是方法组合测试，不证明异常后按钮在真实UI中可达。

[FormClosing](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L573)先Dispose非空映射控件，再ResetAlarm。四项检查覆盖无映射、正常释放、Dispose失败、报警复位失败；Dispose抛异常时ResetAlarm不会执行。该方法没有finally重试或数据回滚。

事件证据：[OK绑定](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.Designer.cs#L308)、[Abort绑定](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.Designer.cs#L331)、[FormClosing及Load绑定](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.Designer.cs#L641)。绑定证明局部事件连接，不等于实际窗口生命周期验收。

## 验证及交接边界

命令 `node scripts/test-manual-wafer-change.cjs`：9项初始化场景、3项提交门控/成功路径、7项提交异常、1项部分提交后Abort、4项关闭清理，共24项。方法源文不改写，输出源文件、片段及夹具哈希。[9段证据快照](manual-wafer-change-evidence.json)接入统一阅读器。

- 已完成：本窗口上述五方法的顺序、失败前缀及局部状态保留；与[自动换片外层](wafer-change-retry-review.md)衔接。
- 未完成：构造深拷贝、Load/名称切换/网格事件、真实UI线程与关闭取消、异常后交互可达性。
- 未完成：实际配方一致性、保存/恢复、SDK运动等待、停止期间设备输出、换片图与语义台账的最终同步。
- 29组仍部分复核、0组完整验收；原方法受控检查不能替代全模块和设备验收。
