# ZX2200 清嘴排胶与手动维护源码复核

日期：2026-10-27。对应全量清单32.01–32.04。依据只读trunk/AKRS.ZX2200，区分参数、入口、动作请求、返回、记忆状态与保存，不执行设备动作。

## 01 取晶前触发

- 非离线取晶在准备和换嘴成功后调用JudgeAndCleanNozzle，再进入DryCycle分支；因此不能把DryCycle解释为自动略过清嘴判断。开关关闭不计运行次数；开启先要求左上角点非空，运行次数达到CleanNozzleAfterPickupNum才调用CleanNozzle。清洁方法返回后，按晶圆相机避让辅助判断请求安全位，运行次数清零，再加一。这个计数按进入分支更新，不是取晶成功数量。PickActionNode.cs:160–182；PickActionNode.Provider.cs:146–172。
- CleanNozzleProgram含开关、每轮清洁次数、清洁间隔、距离/力模式、清洁力、单点使用上限、行列、使用总次数和CleanZCompensation字段。当前CleanNozzle方法没有读取CleanZCompensation；运行计数另为System2RunTimeProvider静态字段，不能与区域Count混为一个值。CleanNozzleProgram.cs:31–91；System2RunTimeProvider.cs:148；字段引用检索见本地审计。

## 02 区域构造与占用

- InitCleanTable每次以左上/右下点构造Row×Column数组，间距分别除以Row、Column，不是减一。X随列增、Y随行减，全部Z取左上角Z。它先计算间距/分配数组，再拒绝行列<=0，最终Save BondProgram；不能把这段描述为端点都包含的网格或事前完整输入校验。System2Controller.cs:1136–1170。
- GetCleanPos每次先InitCleanTable；Count达到总点数×单点使用限时提示更换并直接清Count为0。占用点序号=Count/单点限，列=序号/Row、行=序号−列×Row，逐列分配；随后Count++、取点并保存BondProgram才返回。使用限0没有在此防护；负数Count和超界也无统一校验。取点即占用并保存，后续清洁失败或尚未真正动作不会回滚此计数。System2Controller.cs:1098–1130。
- 实验面板名为工具架重复测试的按钮仅调用GetCleanPos，实际可能重建/推进/保存清嘴区域，没有执行擦拭或原来注释中的重复运动；前31专题已单独标明。UcBondModuelSetting.cs:1596–1608。

## 03 清洁动作

- CleanNozzle先要求配置清洁台，取当前工具，再取并转换清洁点。清洁高度=机械清洁Z+工具MeasureHeightOffset，按工具AlignAngle转T；先安全Z、XY，再到清洁高度+2。方法没有显式当前工具null保护，运动返回值也没有逐个门控。System2Controller.cs:1176–1195。
- 每轮距离模式按速度100下到清洁高度再抬+2；其他模式调用ForceControlSet(force,height,100,10,2)，然后ForceControlReset(height+2,100)。次数<=0会跳过这段循环，但此前区域已经占用，之后仍请求安全Z并吹气。最后开ToolBlow、等待50ms、关吹气；没有统一finally处理异常后的输出/运动恢复，也没有额外的清洁质量检测。System2Controller.cs:1197–1223。完整力控与安全运动复用已发布公共专题。
- 无参OpenToolBlowEle受单步门控，先按焊头真空状态关闭焊头真空并等50ms，再开弱吹；带比例重载按工具真空状态检查，关闭的是焊头真空输出，并在比例不同才设置/等50ms，没有同样的单步代码。CloseToolBlowEle只在输出已开时关。调用吹气的正常返回不能代替实际清洁或抛料结果。BondHeadController.GasIORelated.cs:72–120,181–188。

## 04 吹气盒、抛料与持晶记忆

