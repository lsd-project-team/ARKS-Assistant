# 视觉报警门控、硬件绑定与关灯边界

更新：2026-09-28。承接上视读码专题，区分源码条件与实际配置；未执行设备。

## 已收窄的结论

普通上视报警不能直接描述为“用户可点击跳过”。FrmVisionAlarm_Load按算法和相机名称分支：先处理EpoxyDetectAlg，再判断晶圆相机，最后在CameraName等于“上视相机”时显示“下一颗”并隐藏BtSkip。因此在非胶量算法且相机名匹配的上视/读码报警中，跳过按钮被隐藏。上轮指出的读码switch无Ignore/default仍是代码事实，但不能用它证明这条正常UI路径会产生Ignore。

上视模块按“上视相机”查硬件对象，再把该对象HardwareName写入PR。实际硬件注册名和算法配置仍需对应现场数据，不能把仓库查找字符串与所有运行配置无条件等同。

## 报警交互顺序

1. 构造窗体：InitializeComponent、保存PR、SetAxis、保存消息/标题，Task.Run启动BackgroundWorkerDoWork。
2. Load：显示报警，按算法/相机配置按钮，最终允许后台工作。Designer绑定Load、FormClosing、FormClosed及OK、Abort、Skip、Retry按钮。
3. 后台循环：isclose为false时，每次允许工作就置isWork=true，执行采图/PR和显示，再置false，Sleep(300)。PRHardware不为空时显式lock(entity)；为空的分支没有这层锁，不代表PR内部无锁。
4. OK先禁止后台工作，然后while(isWork)每100ms等待；对于普通PR路径锁entity重新DoWork。失败提示并重新允许刷新；成功保存BaseAlgResult并设OK。MatchResult单独复制坐标/角度，其他结果直接保存对象。实体为空、双模板或晶圆线程、胶量检测存在提前OK分支。
5. Abort先Machine.Stop，再设DialogResult.Abort；若Stop抛出则后一句不保证执行。下一颗按钮只设置Retry，实际抛料/重取在调用方。
6. FormClosing置isclose=true；FormClosed调用CloseAlarm，再while(task.Status==Running)每10ms等待。CloseAlarm只查报警器并做空检查，没有解除报警调用；调用方VisionAlarm在记录数据库后执行ResetAlarm，见既有uplookextra-alarm。

循环catch重新抛异常，没有finally保证isWork复位。若工作阶段在置true后抛异常，OK按钮中的等待存在无法在这段代码内解除的可能；这属于静态风险条件，不是已复现UI卡死。关闭等待只判断Running，不读取Task结果或Exception，也不是全状态等待完成。

## SetHardware确实执行什么

UpLookVisionByCode → System2Controller.SetHardware(name,UpLookCamera) → UpLookController.SetHardware → UpLookModule.SetHardware/GetHardware → PREntity.SetHardware。

- System2Controller只对BondCamera走BondModuleController，其余走UpLookController。
- GetHardware构造PRHardware：上视相机名称、焊头相关XYZ轴名称及点光/环光名称。
- PREntity.SetHardware赋CameraName/AxisXName/AxisYName/AxisZName，并扩展及写入PRLightList的LightName。
- 本次展开的设置链没有轴移动调用、没有曝光或强度设置调用；它是名称绑定，不是移动到CodeVisionPRPos。实际拍照DoWork及硬件属性getter内部行为不在这个结论内。
- UpLookModule.SetHardware没有对Find返回的PR或GetHardware中的硬件对象做null保护，缺失配置可能沿调用链抛异常；上层处理见上视DoWork catch。

## 异步关灯的精确条件

正常上视完成后Task.Run调用动作CloseLight。该方法查询P1和P2模板，单点取P1.IsFlash，双点取P2.IsFlash；只有选中模板IsFlash为true才调用UpLookController.CloseLight。后者先点光SetIntensity(0)，再环光SetIntensity(0)，没有本地try/finally。它不以CodeVisionPRName的IsFlash为判断依据。

因此不能概括为每次上视/读码完成都会关灯，也不能保证第一盏灯出错后第二盏仍关闭。选中模板和灯对象缺失、通知与后续拍照交错均需隔离验证。异步Task未被等待/观察的范围沿用此前专题。

## 精确证据

在[源码阅读器](module-source-explorer.html)搜索alarmhw前缀。路径相对trunk/AKRS.ZX2200，PR库另注明。

|ID|文件及行号|
|---|---|
|alarmhw-construct|Infrastructure/Controls/Currency/FrmVisionAlarm.cs:43–53|
|alarmhw-load|同上:273–331|
|alarmhw-worker|同上:135–185|
|alarmhw-ok|同上:339–408|
|alarmhw-abort|同上:415–419|
|alarmhw-close|同上:515–568|
|alarmhw-designer|Infrastructure/Controls/Currency/FrmVisionAlarm.Designer.cs:60–164|
|alarmhw-dispatch|BondSystem/Controllers/System2Controller.Vision.cs:822–832|
|alarmhw-controller|BondSystem/Controllers/UpLookController.cs:31–64|
|alarmhw-module-names|BondSystem/Modules/UpLookModule.cs:19–37|
|alarmhw-module-bind|同上:80–115|
|alarmhw-light|BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1353–1367|
|pr-runtime-hardware（复用）|trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs:165–180|

## 后续缺口

- 现场相机HardwareName、PR算法类型与各按钮配置对应关系。
- 报警后台线程异常注入、OK/关闭等待及异步关灯交错测试。
- ComponentCode数据导出/恢复以及激光检测调度按原计划继续。
- 外部硬件实现、完整图像采集流程和精度验收仍未完成，不将本专题计作全模块完成。
