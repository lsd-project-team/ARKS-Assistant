# 原S2动作的步骤提交与生命周期边界

两个全新 Framework CLR 宿主各31个不同断言通过。每轮使用原仓库对象、原排序和公开更新的9个新TU上下文，每个上下文19条消息；没有启动原完整生产Task。本轮29原IL方法、20源码哈希、16保真源程序集，父5814+新增72=5886冻结绑定。

## 原排序及明确fixture

公开配置单基板、单模块、单BP，真实原组件仓库加入公开BaseCarrierConfig（使用翻转台、精度后蘸胶），真实焊后检测仓库加入PostBondInspection，公开CurrentNozzleName=TouchDown解析真实默认工具。原BondPositionFirst/StepFirst排序对同一步按组件→检测→点胶互斥优先：chip同时含检测/点胶名，实际只生成Pick/UpLook/Dip/SubstrateCamera/Bond五动作；inspect含点胶名只生成AfterBond。

每次通过原UpdateTransportUnit、Init、InjectSteps重建4实体TU；前序消息由公开FinishCurrent跳过，没有执行前序动作。私有WorkMessages只读观察，没有写入私有消息/实体/单例或替换动作、SDK、源码。离线、Stop、Belt、SafeDoor关闭，实际硬件文件缺失/SDK仓库空；刮胶盘配置true只为通过蘸胶条件，并无真实刮胶盘。系统2点胶配置false。

|直接原动作|实际观察|步骤/消息|
|---|---|---|
|Pick / OffLine|Success在生命周期try/finally之前返回；WorkStart/Stop均0，State未变|chip仍false、当前消息未完成；公开FinishCurrent单独提交消息|
|Bond / OffLine|先WorkStart/Running及准备，再离线判断；原GetAxisZAbsoluteSpeed缺轴自然NRE|chip未完成；原catch走UI分派fixture异常，finally Stop/WorkStop运行|
|AfterBond / OffLine|原Success及finally刷新|inspect已true，消息仍未完成；IsDoWork随后false|
|AfterBond / 频率跳过|Compensate/Stop直接调用，计数0→1，阈值10；Success|inspect已true，未触硬件，finally刷新|
|Dip / 已配置、Stop|原允许蘸胶信号Wait失败，Abort|chip仍false，finally Stop，无硬件/报警|
|S2PreDispense / 禁用|即使IsManual=true，原判定先返回不点胶；DoWork Success|finally清manual、Stop，LastDispenseTime不变|

原Bond的缺轴在离线判断之前；另以闭合Action绑定原PrepareBeforeBondAction真实接收者，实际NRE栈包含GetAxisZAbsoluteSpeed/PrepareBeforeBondAction。没有给它返回值替身。原Bond catch调用Ext.Show；公开MainForm.SendUiAction只读收集原Action文本后抛同一InvalidOperationException，在原直接DBService.Insert之前中断。每轮收集1个、执行0个，DB Lazy始终未创建。Task未执行；这不是原UI正常选择/SQL或成功贴片。

## 焊后检测的提交与回调故障

原AfterBond频率关闭/离线分支先S2FinishedStep，finally先清IsEditTest/StateStop和WorkStop，再无条件调用ReFreshSystem2TuAction。实际未赋值的null刷新自然NRE覆盖Success，但步骤已提交，WorkStop已执行。公开WorkStart抛同实例发生在Running/try之前，finally不运行、步骤仍pending、State保持前值；公开WorkStop抛同实例发生在步骤已提交/StateStop之后，阻止最后刷新。三种不同故障边界均以新上下文执行，没有用私有写恢复步骤。

频率跳过只检验count0、threshold10的首个跳过，不涵盖到达阈值或真实视觉/测高。Compensate下保持Stop直接调用，与原整任务调度无关；收尾先恢复OffLine再原Stop，避免额外硬件路径。

## S2点胶直接调用范围

实际S2Dispense.IsDoWork在OffLine=false，原Task不会按这一条件执行本动作。本轮明确直接调用DoWork绕过这个false，仅核对原内部守卫：一个测试线程实际进入单步等待；原Machine.Stop关闭singleStep后返回Abort，未调用预点胶、epoxy步骤仍false。下一次Stop/非单步直接调用第一次WaitStart=false→Fail；Working直接调用禁用的原预点胶，其公开WorkStop调用原Stop后，第二次WaitStart=false→Fail。两次Fail同样未提交epoxy，没有S1式提前提交。

单步调用通过原System2Domain.WaitSingleStep包装到原Signal.WaitSingleStep；29个原IL包含该包装及两个WaitStart调用。全部测试线程已join，原BondTask.BondWorkTask保持null。这些Abort/Fail没有被写成整Task调度成功、物理点胶或完整退出。

## 验证记录及剩余

首次编译缺ActionNodeMessage命名空间（原类型在AKRS.ZX2200.Services），98b29d失败输入/诊断/零字节emit保留且未执行CLR；修正后7fb0d0原生31检查通过，7a9ec5独立重编译/replay31通过及原IL只读提取。emit SHA相同、固定标签与结果一致，不声明整个stdout字节一致。初次预检错将包装调用预期为直接Signal，55ed8c失败后保留原检查器/IL；修正前shell脚本语法失败adcd5f未改源码。修正实际调用及补取原包装IL后65d343预检/冻结/绑定验证通过。

162引用中10直接源引用，runtime-map172项；两轮各16源程序集从实际bound/replay路径加载。父原S2清零与保真资源80811/b611c9顺序通过。没有生产C#/工程修改、私有写、硬件动作/轴/真实相机/贴片/UI/SQL、完整MSBuild/部署。正式1328、旧40专题3817及主阅读器保持冻结。继续真实依赖下的S2动作成功、清零正常结果、补偿/输入/整任务与Retry、完整输送握手和构建设备验收；16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-s2-action-boundaries-test.json)、[审计](native-s2-action-boundaries-audit.json)、[进度](native-s2-action-boundaries-progress.json)。
