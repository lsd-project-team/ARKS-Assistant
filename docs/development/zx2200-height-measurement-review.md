# ZX2200 测高与测量工具复核

对应原清单 29.01–29.06。以下按项核对主程序的可见入口、实际调用、结果与导出；页面覆盖状态在制作并验收后登记。主程序源码只读，不执行设备动作。

## 入口与共用控制器

主界面“测量工作”注册 BarBtMeasureTool_ItemClick，创建 UcMeasuringTool。其 Designer 实际绑定多高度、距离、固晶水平、S1/S2 平面度五个按钮；焊头标准有独立窗口和处理方法，但面板 Designer 没有对应控件/点击绑定，按现有实现保留该入口边界。标准块处理方法、固晶水平和 S2 平面度先调用 ChangeTouchDownAssistance，false 则返回；S1 平面度不经过该换工具入口。定时器按当前系统切换 S1/S2 按钮，Load 另按是否配置 S1 禁用。依据：UcMeasuringTool.cs:48–179。

S1 MeasureHeightModule 绑定点胶 Z、点胶激光测高、点胶测高传感器、气缸电磁阀、预点胶平台检测及上下检测。开/关缸在配置激光时直接跳过；探针开缸轮询用 TimeSpan.Milliseconds>delay，收缸用 TotalMilliseconds>delay，两者并非相同的超时计算。轮询每次 Sleep(10)，失败可 Retry 或抛异常；模块对缺硬件抛明确异常。依据：MeasureHeightModule.cs:32–116；DispenseMeasureHeightController.cs:52–164。

S1 DispenserHeightMeasurementG0 离线直接 Success/0；DryCycle 可移动到目标后用当前轴位换 G0 Z 返回。在线按 Dispenser/HeightSensor 选预点胶检测或测高传感器，移位、单步通过后按需开缸并测量。失败弹重试/退出，退出在正常收缸之前；仅成功、HeightSensor 且 closeCylinder=true 才执行收缸，最终将机械高度换 G0 并保留 4 位。无统一 finally 保证失败收缸。依据：DispenseMeasureHeightController.cs:175–270。

S1 底层激光支路延时后读取激光，按读数是否 NaN 置返回状态，机械表面高度=当前 Z−读数；探针支路先拒绝已触发输入，再构造负向 Probe，搜索距离=MeasureHeightDownDistance+MeasureHeightDistance，超时10000、IsWaitStopArrive=false，Probe 地址4/4532/5。另一个预点胶输入支路用 IOMeasureHeight，负向距离3。两个 MeasureHeightEntity.DoWork 的驱动内部来自外部依赖，未在主源码中展开。依据：同控制器:279–424。

BondHeadController.MeasureHeight 四参数重载用当前 Z 作为 searchPosition。Manual 返回 Abort/999；TD 使用焊头 LVDT/配置阈值，ForceSensor 使用校正台模拟量/阈值1，其他分支打开真空并用漏晶检测。实体执行前每次 Sleep(1000)，失败可重试；选择取消后保留返回状态。仅 WithVacuumSensor 在正常末段关真空，没有统一 finally；非 TD/Force 的其他枚举也进入开真空分支。依据：BondHeadController.cs:640–864。

S2DispenseController.LaserMeasureHeight 只返回传感器 GetValue；LaserMeasureHeightInGo 返回 当前 G0 Z−焊头到测高偏移Z−读数，方法本身没有运动或在途采样。当前主源码直接名称检索只找到 InGo 定义。ForceMeasureHeight 是独立压力方法：连接压力计，Z以速度1下降5，压力>10停止，若先到位则抛失败；随后100次以阈值20和±0.003调整，最后回机械Z。主源码直接调用只见注释测试，不接到生产多点主链。依据：S2DispenseController.cs:114–213；名称检索全主目录，不推定外部程序集不会调用。

S2 激光头气缸开缸：离线跳过；已有 NLimit+输出真则返回，否则输出true并等待NLimit 2000ms，可重试、忽略或抛异常。收缸：未配置 IsSystem2Dispense 跳过，否则看PLimit+输出false，发false等PLimit 2000ms，重试或抛异常。开缸忽略可直接返回，没有成功bool传给上层。依据：S2DispenseController.cs:697–803。

