# ZX2200 耗材寿命与提醒源码复核

日期：2026-10-27。对应清单37.01–37.04。依据只读trunk/AKRS.ZX2200，区分当前接入的耗材、模型公式、扫描门控、编辑复位和保存；不运行设备或真实耗材寿命验证。

## 01 汇集对象与实际接入

- 每次ScanConsumables先重建列表，依次加入S1胶水、BondProgram时间耗材、当前吸嘴架工具和当前顶针库。没有按Enable过滤，禁用由各模型判断时返回false。后台汇集与窗口入口均未调用GetFlipToolFrequencyList；翻转工具虽有Frequency字段和按当前工具返回/去null/Distinct的接口，不能画成已经进入这条提醒主链。ConsumablesProgram.cs:36–58,72–79；UcMainSystem.DataAdministrator.cs:120–138；FlipModuleProgram.cs:44–55；FlipTool.cs:90。
- S1胶水要求IsSystem1Configrated且当前胶水实体非空；空寿命对象会补建TimeConsumable，名称同步为胶水名。S2胶水要求IsSystem2Dispense；助焊剂要求IsSlideFluxerConfigured，空对象补建并命名。时间对象属于胶水实体或SlideFluxerProgram，胶水程序本身按名查仓库。System1Program.cs:66–86；BondProgram.cs:227–259；EpoxyMaterialProgram.cs:25–32；EpoxyMaterial.cs:29；SlideFluxerProgram.cs:34。
- 吸嘴按当前架非空名称列表查仓库，缺实体跳过，Frequency为空或名字不匹配则新建、加入并调用BondProgram.Save；此处不是NozzleRepository.Save。顶针按当前库槽的EjectionConfig取Frequency，空或名不匹配时重建并调用EjectionBankConfigRepository.Save，末尾按对象Distinct。名单和Enable不同：即使未启用寿命报警也可在名单里。NozzleShelfProgram.cs:170–196；EjectionBankProgram.cs:57–81。
- NozzleRepository.GetFrequencyConsumables还有按当前配方列实体的接口，但当前后台和窗口用的是吸嘴架接口。Dispenser也有DispenseTimes次数对象，点胶头编辑器能修改其开关与总数；当前汇集未加入它，主程序直接引用检索未定位到它的CurrentUseTimes递增。翻转Frequency亦未检出直接递增引用。保留这些定义/接口与接入状态的区别，不扩张到未知外部代码。NozzleRepository.cs:116–125；Dispenser.cs:83–93；UcDispenser.cs:167–175,217–227；本地direct-usage-search.txt。

## 02 次数公式与递增

- FrequencyConsumables总数、当前数、提醒值均为int，默认分别10000、0、90。Enable=false时到期和提醒均false；到期严格CurrentUseTimes>TotalUseTimes，等于总数尚未到期。IsRemind比较的是(Current/Total)>(Remind/100)，两个除法都是整数除法，不能解释成正常浮点百分比；Total为0没有在此保护。FrequencyConsumables.cs:15–84。
- 假设总数100、提醒90且已启用：当前90时0>0为false，当前100时1>0为true。这只是模型计算例，实际弹窗仍受到期优先级、冷却和IsReminded门控；不是90%就会预警的证明。参数模型未加额外值域校验。
- 非离线、非DryCycle的BondAction到达尾部，在工艺完成标记和统计后增加当前吸嘴CurrentUseTimes，之后仍有上限检查与UI刷新；不以Enable门控。顶针从取片分支的AddCountOfUseable调用增加，发生在后续漏晶检测前，控制器只以未屏蔽顶针模组为条件，也不以寿命Enable门控。BaseCarrierConfig同名方法增加的是物料CountOfUseable，不是顶针Frequency。BondActionNode.cs:125–141,343–364；PickActionNode.cs:337–371；EjectController.cs:1059–1064；BaseCarrierConfig.cs:1051–1053。不能把任一计数笼统称为所有成功取贴次数。

## 03 时间公式

