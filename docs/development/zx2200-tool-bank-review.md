# ZX2200 工具库与吸嘴更换源码复核

日期：2026-10-27。对应全量清单31.01–31.05。业务原件位于只读 trunk/AKRS.ZX2200；本记录固定主程序实际入口、状态、条件和返回，不执行设备动作。

## 01 工具、槽位与当前工具

- Nozzle 保存名称、类型、尺寸、形状、几何、偏移、对中角、测高配置、SlotIdentification 和三项示教状态。槽位编号默认−1；PR名称由工具名加 NozzlePR 构成。IsAssistantSucceed 要求高度、对中、几何三项均非空且不为UnAble。Nozzle.cs:49–179,202–269。
- NozzleRepository.GetNozzle 只按名Find。Init 在缺失时建立 TouchDown、BMC 两个 Calibrate/Small 系统配置，初始测高偏移为0；该Init自身没有Save。当前工具名来自 BondHeadParam.CurrentNozzleName，CurrentNozzle 再按名查仓库；SetCurrentNozzleName 写名后立即Save设备参数，并不同步全部槽位。NozzleRepository.cs:47–50,77–110；BondHead.cs:130–140；BondHeadController.cs:870–935。
- NozzleShelf 以槽位数组保存 NozzleName、NozzleType、最大尺寸和State。Index从0、SlotNum从1，位置读取设备参数 PlaceNozzlePos[Index]，工具通过名字取仓库对象。构造过程按SlotNum重建小号空槽，覆盖字段初始化中的交替大小预设。NozzleShelf.cs:29–58,190–239。
- IsOnToolBank 只检查名字是否出现在槽位；GetPickPos/GetPlacePos 按首个同名槽取得数组位置，分别加Z距离、减Y距离，无匹配返回零点；角度无匹配返回0。程序的当前槽按OnBondHead状态找，GetToolOnBondhead 会在多个OnBondHead时抛错，不能把它与设备当前名视为同一事实。NozzleShelf.cs:66–159；NozzleShelfProgram.cs:131–164。
- SelfCheck 拒绝未完成工具，判定排除TouchDown和BMC，但警告选中项仅排除TouchDown；另检查多个OnBondHead。CanWorkProperly只看架对象EditState，未在该属性中加null保护。NozzleShelfProgram.cs:74–83,224–255。

## 02 库配置与编辑

- 产品编程的工具架配置打开 FrmNozzleShelfSetting，当前配方工具池排除已经放入所选架的名称。分配要求空槽和选中吸嘴，写槽名、工具SlotIdentification和OnSlot；取消分配写−1、清名并置Empty。这两个按钮先改共享内存对象，未在各自处理器中Save。UcEditProductProgramming.cs:1359–1362；FrmNozzleShelfSetting.cs:62–137,251–308。
- 保存分别写 NozzleRepository、NozzleShelfRepository 和BondProgram；取消只设置DialogResult.Cancel，没有看到统一回滚。删除按钮移除当前配方归属并保存吸嘴仓库，不等于全局删除实体。刷新遇到仓库缺失名称会清槽名与状态。FrmNozzleShelfSetting.cs:234–244,315–399。
- 新建可JSON深复制参考吸嘴，再改名、尺寸、形状、创建时间、配方归属并Add/Save，未显式重置复制来的示教和槽位字段。名称变化处理器禁空名、已有同名、BMC/TouchDown及非法文件字符。FrmNewCreateNozzle.cs:50–108,115–155。
- UcNozzleEdit 初始分别读取XY/Z选项，但Save把XYDeterminationMethod也赋自Z控件；AfterBondingVacuumCheckDelay来自焊后真空阈值控件。真空采集按钮开ToolVacuum、等1000ms、读值、关真空，再确认保存全部编辑字段。不能按控件标题推断已正确写入对应字段。UcNozzleEdit.cs:24–130。

## 03 工具库位置示教