- ThrowAction读原比例，转换G0抛料位并请求MoveSafeBondXYZ，再按抛料比例开吹、等ThrowBlowDelay，恢复原比例、再次等同一延时，关吹并请求安全Z。最后清IsMaterialOnBondhead，统计AbandonNumber加一并true。检测残留料的代码被注释，移动的返回值未门控，没有统一finally恢复，不能把清记忆或true当成传感器已证实无料。BondModuleController.MovementRelated.cs:806–856。
- 快捷抛料入口先要求机器停止，调用后另去安全位；模块菜单区分只移动到抛料位、抛料、清理吸嘴。ClearHead仅设置抛料比例、等20ms、直接开弱吹500ms后关，没有移动到抛料位、恢复原比例、检查物料或更新持晶记忆。UcShortcutMenu.cs:506–513；UcModule.cs:248–278；BondHeadController.GasIORelated.cs:24–30。
- 客户设置可打开吹气盒示教。提示在配置刮胶盘时强调上视到抛料盒的直线路径，但本窗没有由提示自动做避障规划。在线Done把当前机械位置转换G0写ThrowPos并保存设备参数；离线Done仅OK，取消确认后关闭。手动吹气根据按钮颜色切换，开启先设置比例并等50ms；关闭窗只释放移动控件，未在该关闭处理器统一关吹气。FrmCustomerSetup.cs:102–107；FrmBlowOffBoxAssistant.cs:61–160。

## 05 S1 手动挤胶与预点胶

- 主界面手动点胶菜单打开UcDispenseManual。挤胶按钮切换输出，开启时用设备示教压力及0负压调用设压，然后OpenDispensingElectric；此按钮处理器本身没有快捷菜单同样的IsStop判断。定时器离线不更新显示，打印工具按钮按硬件配置启用。模块内部输出与压力通讯另由对应接口实现。UcMainSystem.Manual.cs:166–174；UcDispenseManual.cs:48–109,181–201；DispenseController.cs:827–861。
- 面板预点胶仅在Mode==Off时拦截，否则置IsManual=true并DoWork，未消费DoWork返回值；快捷预点胶先要求停止，S1分支以Mode与Timing均Off才拦截。快捷换胶和预点胶还按当前工位/硬件分到S2，不能把所有入口合并成相同门控。UcDispenseManual.cs:163–174；UcShortcutMenu.cs:359–417。
- PreDispenseAction在try内先判断是否应执行，手动直接执行；自动还支持首料前或时间间隔条件。然后检查点胶头存在且示教完成、图案名非空、板AssistanceFinish；失败Abort。可选EpoxySqueeze依次设压、到挤胶位、开阀/等待/关阀、到擦胶位，没有在此统一finally关输出。PredispenseAction.cs:74–93,177–278。
- 执行前一次性取RepeatPreDispensing个板点，逐个取点已递增保存Index；空列表抛错。逐点调用插补，DryCycle传isDrip=false，插补非Success即Alarm。配置后检测对象时调用CheckEpoxyApplication，但该返回值未被上层消费；没有对象且手动时移动到末点视觉位置。正常尾部刷新LastDispenseTime；catch Exception返回Exception；try的finally清IsManual、置Stop并通知WorkStop。PredispenseAction.cs:98–168,287–296。

## 06 板上试胶与点列重置

- “清洁预点胶板”实际调用InitPre：按首末点和(rows−1)/(columns−1)间距建数组，单行/列间距0，置Index=0并保存System1Program，没有在该方法执行物理擦板。GetEpoxy在数组空时初始化，Index恰等于总数时DryCycle自动重建，其他模式要求人工确认或抛错；尺寸变化也要求确认重建。每次分配按行优先推进列，先Index++，取点/Save后返回。IsReady只返回AssistanceFinish。PreDispensePlateProgram.cs:55–202；UcDispenseManual.cs:143–146。
- 图案编辑的板上试胶先Confirm、置IsFirstDispense，再按当前工位与硬件分S1/S2；S2打印还验证工具存在且完成并换嘴。S1要求点胶头和板完成，先GetEpoxy，再以isDrip=true、isPrePlant=true直接调用插补，没有使用该返回值门控后续安全Z和末点视觉位置。它与手动PreDispenseAction的DryCycle出胶参数、批点/后检测和返回消费不同。UcEpoxyApplication.cs:968–1079。轨迹算法、S2工艺和完整后检测分别留在25、26、28专题。

## 07 清洁台与板面示教

