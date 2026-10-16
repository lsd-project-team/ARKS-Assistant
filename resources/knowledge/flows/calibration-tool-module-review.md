# AKRS.Calibration 标定工具与生产接入边界

更新：2026-09-28。限定范围静态复核，未运行视觉SDK、设备或标定方案。

## 工作流摘要

窗口构造时尝试加载固定路径SOL；人工选择SOL后，加载按钮同步调用SDK加载方案、枚举流程、注册结果回调并绑定首个流程。选择流程后，运行按钮直接Run；回调读取字符串out并记录耗时。保存按钮仅在solutionIsLoaded为真时调用SDK Save。另有DripCalib API输入四组坐标数组，运行指定标定流程后返回缩放与平移。不能将这条工具链自动视为ZX2200生产启动链。

## 工程与调用边界

- [项目声明](../../trunk/AKRS.Calibration/AKRS.Calibration.csproj#L8)为Library，目标.NET Framework 4.8；[Program.Main](../../trunk/AKRS.Calibration/Program.cs#L16)虽调用Application.Run(new FormCalib())，声明的类库并不据此成为可独立启动的EXE。
- [主项目](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4078)有ProjectReference。对trunk中非bin/obj的C#/csproj搜索FormCalib、AKRS.Calibration及Correction.GetInstance，未找到ZX2200有效直接调用FormCalib的语句；CalibrateTask的两个Correction调用是注释。此为文本检索边界，不排除反射、动态或外部调用。
- [Correction构造函数](../../trunk/AKRS.Calibration/Correction.cs#L54)中Init调用被注释；其私有Init的四个PRC加载不能描述为构造时必然执行。

## 步骤、输入输出与失败处理

|步骤|源码证据|确认行为及边界|
|---|---|---|
|窗口初始化|[76–110](../../trunk/AKRS.Calibration/FormCalib.cs#L76)|创建RenderControl，设300ms计时器，调用InitSolutiion加载用户桌面固定SOL；异常弹窗后继续订阅SDK状态事件；没有在此设solutionIsLoaded=true|
|选择文件|[208–235](../../trunk/AKRS.Calibration/FormCalib.cs#L208)|选择.sol，清加载标志、保存路径并启动指示计时器；取消只清路径|
|加载方案|[286–338](../../trunk/AKRS.Calibration/FormCalib.cs#L286)|同步Load→枚举→更新选项→注册回调→置加载标志→访问processList[0]；空列表可能在置标志之后抛异常。catch只记录，finally恢复按钮；无自动重试或回滚|
|流程列表和回调注册|[344–375](../../trunk/AKRS.Calibration/FormCalib.cs#L344)|从VmSolution枚举流程；注册函数实际遍历字段processList而非传入lst，异常只记录|
|单次运行|[518–535](../../trunk/AKRS.Calibration/FormCalib.cs#L518)|按SelectedItem取得VmProcedure并Run，本方法没有空值检查或catch；不代表连续生产调度|
|读取结果|[382–415](../../trunk/AKRS.Calibration/FormCalib.cs#L382)|要求out是字符串，读取首项并记录；未配置则记录提示，异常记录，最后正常路径记录ProcessTime|
|保存|[423–436](../../trunk/AKRS.Calibration/FormCalib.cs#L423)|加载标志为真才Save；初始化直接Load没有同步此标志。SDK保存内部格式及原子性未提供|
|计时器|[444–460](../../trunk/AKRS.Calibration/FormCalib.cs#L444)|只切换加载按钮颜色，不启动标定或生产任务|
|点胶标定API|[549–598](../../trunk/AKRS.Calibration/FormCalib.cs#L549)|加载固定SOL，取4点胶9点标定；传WorldX/Y、ImageX/Y，Run后取CameraScale、TransX/Y；isSuccess为0或异常返回false。输出数组为空时保留0，也可能因非零isSuccess返回true；本层未校验输入数组长度|
|关闭|[802–811](../../trunk/AKRS.Calibration/FormCalib.cs#L802)|只停止、退订并释放指示计时器；本方法没有退订SDK静态状态事件/流程回调，不据此推断SDK已释放或运行停止|

## 缺失项与下一验证

1. 窗口与Correction标定API、偏移/角度和仿射方法已分段复核（见后续章节）；需完成数值边界、动态调用、外部SDK与现场验证，不能以源码阅读代替验收。
2. 两个控件包装、窗口切换、连续运行事件和日志已作源码复核（见下节）；重复加载、关闭后回调及外部控件释放需运行验证。
3. 核验固定SOL/PRC资产、VM/Halcon版本和项目实际编译条件；缺少外部实现时只描述调用接口。
4. 追踪主工程实际使用的标定服务，区分源码存在、项目引用和运行接入三种证据。
5. 在隔离环境测试空方案、缺失输出、无选中流程、加载失败和关闭中回调；未做测试，不宣称复现或设备安全结论。

本轮结论与源码片段登记于module-reviews.json及module-review-evidence.json；状态仍为部分复核。

## 2026-09-28：窗口标定API与转换结果契约

|接口|实际流程名|结果契约|
|---|---|---|
|[BondCamCalib](../../trunk/AKRS.Calibration/FormCalib.cs#L611)|3上相机12点|四组坐标输入→Run；输出读取代码被注释，三个out参数保持初值0|
|[WaferCamCalib](../../trunk/AKRS.Calibration/FormCalib.cs#L675)|5晶圆相机9点|四组坐标输入→Run；输出读取被注释，三个out参数保持0|
|[UpLookCamCalib](../../trunk/AKRS.Calibration/FormCalib.cs#L741)|1下相机12点|四组坐标输入→Run；输出读取被注释，三个out参数保持0|

三者每次加载固定桌面SOL并设置渲染控件ModuleSource；isSuccess首项为0或发生异常返回false，否则true。因此true不能等同于已返回有效cameraScale/transX/transY。本层没有输入数组等长/有限值检查；SDK内部行为未知。与DripCalib真实读取输出的行为不同，不得按同名接口泛化。

### 四类坐标转换及偏移计算

[Invoke包装](../../trunk/AKRS.Calibration/Correction.cs#L1015)直接返回对应私有转换结果。四个方法分别为[Wafer](../../trunk/AKRS.Calibration/Correction.cs#L1071)、[Drip](../../trunk/AKRS.Calibration/Correction.cs#L1115)、[UpLook](../../trunk/AKRS.Calibration/Correction.cs#L1158)、[Bond](../../trunk/AKRS.Calibration/Correction.cs#L1199)：double输入转成单元素float数组→加载固定PRC→SetInputFloat→Run→读取X/Y首项→Dispose→true。异常直接false；Dispose不在finally，不能保证失败时释放。若X读取成功而Y失败，false也可能带部分更新的输出。这里没有检查isSuccess输出，true只表示本层未抛异常。Wafer与Bond还取全局变量1对象，后续赋值语句被注释；这次对象获取仍可能参与异常路径。

[GetOffsetWorld](../../trunk/AKRS.Calibration/Correction.cs#L1247)按Drip/Wafer/UpLook/Bond选择转换，分别转换输入点和固定参考点(1224,1024)，再做差。所有Invoke的bool均未消费；未知name（含默认null）直接返回初值0。由此只能记录未传播失败的静态边界，不能断言现场已发生错误偏移。

### 主工程实际接入对照

- [上视标定段](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L541)：建立UpLookCameraCoordinateSystem→DependentCoordinateSystem.Init(CameraStaticDown)→Save→Refresh，再NPointTrans并保存UpLookHomMatTrans；旧Correction.UpLookCamCalib为注释。复用证据calib-uplook-grid。
- [晶圆标定段](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L851)：旧Correction.WaferCamCalib为注释；实际创建WaferCameraCoordinateSystem→Init(CameraStaticUp)→Save→Refresh，再NPointTrans并保存WaferHomMatTrans。复用证据calib-wafer-grid。
- 对非bin/obj的trunk C#查找四个Cam/DripCalib调用，仅发现FormCalib/Correction定义及上述注释；此结论限定为文本检索，不能排除动态/外部调用。

待验证：非零状态但输出缺失、PRC加载/输出/Dispose失败、并发重用静态流程字段，以及主工程完整停止与保存恢复流程。未运行外部SDK或设备。

## 2026-09-28：显示控件与后台回调的边界

- [MainViewControl](../../trunk/AKRS.Calibration/Controls/MainViewControl.cs#L13)只初始化设计器并包装LockWorkArea/UnlockWorkArea；Unlock使用空条件调用，Lock直接调用。设计器创建VM全局工具和主配置控件；这不等于生产互锁或设备暂停，SDK内部语义未核实。
- [RenderControl](../../trunk/AKRS.Calibration/Controls/RenderControl.cs#L28)的ModuleSource setter先赋值给SDK控件，成功后才更新本地字段；没有启动Run。图像由外部VM控件处理，不能推断该setter自行采图。
- [窗口构造](../../trunk/AKRS.Calibration/FormCalib.cs#L76)中mainViewControl实例化、Lock和Dock三句均被注释。该字段在当前FormCalib源码和设计器中未找到有效赋值；[Load](../../trunk/AKRS.Calibration/FormCalib.cs#L502)与[配置按钮](../../trunk/AKRS.Calibration/FormCalib.cs#L195)却仍尝试Controls.Add(mainViewControl)。因此不能将配置页描述为已完成正常接入；是否抛错或显示空页未运行验证。
- [图像按钮](../../trunk/AKRS.Calibration/FormCalib.cs#L179)读取选中流程、绑定ModuleSource、清空Panel再加入RenderControl；没有本层空选项检查及catch。配置按钮只清Panel并加入配置控件、改颜色，不启动标定。

### SDK事件与UI状态

[开始事件](../../trunk/AKRS.Calibration/FormCalib.cs#L117)直接Invoke切换到UI；nStatus==0时禁用选择/加载/保存按钮并写日志，没有IsHandleCreated前置判断。[停止事件](../../trunk/AKRS.Calibration/FormCalib.cs#L145)先检查IsHandleCreated，nStopAction==1才恢复选择和加载；保存按钮恢复语句被注释。开始/停止回调均未在本层发起SDK连续运行或停止命令，只响应SDK通知。不能因存在回调就补出一个自动调度器。

构造函数订阅两个静态状态事件，加载方法为各流程追加OnWorkEndStatusCallBack；在本模块C#检索仅发现这些+=，未发现对应SDK事件-=。已读FormClosing只处理指示计时器。控件设计器Dispose调用components.Dispose及base.Dispose，不代表全局SDK、流程或静态订阅已释放；SDK换方案时是否自动释放旧回调尚未知。

### 日志输入、输出与失败路径

[AppendLog](../../trunk/AKRS.Calibration/FormCalib.cs#L241)先检查界面日志数量（大于10000时清空），再根据InvokeRequired使用BeginInvoke或直接插入，并同步追加相对路径./log/LocateDemoCs.log。数量检查和Clear在跨线程判断之前；异步UI插入成功与磁盘追加成功不是统一事务。catch重新throw new Exception(ex.Message)，没有重试。调用者catch内部再次AppendLog时，日志故障仍可能向上传播；文件权限、并发写入和关闭中回调尚未复现。此文件与主工程生产日志仓库不是同一已确认链路。

本节仅阐明当前代码，不修改生产实现；上述UI/SDK行为需隔离环境验证。

## 2026-09-28：单点与双点批量仿射纠偏

### 实际执行顺序

1. [单点入口](../../trunk/AKRS.Calibration/Correction.cs#L692)创建输出列表；workName为Drip或Bond时转换基准和定位像素点，两次Invoke返回值均未使用。未知workName没有异常分支，转换变量保留初值0。
2. 相机基准/定位位置分别叠加转换坐标，形成两组绝对点；[CalcuSubMapP1](../../trunk/AKRS.Calibration/Correction.cs#L738)调用TupleRad转换p1Angle，再以基准角0、定位角P1Rad调用VectorAngleToRigid。局部offsetX/Y计算未用于矩阵构建。
3. 遍历initialPoints，经[MapPointTrans](../../trunk/AKRS.Calibration/Correction.cs#L993)调用AffineTransPoint2d，将输出首项转float并加入新列表。输入顺序被保留；空列表不跳过前面的矩阵计算。
4. [双点入口](../../trunk/AKRS.Calibration/Correction.cs#L775)同样只分Drip/Bond，执行四次坐标转换并叠加各自相机位置；调用[CalcuSubMapP1P2](../../trunk/AKRS.Calibration/Correction.cs#L837)，再逐点映射。矩阵方法用AngleLx获取基准/定位连线角，计算各自中点，调用VectorAngleToRigid；最后还变换固定点(1224,1024)，但该调用的qx/qy未用于返回结果。

### 输入、输出及失败处理

输入包含工作类型、相机位置、像素点、待转换点列表；单点另有角度。输出是PointF列表。本层未校验列表null、坐标有限性、双点重合或未知工作类型，没有catch、自动重试或失败状态返回。底层Invoke返回false不会中断；但矩阵/映射SDK抛异常会向上传播。若遍历中途抛异常，out列表已经分配且可能包含前缀结果；调用者不能把部分结果视为全部转换成功。SDK数值语义与工艺角度/单位仍需独立验证。

### 不纳入运行链的代码

[865–984行](../../trunk/AKRS.Calibration/Correction.cs#L865)的公开GetJointPositionByP1P2P3Affine及其CalcuSubMapP1P2P3处于整个块注释内，不登记为有效调用关系。注意这不等于Correction没有任何其他三点相关方法；前部同名/近名私有方法须独立复核。

对trunk非bin/obj C#搜索GetJointPositionByP1Affine、GetJointPositionByP1P2Affine，仅找到公开入口及私有重载定义，没有显式调用点；不排除反射/外部代码，也不把这些能力接到主生产图。此处是库内数据变换调用顺序，不是设备运动步骤。

## 2026-09-28：组合偏移、角度与私有定位方法

### 组合偏移链

[CalcOffset](../../trunk/AKRS.Calibration/Correction.cs#L208)先调用CalcBondOffset(Bond)，令rotateAngle=upLookAngle+bondAngle，再调用CalcUpLookOffset，但传入角度为常量0而非rotateAngle。最终XY为两种偏移相加，角度输出为两角之和；不能描述为先按合成角旋转再得到XY补偿。

[CalcBondOffset](../../trunk/AKRS.Calibration/Correction.cs#L160)按Drip/Bond转换基准和定位点，叠加对应相机位置后作差；未知类型保留零转换值，仍继续相减。[CalcUpLookOffset](../../trunk/AKRS.Calibration/Correction.cs#L122)两次上视转换后叠加相机坐标，调用Rotate再与基准点作差。两者均忽略底层转换bool。

### 角度与单/双点偏移

- [CalculateMidpoint](../../trunk/AKRS.Calibration/Correction.cs#L264)返回中点及Atan2连线角（弧度转度）。[GetAngle](../../trunk/AKRS.Calibration/Correction.cs#L237)在两点模式取列表前两点，在多点模式调用线性回归，其他枚举返回0；未检查列表数量。
- [CalciLinearRegressionAngle](../../trunk/AKRS.Calibration/Correction.cs#L283)直接按求和公式算斜率并Atan转度，未检查空列表、分母为零或有限值；[CalcCamAngle](../../trunk/AKRS.Calibration/Correction.cs#L307)对P1→P2/P3分别调用AngleLx与TupleDeg。数值退化与角度工艺约定待验证。
- [GetXYAngOffsetByP1](../../trunk/AKRS.Calibration/Correction.cs#L332)转换基准/定位像素，使用同一相机位置叠加后相减；仅返回XY，无角度输出。
- [GetXYAngOffsetByP1P2](../../trunk/AKRS.Calibration/Correction.cs#L376)四次转换后计算基准/定位中点和角差。然而417、418行CalculateMidpoint的第二实参分别为p1AbsBasePoint.X和p1AbsMarkPoint.X，不是相应Y。这里记录实参与签名不符的疑点，不能将其输出当作已验证的二维几何结果。该方法仍忽略转换bool，未加catch或重试。

### 私有定位/偏移重载

[435–487行](../../trunk/AKRS.Calibration/Correction.cs#L435)的单点/双点偏移定位：邦头坐标转换→叠加相机位置→单点或中点加指定XY偏移。双点方法计算的角度未用于输出。

[500–588行](../../trunk/AKRS.Calibration/Correction.cs#L500)：私有双点仿射重载构建矩阵后MapPointTrans；私有三点仿射重载虽是有效代码，但矩阵构建调用被注释，只把new HTuple()传给MapPointTrans，传入的六个基准/定位点未被使用。不能与865–984行整段注释的公开三点版本混为一谈；SDK如何处理空矩阵尚未运行。单点/双点Location方法计算像素点或中点的基准/定位转换差，再叠加xyzPosition；不消费转换bool，双点角度也未使用。

[Rotate与CalculateRotatedOffset](../../trunk/AKRS.Calibration/Correction.cs#L600)均先把角度转弧度，再以sin/cos计算；前者绕指定中心，后者旋转偏移向量，最终转float PointF。无运动硬件调用。

对非bin/obj的trunk C#搜索CalcOffset、GetXYAngOffsetByP1P2与GetJointPositionByP1P2P3Affine只发现定义（含公开注释版本），未发现显式调用方；因此上述疑点未被认定为生产可达故障。剩余同名标定方法、资产和SDK行为仍需复核。

## 2026-09-28：Correction同名标定接口与可复现依赖

逐方法复核结果：

|源码接口|执行流程及结果|
|---|---|
|[Correction.DripCalib](../../trunk/AKRS.Calibration/Correction.cs#L1287)|加载固定SOL→取4点胶9点标定→传WorldX/Y、ImageX/Y→Run→分别检查CameraScale/TransX/TransY输出数量并取首项；未输出项保持0；状态首项0或异常false，否则true|
|[Correction.BondCamCalib](../../trunk/AKRS.Calibration/Correction.cs#L1349)|3上相机12点；同样传四数组并Run，但数值输出读取被注释，三个out保持0；由isSuccess首项和异常决定bool|
|[Correction.WaferCamCalib](../../trunk/AKRS.Calibration/Correction.cs#L1412)|5晶圆相机9点；数值输出读取被注释，三个out保持0|
|[Correction.UpLookCamCalib](../../trunk/AKRS.Calibration/Correction.cs#L1477)|1下相机12点；数值输出读取被注释，三个out保持0|

这些接口不调用FormCalib同名方法，也不设置窗口渲染控件；本层没有输入数组长度/有限值检查、重试、结果持久化或显式Dispose。发生异常后只返回false，不记录异常。即使点胶接口，也不能把非零状态等同于三个数值输出都有效。未找到实际生产调用点的限制仍适用。

### 方案与SDK核验（2026-09-28快照）

[依赖核验记录](calibration-tool-dependency-audit.json)覆盖trunk（包含bin/obj，跳过符号链接及.git）的精确文件名搜索：上下相机映射对位_V4.3.0.sol、晶圆台标定转换.prc、邦头标定转换.prc、上视标定转换.prc、点胶标定转换.prc均未找到。代码使用C盘另一用户桌面的固定路径，本次只核验源码包，不推断现场电脑是否另有安装这些文件。其他PRC模板存在不能证明能替代上述方案。

项目[73–120行](../../trunk/AKRS.Calibration/AKRS.Calibration.csproj#L73)和[144–163行](../../trunk/AKRS.Calibration/AKRS.Calibration.csproj#L144)指向ZX2200/libs中的VM、VMControls、GlobalVariable及Halcon DLL；核验记录中11个指定文件均存在。VM相关引用多声明Private=False、SpecificVersion=False，不能据此保证输出目录自动携带完整运行依赖。未检查许可、原生依赖、实际加载版本或MSBuild求值，未执行程序集。

### 模块下一验收条件

本专题已覆盖主要行为文件的上述指定范围，仍不宣布模块完整验收。下一步需将固定方案缺失、SDK/位数/许可环境、UI与结果边界测试纳入交接检查；源码可继续分析，设备和方案运行验证等待相应环境。