## 生产物料的多点测量与回写

S1 Domain 在无点或未开启 S1 测高时返回 Success；逐点单步、局部→G0，并按激光0/探针MeasureHeightDistance抬高目标，调用共用 HeightSensor 方法。测量结果先转回物料局部Z并加入 resultList，再检查返回值、G0偏差和NaN。Retry 不移除刚加入的失败样本；Ignore 禁用物料并返回 Success，Abort 返回 Exception。全部通过后取实测局部Z均值−配置局部Z均值，先写 MeasureHeightResult，再判NaN、累加 CoordinateSystem.Distance.Z、置 IsMeasureHeight。依据：System1Domain.cs:371–475。

S2 Domain 在无点或未开启 S2 测高时跳过。激光支路先按测高偏移移位、开缸、延时，检查原始读数绝对值阈值/NaN，通过后加入 pos.Z−原始读数；TD 支路移到 G0Z+搜索起距，调用焊头TD，再把机械测量值换 G0，检查返回/偏差后加入 G0Z。两支路的单步都实际调用 System1Domain.WaitSingleStep；Retry 只重读/重测，Ignore 禁用物料并返回Success，Abort返回Exception。最终同样以结果均值−配置局部Z均值调整整体Z，先写结果再判NaN；TD支路没有额外先转物料局部坐标。依据：System2Domain.cs:796–1010。

上述两条生产主链只使用均值及整体Z平移，没有在这些方法中建立平面模型或按XY插值。旧 BondModuleController.MeasureHeightOnEntity 在进入原采集正文前已无条件返回 Success；后面的旧均值坐标更新不可达。全局标定中的 PlaneInterpolate 另属旧 Bond 偏移模型，参见已完成专题，不将同名工具接成当前物料测高算法。依据：以上 Domain 完整方法；BondModuleController.cs:83–146；全局标定复核的独立模型段。

System2Controller.LaserMeasureHeight(list) 是另一个逐点原始激光批量读取入口，逐点移位/开缸/延时后检查绝对值阈值，可重试、忽略或抛异常；没有相同的 IsNaN 检查，也未统一收缸。它返回原始数值列表，不等同于 G0 表面高度列表。依据：System2Controller.cs:1388–1450。

## 固晶水平与平面度

固晶水平 Measure 每点先上安全位，依次转T=-180、-90、0、90；第一点到示教BMC中心，后续相对当前XY作(-17,-17)、(+17,-17)、(+17,+17)移动。用示教ZG0转机械作为搜索起点，TD测高后换G0，写入 Height0/90/180/270；字段名称与实际角度顺序不同。极差=Max−Min保留4位。失败返回默认结果对象，catch后也返回对象，finally尝试安全位；外层每轮仍加入对象。结果窗Retry会清空本批并重跑。依据：FrmBondLevel.cs:75–189、197–267；BondLevelMeasureResult.cs:16–54。

S1平面度按所选配置的G0 XY列表和ZG0逐点移动，共用S1测高，closeCylinder=false，失败可带着已有部分结果返回。外层只检查Count==0，非空部分结果也会计算极差并以反射按属性顺序赋值，故不能等同全点成功；正常末段上安全位，未做同样统一收缸。S2平面度用勾选项分TD/激光，TD机械值换G0；激光原始读数也直接过ConvertMachineToG0Pos，且判空写为 heightInMachine==double.NaN，不是IsNaN。按ChkBackCy逐点收缸，批次开始/结束另按硬件配置收缸。外层同样只拒绝空结果、非空就算极差，结果窗Retry整批重来。依据：FrmSystem1FlatLevelMeasure.cs:68–235；FrmSystem2FlatLevelMeasure.cs:141–350。