- 主界面客户设置打开 FrmCustomerSetup；工具架示教按钮实际创建 FrmLearnToolBank，旧 FrmLearnNozzleBank1 的创建语句被注释。客户按钮及新窗Load/Next/Done事件在Designer中绑定。UcMainSystem.cs:789–800；FrmCustomerSetup.cs:63–77及Designer:184–195；FrmLearnToolBank.Designer.cs:346–385,546–547。
- 新窗构造先初始化并在非离线状态回T轴。Load输入槽位数量，仅TryParse整数，未限制至少2或上限；空输入未赋值，不能视为完成有效槽位设置。FrmLearnToolBank.cs:129–138,542–569。
- 五步为工具架Y换嘴位、首槽放嘴、首槽取嘴、末槽放嘴、末槽取嘴。首槽放嘴步骤以当前焊头G0和工具架实际Y创建/初始化 ToolBankCoordinateSystem，写ToolChangePosition；以当前Z+7检查软限位，实际写ChangeNozzleSafePos.Z为当前Z+6，然后保存坐标目录。FrmLearnToolBank.cs:151–245。
- 首末取/放点分别记录G0位置和T角。末槽放嘴中间检查读取旧PlaceNozzlePos[6]与[0]；最后Done回调才比较本轮lastPlacePos.X与firstPlacePos.X。有效尾部线性插值四个点/角度数组，槽距=(lastPickX-firstPickX)/(slotNum−1)，写SlotNum后保存设备参数；并未在此重建已有仓库的槽位对象。GeometryService对数量<=0返回首点数组，数量1仍进入除以0的计算，不把这当作数量校验。FrmLearnToolBank.cs:251–412；GeometryService.cs:254–296。
- Done回调保存后关焊头真空、请求换嘴安全高度、工具架回位和模组安全位，清当前工具名。外层BtDone不检查回调结果，仍Save并设置OK；即使最后回调因左右关系返回也会到外层。取消只关闭窗口，已在中途保存的坐标不回滚。FrmLearnToolBank.cs:338–368,447–485。
- 旧示教窗仍有按首末视觉点/6构造7槽、旋转工具偏移、取放Z差及ToolBank坐标创建的实现；本轮只将它列为独立旧实现，未在主程序找到有效直接创建调用。FrmLearnNozzleBank1.cs:462–529；同名引用检索见本地审计。

## 04 几何、高度与对中

- 产品编程三个助手均先ChangeNozzleAssistance；高度窗返回OK后Start，若工具仍未全部示教完成则提前返回，否则调用人工还嘴助手。对中窗OK后Start，但处理器尾部没有同样还嘴调用；几何窗OK刷新节点，无论OK与否在尾部请求人工还嘴。UcEditProductProgramming.Assistance.cs:928–1029。高度和对中计算复用已发布07专题，不重复推导。
- 几何为矩形两点、圆形三点。矩形把第二点减第一点写ToolGeometry.X/Y，未取绝对值；用角点偏移减几何半值写NozzleOffset，置EditState.Completely并Save。圆形FitCircle返回的radius写ToolGeometry.Z，不是直径。FrmToolGeometryTeach.cs:128–198,216–265。
- 几何窗离线回调可只返回OK；圆拟合失败回调可返回Cancel或要求重教。但外层BtDone无条件将ToolGeometryAssistant置Able、Save并设置OK，不能仅凭Able证明尺寸有效。返回上一页不删除此前pointList内容。FrmToolGeometryTeach.cs:352–384。

## 05 自动判断与状态冲突

- IsNeedToChangeNozzle只比较目标名与当前名；JudgeAndChangeNozzle同名直接true。TakeNozzle自己也先同名true。生产取晶只在不同名时Change，false变Abort，随后重新按名取当前对象，null抛错；S2打印点胶先验证所选吸嘴存在且示教完成，再JudgeAndChange，false变Abort。System2Controller.cs:157–170,1008–1041；PickActionNode.Provider.cs:120–140；S2DispenseActionNode.cs:104–121。
- ChangeNozzle停用工具库时关焊头真空，人工确认后写当前名/Save并开真空，取消false，不更新槽位。启用时先读逻辑名与物理在位，再关真空，即使未启用工具检测也执行这次物理读取；检测开关决定后续使用物理还是逻辑在位。System2Controller.cs:898–980。
- 开检测后物理有嘴但逻辑空直接false；物理空而逻辑有嘴，OK清名后再次检测，Ignore保留初始无嘴判定，Abort返回false。存在工具则Putback，false退出；Take目标false退出。最后MoveShelfToHome返回值未门控就返回true。System2Controller.cs:933–1000。