- TimeConsumable开始时间默认DateTime.Now，寿命为分钟，默认1440；DueDate=StartDateTime.AddMinutes(UseDateTime)。到期比较Now>DueDate，提前提醒比较Now>Start+截整分钟(UseDateTime×RemindTimeRate/100.0)，默认比例80。停机或禁用不改变这段墙钟公式，Enable只让到期/提醒查询返回false，不会暂停或重置开始时间。TimeConsumable.cs:14–88。
- GetRemainingTime将DueDate−Now的TotalMinutes强转int，向零截断；剩余显示0不能单独证明已到期或未到期，颜色另调用到期/提醒判断。Current时间在各调用中分别获取，未按同一采样时刻统一快照。TimeConsumable.cs:95–98；UcTimeConsumable.cs:78–115。
- EpoxyMaterial仍有旧寿命/预警字段，但当前扫描使用嵌入的EpoxyMaterialConsumable，不由旧字段名推导当前公式。EpoxyMaterial.cs:29,45–110。

## 04 后台调用与扫描分派

- 主窗初始化加载后启动Machine.StartBackGroundThread；后台线程存活则不重复创建，循环条件为RuntimeProvider.ThreadFlag。每轮顺序做安全门、编码器、自动退出、温度、耗材等任务，最后Sleep(100)。ConsumablesProgram.BackgroundConsumable只同步调用ScanConsumables，它自身没有启动独立扫描线程；不能把100ms停留当成精确周期。此循环本段没有只在生产运行时扫描的门控，也没有围绕耗材扫描加独立catch。MainForm.cs:244–257；Machine.Operate.cs:662–700；ConsumablesProgram.cs:64–114。
- 对每个非null对象，先判断IsExpired()&&IsEnableTimeToAlarm()。满足时先置IsReminded=true、LastAlarmTime=Now，再同步显示到期提示。忽略只继续；停止调用Machine.Stop后直接Clear，不等待更换确认，也未在这段追加Save。否则进入IsRemind()&&!IsReminded，显示提前提醒后置true；即使已经到期但冷却未过，语法上仍会落到这个else-if，而非统一直接跳过。ConsumablesProgram.cs:72–113。
- BaseConsumable第一次报警门控把IsAlarmed置true并立即允许；以后仅在Now−LastAlarmTime严格>10分钟时允许。实际LastAlarmTime更新由扫描到期分支完成。IsReminded是提前提醒的一次性标志，不是到期报警的唯一门控；到期分支不受它阻止。BaseConsumable.cs:14–67。
- 提示在同一后台线程同步调用，等待提示返回会延后下一项、后续监控任务与本轮末尾Sleep。模型计算或列表构造异常也没有由ScanConsumables自身统一吞掉，不能把后台始终正常刷新当作已验证事实。

## 05 窗口与编辑

- “使用耗材”菜单首次或旧窗Disposed时构造FrmConsumables，传当前吸嘴、顶针、合并时间对象和额外flux参数；窗口未销毁则复用，列表在构造时传入，Load中绑定与初始化。它与后台每轮重取列表不同，不能声称打开后随配置切换自动重建所有卡片。UcMainSystem.DataAdministrator.cs:120–138；FrmConsumables.cs:28–34,78–125。
- 固定卡片为7个工具、5个顶针、2个时间对象，InitData按传入Count直接索引，未限长或动态扩展。若时间列表超过2项会超过卡片数量。第四个flux参数存入字段却没有单独绑定；但助焊剂若已由BondProgram加入合并时间列表，仍可能占用时间卡，不能据此说助焊剂完全不显示。FrmConsumables.cs:28–55,87–125。
- 窗口Timer为500ms，刷新所有固定控件；没有对象则Refresh隐藏控件。次数控件绑定TotalUseTimes，显示当前数、Enable并设灰/红/黄/绿，当前次数编辑框禁用，清记忆按钮直接Clear，开关直接写Enable。这里不提供RemindUserTimes编辑控件，没有显式Save或取消回滚入口。UcConsumables.cs:28–99及Designer:40–105；FrmConsumables.Designer.cs:327–340。
- 时间控件可修改总寿命分钟、开始时间与Enable，开始时间编辑会清IsReminded；改寿命和开关未在处理器中重置提醒标志。到期与剩余显示禁止直接编辑，清记忆直接Clear。初始Refresh之后才订阅开始时间变化事件；同窗颜色按实际模型结果刷新，没有独立修正整数提醒算法。UcTimeConsumable.cs:24–158及Designer的Click/CheckedChanged/EditValueChanged绑定。