S1/S2平面度示教最多十个手动点，Next记当前G0 XY、Back删末点，任一步Done记当前点并把列表写配置/Save，不是自动矩阵采样。S1示教构造先安全位并开缸，Done/Cancel收缸，FormClosed只释放方向控件；S2示教由外层按激光勾选开收缸。预测Z是另一个单步示教窗保存ZG0，S1/S2均由Done写仓库、OK结束。依据：FrmSystem1FlatLevelMeasureTeach.cs:65–84、95–381、438–465；FrmSystem2FlatLevelMeasureTeach.cs:50–60、76–368、425–454；FrmSystem1HeightTeach.cs:85–96、153–168；FrmSystem2HeightTeach.cs:83–95、152–172。

## 四层产品示教与动作入口

四层调用均将当前对象坐标系和对应配置交给 FrmMeasureHeight；焊点先检查测高开关，部分入口选择当前基板/模块/焊点，异形对象另先定位。窗体Load在S1/S2都未启用时直接标ForBidden并OK；否则固定以SubstrateCamera方式示教。Next/Done取得当前物料局部点，再通过TUAssistantHelper测高，将G0结果换回局部Z后加入点列。失败时NextAction先减stepIndex、外层Next再增；Done失败也先减索引但外层仍会把当前部分列表赋给配置。正常Done先更新示教状态、ProductConfiguration.Save并OK，再由点击处理方法赋 HeightMeasurementPoints，新列表赋值晚于窗内保存调用。默认stepCount=5，但SetUiControl在stepIndex==2时隐藏Next，正常按钮路径是1–3点。上层返回后主要刷新状态/进入下一步骤，不能把窗内保存顺序写反。依据：FrmMeasureHeight.cs:99–237、256–316、362–365；UcEditProductProgramming.Assistance.cs:510–660；UcObjectFunctionEdit.cs:390–427。

生产动作层：S1载具/基板/模块/焊点均转Domain共用方法，但IsDoWork和DoWork检查位置不同；S1载具在DoWork再看全局开关，基板还看EntityState.Process。S1焊点把非Success的Domain结果改成Abort；异常仍Exception，finally置Stop并通知WorkStop。S2四层同样转Domain；基板/模块的MatterProductState条件实际排除了EnableInSystem2，载具和焊点排除EnableInSystem1；焊点IsDoWork未检查S2测高开关，但Domain仍会检查。不能合并成所有对象完全相同的门控。依据：S1/S2的四类测高ActionNode完整DoWork/IsDoWork。

## 多高度测量与公共助手

多高度Load实际打开FrmChooseMeasureHeightType，未检查ShowDialog的OK/Cancel就读取Type；该选择窗在线构造时直接SetTouchDownOnBondhead。这个设置方法开焊头真空、将当前工具名记为TouchDown并保存，不证明执行了一次工具架物理换装。独立FrmMultipleHeightMeasurementType窗的值变化事件写死TouchDown，主链只复用它的枚举。示教Next/Done记当前点，Back删末点，Cancel置点列null；S1在Load上安全位并开缸，FormClosed仅释放方向控件。依据：FrmMultipleHeightMeasurement.cs:52–223；FrmChooseMeasureHeightType.cs:36–67；FrmMultipleHeightMeasurementType.cs:31–73；BondHeadController.cs:870–876。

TUAssistantHelper按当前系统移动/测量。离线给Success/0；S1 TouchDown走探针公共接口，SubstrateCamera先转换相机偏移并抬2，测后移回，但最后写死Success，未透传原result。S2 TouchDown和相机方式都调用TD，机械高度换G0，前者另上安全位，后者移回原位置。GetPosBySystem在相机方式叠加对应偏移，给了物料坐标系才转局部。依据：TUAssistantHelper.cs:282–386、463–502。

实际连续测量创建后台Thread：每一外层批次先Init清空各点结果，再10轮逐点移到所教Z+3，始终调用TouchDown（不使用窗口Type）且closeCy=false。成功写各点ResultList及TestList[0]，失败直接返回；ResultVision第0点展示原值，其余展示相对第0点同轮差，并Sleep(1000)。取消选中只在点边界被检查，正常/取消会调S1收缸；FormClosed对活线程Abort，无统一finally保证异常后的收缸或轴停止。结果刷新由timer的needFresh触发。依据：FrmMeasureHeightPoints.cs:72–246、326–370；Designer:121、144、297–299。