## 06 取嘴

- TakeNozzle工具库停用分支仍查工具与架，人工OK后把目标SlotIdentification−1的槽写OnBondHead，写名/Save、开焊头真空、保存架，取消false。普通Change停用分支没有这份槽位更新，不能合并。System2Controller.cs:172–202。
- 非DryCycle且开检测，先检测焊头已有工具，关真空；报警可忽略继续或终止。待取槽DryCycle只检查已配置名称，其他模式还要求槽位传感器有嘴；Retry重查，Ignore跳到Continue，跳过机械取嘴全段，Abort false。System2Controller.cs:204–264,516–546。
- 请求换嘴安全Z后后台移动工具架，同时取得取嘴G0/角度并转T；按Y安全判据选择XYZ直接移动或先XY再Z。T偏差>0.1会在等待工具架任务之前false；工具架任务成功且IsShelfAtChangeNozzlePos通过才继续，否则抛错。System2Controller.cs:267–335。
- Z进入槽位，开焊头真空，再按放嘴辅助位置慢速抬Z。取到检查失败可按自动重试次数关真空、回取嘴Z并重做；人工Retry只重查物理在位，Ignore继续，Abort false。这一轮检查没有DryCycle豁免。System2Controller.cs:338–445。
- 可选换嘴吹气是独立Task，内部才置IsChangeToolBlowFinish=false，未在当前方法await；没有统一finally恢复此标志。随后Y退离。Continue后的最终检查仅在非DryCycle且开检测执行，也允许Ignore后到状态提交。最终写目标槽OnBondHead、当前名/设备Save、架Save后true，没有在这里清其他槽或回架。catch报警/记日志再抛出，没有统一回滚。System2Controller.cs:447–573。

## 07 还嘴

- Putback停用工具库时人工确认只清当前名/Save，不更新槽位或显式关真空；启用而当前工具对象null直接true。非DryCycle发现当前工具未配置时请求手动取走，可重查物理，确认空后关真空、清名true，不保存槽位。System2Controller.cs:579–650。
- 非DryCycle要求待还槽传感器为空，Retry重查、Abort false。预备位置为Place数组Y−退离距离，Z低于BMC测高结果则抛错；先到预备Z，Y不安全时退模组，后台移动工具架，同时转T、移动Z/XY。先关焊头真空，再等架任务及到位判据；随后核对T角。System2Controller.cs:653–764。
- Y推入放嘴点后，Z按当前+3、速度100抬起，再请求换嘴安全Z。非DryCycle且开检测检查焊头不应有嘴，读后关真空；Retry重查、Ignore继续、Abort false。尾部写槽OnSlot、清当前名/Save、架Save、true。catch报警并抛错，没有统一状态或运动回滚。System2Controller.cs:766–890。

## 08 检测、回位和安全判据