- 客户设置的清洁台入口先检查清洁台硬件开关，再ChangeTouchDownAssistance，失败不打开窗。三步记录左上/右下G0，再按焊头安全Z和TDSensor测高；只有测高Success才给两角写同一G0高度，输入行列，接受>=1（提示文字却写大于1），保存设备与BondProgram。外层Done无论回调是否成功或离线早退，仍Save设备并OK。取消不统一回滚已写内存；FormClosing始终请求PutbackNozzleAssitance，其返回值未消费。FrmCustomerSetup.cs:133–154；FrmNozzleCleanPosTeach.cs:90–205,267–301。
- 预点胶板助手Load固定CurrentMachineSystem=S1、type=TouchDown，并到安全位、开测高气缸。激光硬件只在此改变提示文案；实际该type经公共助手进入S1 HeightSensor接口，具体测高共用29专题。测高失败设置Abort后同一回调仍继续构造相机位；不能画成所有后续语句已立即停止。首末点临时保存，Done对行列TryParse并取绝对值，未排除0；写同一高度、Rows/Columns和AssistanceFinish=true保存设备，再关气缸、安全位、InitPre重建/保存程序。FrmDispensePlateAssistant.cs.cs:96–276,310–356；TUAssistantHelper.cs:302–326。
- 面板的板助手调用在ShowDialog返回后无论结果都另关气缸、去安全位；助手自身Cancel/Closed只关闭/释放控件，不执行同样的所有收尾。与清洁台外层Done不同，板助手BtDone调用回调后只Close，没有无条件设OK。UcDispenseManual.cs:118–124；FrmDispensePlateAssistant.cs.cs:310–356。
- 板面到传感器距离助手记录两次机械Z，距离=第一次−第二次，仅(0,1]有效；无效Abort并返回，有效写DistanceInSensor/Save并去安全位，没有外层覆盖Abort为OK。传感器灯显示独立读取，Done没有再次以信号值门控。取消关闭，Closed只退订/释放计时器。FrmAssistantPreDispenseDistance.cs:87–158,214–250。

## 08 换胶七步与保存取消

- FrmChangeEpoxy.Load设置当前工位S1；缺点胶头设置Abort但没有立即return，非离线请求安全位后继续初始化。七步依次移动到换胶位、更换胶桶、挤胶、擦胶、蘸胶、测高试胶和视觉对齐；普通点胶头在擦胶之后额外递增步骤索引跳过蘸胶步骤。实际数组和外层Next都推进索引，不能按提示中重复的步骤编号推导执行。FrmChangeEpoxy.cs:53–73,141–335。
- ReplaceGluePosition、ThrustPosition、ErasePosition、PrintingToolPos和DispenserMeasureHeightPos在各步Next就写当前G0并分别保存。测高失败内部stepIndex--抵消外层++，留在当前步骤；成功以测高高度加DistanceInSensor试胶，非离线设压/开阀/等示教时长/关阀，随后按旧针偏移移动观看，移动异常提示手动调整。FrmChangeEpoxy.cs:201–400。
- 最后Done记录观看G0并计算针偏移，Z还使用板高与G0视觉零点；可选清整体点胶偏移，然后分别保存System1Program、设备和点胶头仓库状态（DispenserAssistant.Able）。外层再请求安全位、OK并将当前工位改为S2。取消仅DialogCancel，关闭仅释放计时器/移动控件，不撤回中途保存，也不在同一关闭处理器复位工位或统一关闭挤胶。ClearPosition只清六个设备位置内存，方法自身未Save。FrmChangeEpoxy.cs:415–458,479–602；DispenseDevicePara.cs:78–85。

## 09 本批验证范围

本记录先固定源码事实。正式图谱、逐项绑定、实际Archify图及页面验收完成前，32.01–32.04继续pending。未运行ZX2200设备、驱动、排胶、测高或清洁质量验证；原45专题241条范围继续有效。

本批已审计36个主程序文件，58段拟绑定范围，按Windows路径忽略大小写均在当前1,137个Compile项中；对照1,157个C#原件基线，指纹一致。读取范围、编译归属及指纹在 output/functional-atlas/manual-maintenance-source-audit.json。正式业务数据未改。