多高度SaveData只在TestList.Count>100时导出固定D盘目录。TestList每次进入DoWork只新增一个外层列表，所有数值却始终写入第0组；因此Count门槛不是100个测量点或100轮。保存后Clear，仍继续同一循环时没有重新建立第0组。FileHelper.SaveDoubleExcel按外层行、内层列写入xlsx，保存并释放ExcelPackage，没有创建目标目录。依据：FrmMeasureHeightPoints.cs:74–132；FileHelper.cs:30–62。

## 距离与焊头标准工具

距离示教记录两点：S2取机械真实位置，S1取G0；只把第二点减第一点的XY送结果窗，显示ΔX、ΔY和sqrt(ΔX²+ΔY²)，没有使用Z。过近判断实际为两个绝对差都小于0.01，提示文字却说至少0.10；失败选择OK回第一步，Cancel关闭，计数在校验之前已经递增。依据：FrmDistanceMeasurement.cs:88–209、232–303；FrmDistanceMeasureResult.cs:16–48。

焊头标准独立窗口读安装角、工具长度和次数，Task.Run采集。围绕硬编码G0点(168.1554,-274.8245,106.7341)，四个XY方向按工具长度偏移，T依次安装角加0/90/180/270，各次TD liftLevel=-28；前三次额外Sleep1000。没有检查四个Ret就计算ResultX=第1−第3、ResultY=第2−第4并加结果。仅正常末段上安全位，catch提示，无finally；按钮只改颜色而未禁止再发起，关闭只停timer、不取消或等待任务。依据：FrmBondheadStandardMeasurement.cs:85–200、249–263。该窗口自身Start事件已注册，但主工具面板的标准测量处理方法尚无按钮绑定，不能作为已证实可点击入口。

## 结果、范围与导出

平面度Range由本轮实际非空列表Max−Min得到；FlatLevelMeasureResult.GetMinMaxValue却始终使用10个高度字段，未测字段默认0可能参与着色。CustomDrawCell排除字段名写MaxDifference而该模型实际字段为Range，Range也进入同一数值着色判断。固晶水平窗口显示相对Height0的三项差，保留4位，四个高度参与最小最大着色；没有同样显式Excel导出方法。两个结果窗的Retry都会让对应上层清空整批并重测。依据：FlatLevelMeasureResult.cs:14–78；FrmLevelMeasureResult.cs:23–107；BondLevelMeasureResult.cs:16–54；FrmBondLevelMeasureResult.cs:25–109。

平面度的显式导出按钮使用SaveFileDialog和ExportToXls，取消不写，异常弹提示。测高数据独立窗订阅静态AddMeasureHeightData并Invoke追加BindingList；FormClosed弹xls导出，之后取消订阅并清空。该事件绑定已确认，但当前主源码直接名称检索未发现创建此窗或生产投递点，不把它画成所有测高结果都会自动进入的数据库/统计路径。依据：FrmMeasureHeightData.cs:24–91；Designer:144；原始名称检索另存output。

固晶水平中心与ZG0保存到BondLevelMeasureFilePath.json，S1/S2平面度点列、预测高度和S2勾选项保存在各自配置仓库，对应System1FlatLevelMeasureFilePath.json、System2FlatLevelMeasureFilePath.json。配置保存、结果表格与导出文件属于不同输出。依据：BondLevelMeasureSetting.cs:14–32；两FlatLevelMeasureRepository.GetFileName；ZX2200PathConfig.cs:321–331。

## 编译与复核范围

本批准备绑定63段源码范围、48个主程序文件；这些文件均登记在当前 AKRS.ZX2200.csproj 的1137个Compile项中。实际UI事件摘录与单次读取/独立数据窗的直接名称引用检索保存在output/functional-atlas/，不能由缺直接调用推定不存在反射或外部程序集调用。源码校验、页面制作及图表验收仍按各自步骤完成。