- 参数less IsToolOnBondheadPhy 开焊头真空、等200ms；普通开关读CheckToolSensor，模拟检测读焊头真空并比较配置阈值，方法不自行恢复真空。带Nozzle重载读一次PDO后直接true，不能替代前者的有效检测。逻辑在位只看当前名是否非空。BondHeadController.GasIORelated.cs:127–175。
- CheckToolBankConfiguration停用架直接true；启用时硬编码前7槽，只拒绝“空配置槽但传感器有嘴”，不保证所有配置吸嘴都物理存在。主程序启动自检消费其false，并在开工具检测时核对当前逻辑/物理冲突：物理有逻辑无false，逻辑有物理无可人工清名或终止。NozzleShelfController.cs:73–179；System2Domain.cs:706–745。
- 模组定义12个槽位传感器，IsSlotHaveNozzle支持1–12，其余false；控制器架空检查仍只检查1–7。可配置槽数、数组长度、实际传感器范围与控制器检查范围不是自动统一的数量。NozzleShelfModule.cs:45–111,158–199；NozzleShelfController.cs:262–275；NozzleShelfParam.cs:22–117。
- 模组MoveShelfToHome为AxisY.AbsoluteMove(−1,true)，NoWait为SendAbsoluteMoveCommand(0)，未在方法中用零位传感器执行寻零。控制器有单步门控，IsShelfAtHome却判断实际Y<−3。换嘴位移动转换取Y，但IsShelfAtChangeNozzlePos把实际Y与转换结果Z比较，不能按名称替换成正确Y到位条件。NozzleShelfModule.cs:119–132；NozzleShelfController.cs:44–67,217–245,308–313。
- 换嘴安全Z方法离线或单步不通过均void返回，否则请求配置的ChangeNozzleSafePos.Z；调用者不能从void得到统一成功状态。IsNozzleShelfAxisYSafe比较焊头G0.Y与PlaceNozzlePos[0].Y−ChangeToolDistanceY，非全区域碰撞求解。BondHeadController.MovementRelated.cs:71–91；System2Controller.cs:1048–1071。

## 09 人工入口与取消

- 主界面“吸嘴库”非离线先要求ToolBank坐标存在；TestRun入口无离线豁免，也先要求该坐标并退出单步。Designer的两个ItemClick均绑定。UcMainSystem.Manual.cs:76–142及Designer:829–856。
- FrmNozzleBankManual取嘴使用Change，只有true再去安全位；同名提前返回路径不会执行尾部Refresh。还嘴按钮忽略Putback与Home结果，继续请求安全移动。刷新先SelfCheck但不消费bool，再以槽OnBondHead反写当前名并保存，RefreshControl本身也Save架。维护按钮在工具架Y>=−1.5时请求换嘴位，否则直接调模组Home，错误提示不一定终止其余刷新。FrmNozzleBankManual.cs:99–292,367–420。
- ChangeNozzleAssistance只有名称不同、工具在架且架启用才走自动；否则关ToolVacuum后人工提示，OK写名/Save并开焊头真空，Cancel false；同名true不物理复核。TouchDown独立助手未配置/架停用时也是人工路径，但OK经SetTouchDown保存，BMC委托通用助手。System2Controller.Assistant.cs:1661–1700,1827–1864。
- PutbackNozzleAssitance未配置或架停用分支，只有OK内部检测并清名，但Cancel仍可落到当前槽OnSlot/架Save并true。自动分支忽略Putback bool，只有随后架Home的ExcuteResult有显式失败异常；catch false。不能把整个助手true等同于还嘴已经物理完成。System2Controller.Assistant.cs:1706–1820。

## 10 重复测试与旧实验按钮

- 主界面可达FrmToolsTestRun的PP按钮在架停用时退出。Start只创建后台任务并立即true；循环遍历所有非空槽名，即使同名也Change。失败弹窗退出；每次换后并发请求架Home和模组安全位，分别Wait(10000)，只显式检查t1.IsCompleted，未消费两个动作的完整成功状态。延时100ms后才看停止标志。FrmToolsTestRun.cs:98–266及Designer:35–53。
- 再点停止只置标志/改按钮，不同步等待。finally仅当末次换嘴bool成功时回架并重置按钮。FormClosing仅检查顶针测试线程，没有同样检查PP线程。SaveForceVal是独立方法，常规PP循环未调用它，不能宣称自动导出换嘴力值。FrmToolsTestRun.cs:117–157,239–266,354–426。
- 管理员双击固晶模块可打开UcBondModuelSetting；其“吸嘴示教重复性验证”处理器主体全为注释，“吸嘴架运动重复性测试”实际仅GetCleanPos，原50次回位/换位循环被注释。不根据按钮标题画成有效重复测试。UcModule.cs:502–511；UcBondModuelSetting.cs:667–760,1596–1608及Designer:395–402,517–524。
- FrmMachineFunctionTest另有PP重复换嘴：换嘴后同样并发两次移动/限时等待，只核t1完成；停止或总时长>1小时退出，finally导出每次耗时到D:\设备功能测试，且末次成功才回架。本轮未检出主程序直接new此窗的有效调用，把它作为独立已编译诊断实现，入口可达性不作扩张。FrmMachineFunctionTest.cs:343–478。