## 06 复位与保存

- 次数Clear只清CurrentUseTimes和IsReminded；时间Clear只把StartDateTime设Now并清IsReminded。两者均保留Enable、限值、IsAlarmed和LastAlarmTime。清记忆、到期停止分支和同对象开始时间编辑不能视为同时重置全部报警冷却状态。FrequencyConsumables.cs:38–42；TimeConsumable.cs:46–50；BaseConsumable.cs:47–67。
- S2点胶助手正常完成的尾部可提示是否重置胶水有效期与点胶头次数，确认后分别Clear。清零发生在前面的Save调用之后，随后没有追加同样的仓库Save。S1换胶助手上一专题记录的完成主链没有这两处Clear调用；普通换嘴也不能自动等同于寿命归零。FrmAssistantDispense.cs:372–388；本轮直接引用检索及31/32公共专题。
- 点胶头编辑器确认会把DispenseTimes.Enable/TotalUseTimes和胶水TimeConsumable.Enable/UseDateTime写回，再Save DispenserRepository和System1Program；这一处没有直接EpoxyMaterialRepository.Save。胶水程序按名查仓库实体，不能把保存程序选择名当成已确认胶水仓库完成相同持久化。UcDispenser.cs:217–233；EpoxyMaterialProgram.cs:25–32。
- 耗材窗口的编辑/清零与扫描停止分支没有独立Save；主界面保存和Machine.DataSave另顺序调用顶针库/顶针、翻转、吸嘴、BondProgram、S1程序、点胶头及胶水仓库Save，退出也调用DataSave。各对象保存是独立调用，不能当作跨仓库事务。UcMainSystem.cs:632–690；Machine.cs:352–410；Machine.Operate.cs:706–712。

## 07 本轮边界

本记录先固定源码事实；正式图谱、逐项绑定与浏览器验收完成前，37.01–37.04继续pending。未运行设备、耗材实际寿命、真实到期提示或仓库写入验收。原45专题241条范围继续保留。

本批35个引用文件、42段拟绑定范围均属于当前1,137个Compile项，对照1,157个C#原件指纹一致；审计在 output/functional-atlas/consumables-source-audit.json。直接次数/汇集引用与提醒复位检索结果在 consumables/ 同名输出目录，正式业务数据未改。

## 08 图文与页面验收

形成7个阅读环节、24节点，使用真实Archify横纵图各8节点7关系，四个原始交付检查均通过、无诊断与交叉提示。汇集七行与复位四行集中对照；已有工具更换、手动维护专题用链接复用，S1换胶和普通换嘴未调用同样寿命Clear的完成边界另引用已核对的公共依据。37.01–37.04逐项绑定后累计74/241，167条保留原范围。

图谱变更阶段完整前端361项通过；最后措辞和表格调整后的相关35项通过，源码/资源、TypeScript与最终构建通过。未采集覆盖率，未执行后端单元或设备寿命/精度验收。原主程序1,157个C#指纹一致。浏览器逐项切换24节点，并目视1280px与497px的主图和两表，使用普通页面滚动。最后的更换差异文本和缩短表格单元另在固定候选构建复查；日志、截图和逐项审计均在 output/functional-atlas/consumables/。

8765在本轮页面验收期间由其他部署重启，旧会话失效，后续共享dist又发生变化。最终浏览器验收改用仓库现有隔离工具，在独立临时数据目录的普通测试账号下正常登录，并以18768预览固定候选构建、18767提供隔离API。没有读取正式密码或用测试账号访问正式数据库。当前正式服务对新入口脚本仍返回401，启动时静态白名单需与最终构建统一同步；因此本记录只确认图文和隔离页面验收完成，不宣称8765最终发布验收通过。该部署收尾仍需后续复核。
