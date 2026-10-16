# 就绪检查下层：S1配置、S2自检、吸嘴架与预点胶

更新：2026-09-28。承接production-domain-readiness-review.md；全部是静态源码核对，外部扩展方法、对象加载及硬件输入真实性仍需独立验证。

## S1三个IsReady

- DispenserProgram.Dispenser按DispenserName查仓库；IsReady先判null并提示false，再判示教完成。属性会再次查找，不是先缓存同一对象；不声称对并发配置变更有原子保护。证据readydeep-dispenser。
- PreDispensePlateProgram.IsReady直接返回DispenseDevicePara.GetInstance().PreDispensePlatePara.AssistanceFinish，没有在此检查板对象非空或区域大小；不能据此断言整个配置不存在其他校验。证据readydeep-plate-param、readydeep-plate-check。
- EpoxyMaterialProgram按名称查对象，IsReady只拒绝null，其余true；该方法未检查胶材ID、到期时间或耗材剩余量，其他后台检查另算。证据readydeep-epoxy。

## BondProgram.SelfCheck

先NozzleShelfProgram.SelfCheck，false短路；再遍历GetCarriers结果，逐项检查：吸嘴名称非null/空；贴片、取片、中转台取片、中转台放片各自处于Force模式时，其力值必须严格大于ForceControlMinVal且严格小于ForceControlMaxVal；等于边界也拒绝。

随后检查UpLook/Bond纠偏相机对应的P1VisionPos是否Equals(new AKRSPoint3D())；关真空延时大于PlacementDelay拒绝；已配置IPT且中转台关真空延时大于IPTPlacementDelay拒绝。并非所有参数的完整物理范围校验。证据readydeep-bond。

## 吸嘴架两种检查不能混同

- NozzleShelfProgram.SelfCheck先Any排除TouchDown和BMC后查未示教；报警选择FindLast只排除TouchDown，谓词不完全一致，提示名称可能与触发集合不同，取决于列表顺序。
- 后面源码写NozzleShelfSlots.Find(...OnBondHead).Count()>1，命中分支提示并throw。槽位字段是数组；此次未确定Find扩展绑定，保留表达式而不把它强行解释为LINQ Where或普通List.Find。不凭该文本宣称已保证最多一个焊头吸嘴。证据readydeep-nozzle、readydeep-slots。
- CheckToolBankConfiguration在IsToolBankEnable=false时true；启用时固定访问槽位[0]到[6]，各槽只有“配置名为空且对应传感器为true”时拒绝。不是双向的一致性比较，有名称但传感器false不在这些if中拒绝。
- NozzleShelf构造调用CreatNozzleShelfSlots，数组长度由NozzleShelfParam.SlotNum决定。七槽位检查本方法没有长度保护；若数组少于7且执行到超界索引会抛异常，而非false。实际保存数据、参数限制和输入分支需测试，不断言当前设备配置必然越界。证据readydeep-toolbank、readydeep-slots。

## S2动作列表和预点胶

- S2ActionNodeController.SelfCheck拒绝ProcessSteps=null或Count=0；普通TU检查每步焊点名非null/空且存在，异形TU跳过这段foreach。ProcessSteps的生成/筛选不是本方法的功能，不据此推断它等于原始工艺列表。证据readydeep-s2steps。
- S2PreDispenseActionNode.IsAlarm：未配置S2点胶直接false；配置后先读取Dispenser.PreDispense，仅在Mode与Timing都Off时false；任一个开启就继续。该方法在读取这些嵌套属性前没有Dispenser null判断。
- 然后依次：点胶头未示教、胶型名null/空、S2预点胶板IsReady=false，任一提示并返回true；否则false。本方法没有像S1域那样检查胶型名称是否存在于胶型列表；S2板IsReady实现仍需核实，不能套用S1板结论。证据readydeep-prealarm、ready-s1。

## 交接待办

- [ ] 找到数组Find扩展绑定及实现，核实焊头吸嘴计数表达式语义。
- [ ] 核对SlotNum保存/加载约束及1–6、7、超过7槽位配置的隔离测试。
- [ ] 展开S2预点胶板IsReady、ProcessSteps生成筛选。
- [ ] 关联校验异常与启动UI的Stop处理及已发生副作用。
- [ ] 本轮没有修改业务源码或执行硬件测试。

## 源码证据

- [readydeep-dispenser 30–80](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/DispenserProgram.cs#L30) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-dispenser)
- [readydeep-plate-param 26–43](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs#L26) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-plate-param)
- [readydeep-plate-check 200–203](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs#L200) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-plate-check)
- [readydeep-epoxy 20–65](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyMaterialProgram.cs#L20) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-epoxy)
- [readydeep-bond 85–211](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L85) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-bond)
- [readydeep-nozzle 224–255](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs#L224) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-nozzle)
- [readydeep-s2steps 1359–1404](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1359) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-s2steps)
- [readydeep-toolbank 73–179](../../trunk/AKRS.ZX2200/BondSystem/Controllers/NozzleShelfController.cs#L73) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-toolbank)
- [readydeep-slots 26–59](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/NozzleShelf/NozzleShelf.cs#L26) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-slots)
- [readydeep-prealarm 211–260](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs#L211) · [源码阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=readydeep-prealarm)