## 11 保存对象与本轮边界

- 当前名由SetCurrentNozzleName立即写设备参数；取/还尾部另Save槽位仓库，没有统一跨文件事务或失败回滚。
- 吸嘴实体的几何、示教/编辑、新建与配方归属保存到吸嘴仓库；工具槽配置保存到工具架仓库；选择哪个工具架写BondProgram。
- 工具架位置/角度/安全Z/SlotNum保存到设备参数，ToolBank坐标在示教中途另存坐标目录。仓库路径分别为设备目录NozzleRepositoryPath.json和NozzleShelfRepositoryPath.json，见ZX2200PathConfig.cs:118–128。
- 本记录完成当前源码事实复核。完整阅读页、实际Archify图、清单逐项绑定及浏览器验收完成前，31.01–31.05继续pending。没有运行硬件、驱动、真空或动作精度验证。

本批审计40个主程序文件，按Windows路径忽略大小写与当前1,137个Compile项核对均在编译范围；85段拟绑定依据保存于本地审计。对照原基线复算1,157个C#原件，指纹全部一致。完整读取/引用范围、文件指纹和编译归属在 output/functional-atlas/tool-bank-source-audit.json；本批未修改正式业务数据。

## 12 完整阅读页发布

新增 /#topic/tool-bank，与 /#catalog/tool-bank-process 共用同一页面。11个环节、47个节点覆盖31.01–31.05；默认先看自动换嘴主链，再分别展开工具/槽位、配置、示教、取还嘴、检测、人工和测试。高度/对中计算复用07的中心与高度环节，通过公共入口连接，不重复正文；四种状态和六类保存对象各用一张表对照。

以本记录提交 a1a4e5f18061568c7c03dd8d0e1e59631e62b9c9 固定来源，使用Archify3.2.0实际生成tool-change-overview及tool-change-reading。两图均9节点、9关系，保留相同文字、来源和分支，横图在图框不足860px时切纵图；四个交付检查均通过，无诊断。规格、原始HTML、交付回执与页内检查范围见 tool-bank.verification.json；本轮页内阅读使用18/14px，不把原生检查替代放大后的目视核对。

当前源码绑定85段依据，涉及40个主程序文件；全局17个专题、194环节、785节点、1,186条说明，249文件1,123段依据。前端357项通过；最后只缩短一个节点标题及状态表短语后，相关31项再次通过。源码/资源检查、TypeScript与最终生产构建通过，本次构建38.07秒；76项目录119资源链接通过。未采集覆盖率，未运行设备、驱动或换嘴精度测试。

浏览器逐个切换47节点并确认标题，目录入口也检查为相同专题；桌面和497px分别目视完整九节点主链及四行状态、六行保存表。窄屏初版存在末字单独换行，缩短后重新构建发布，并检查更新后的标题和四行表。检查只作普通页面滚动，没有图内缩放或拖动。截图、节点记录、目录快照、尺寸记录及日志在 output/functional-atlas/tool-bank/。

最终发布继续复用健康8765服务的原进程23012，保留旧哈希资源并最后替换首页；原首页、索引及公开资源清单在 output/functional-atlas/before-tool-bank/。原1,157个C#指纹一致，正式业务数据和设备配置未改。临时窄屏检查页验收后移除。累计66/241条逐项复核、175条继续制作，下一项32清嘴排胶与手动维护，45专题原范围不变。
