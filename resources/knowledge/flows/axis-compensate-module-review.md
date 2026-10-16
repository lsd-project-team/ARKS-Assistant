# 轴补偿模块：计算、测试调用与生产边界

更新：2026-09-29。范围为trunk/AKRS.Galaxy2.AxisCompensate及其显式调用点。静态阅读与原类数值隔离验证，未运行运动、生产标定或写入设备配置。

## 工作步骤摘要

1. 工程声明为.NET Framework 4.8 Exe，但Program.Main为空，没有在入口启动补偿任务或调度器；ZX2200通过ProjectReference引用该工程。见[项目声明](../../trunk/AKRS.Galaxy2.AxisCompensate/AKRS.Galaxy2.AxisCompensate.csproj#L8)、[入口](../../trunk/AKRS.Galaxy2.AxisCompensate/Program.cs#L13)、[主工程引用](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4090)。因此不能把它画成独立运行的自动补偿服务。
2. AxisCompensateProgram静态构造将FilePath设为DeviceDirPath/AxisCompensateProgram.json；继承的Singleton加载保存契约需另核，不能从路径赋值推定加载成功。GetOffset按轴名找到配置；不存在抛异常；输入落在StartPos+0.5到EndPos-0.5以外则原值返回，否则调用具体补偿对象，输出与输入偏差大于0.5时抛异常。返回值是补偿后的坐标，不是需要再相加的偏移量。见[入口与判断](../../trunk/AKRS.Galaxy2.AxisCompensate/AxisCompensate/AxisCompensateProgram.cs#L24)。
3. LsmCompensate调用MathService.GetPolynomialValue，将系数按升幂求和输出。没有运动指令、队列或本地重试。见[计算入口](../../trunk/AKRS.Galaxy2.AxisCompensate/AxisCompensate/LsmCompensate.cs#L42)、[多项式求值](../../trunk/AKRS.Galaxy2.AxisCompensate/AxisCompensate/MathService.cs#L25)。
4. 已定位的显式GetOffset调用在FrmTestMoveAccuracy.BtnTest_Click：按钮触发Task.Run，获取当前位置及步长文本→MoveTestPR定位和移到相机中心→51次循环；每次取当前坐标、X加54、计算BondX/BondY补偿并MoveBondXY→定位记录误差→目标X减51、再次补偿并MoveBondXY→循环结束写D:/MoveTestPR.xlsx。读取的step变量没有用于这段循环的54/51位移。见[事件绑定](../../trunk/AKRS.ZX2200/Experiment/Test/FrmTestMoveAccuracy.Designer.cs#L207)、[前半流程](../../trunk/AKRS.ZX2200/Experiment/Test/FrmTestMoveAccuracy.cs#L253)、[返回及输出](../../trunk/AKRS.ZX2200/Experiment/Test/FrmTestMoveAccuracy.cs#L313)。这是测试窗口链路，不能替代实际生产任务的补偿接入证据。
5. 此测试处理器没有保留或await Task，内部未见局部catch、取消标记检查或重试；异常会打断后续循环/导出，不能推定已向操作员报告。超过1的差值分支只弹框，没有return；同时外层GetOffset已有0.5阈值抛出，应区分两层判断。另有标定窗口停止按钮调用Save，不能据此推断每次自动生产都会保存补偿。见[测试任务253–355](../../trunk/AKRS.ZX2200/Experiment/Test/FrmTestMoveAccuracy.cs#L253)、[标定停止](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs#L228)。

## 系数生成不是已接入的自动生产步骤

|方法|输入、处理和输出|边界|
|---|---|---|
|AddAxisCompensate单列表|realPos拟合到axisPos；阶数为两长度最小值减1；创建LsmCompensate并按名称替换内存项|有效区间取axisPos最小/最大；没有Save调用；没有显式长度相等、空集或有限数检查|
|AddAxisCompensate多列表|先按同一列索引跨各轮取平均，再拟合；阶数大于30时改15，否则保留；按名替换内存项|有效区间改取realPos最小/最大，与单列表版本不同；缺项各列样本数可不同；没有显式完整矩阵检查|
|SegmentedCompensation.GetOffset|区间外原值返回，区间内也原值返回|CalibrationList虽声明80槽，但该方法未使用其值做插值或补偿；是当前源码中的未实现计算，不可宣传为可用分段算法|

依据：[两种拟合75–153](../../trunk/AKRS.Galaxy2.AxisCompensate/AxisCompensate/AxisCompensateProgram.cs#L75)、[按列平均35–60](../../trunk/AKRS.Galaxy2.AxisCompensate/AxisCompensate/MathService.cs#L35)、[分段实现36–46](../../trunk/AKRS.Galaxy2.AxisCompensate/AxisCompensate/SegmentedCompensation.cs#L36)。两种拟合catch仅Console.WriteLine再throw，不构成重试或回滚。MathNet Fit.Polynomial、外部Singleton及运动控制下层是本专题边界。

## 调用覆盖、缺失项与验收

- 在trunk的C#文本（排除bin/obj）检索AddAxisCompensate和SegmentedCompensation，仅定位到定义；IsAxisCompensateOpen也只定位到属性定义。GetOffset本身没有读取该开关。因此不能声称开关为false就必定绕过补偿，也不能声称系数生成已经接入自动标定。文本检索不排除反射、外部程序集或未提供源码调用。
- 主工程可见GetOffset显式调用来自上述实验窗口；维护停止按钮调用Save。窗口上层打开入口、外部配置反序列化以及实际生产控制器是否另有其他补偿机制，不在本结论中被否定。
- 本地边界用例已补37项，见下节。完整多项式条件数/误差分析、高阶与大坐标样本、生产配置加载、实际运行版本和运动接入仍待验收。
- 已完成下述五个原类的隔离编译与测试；未做完整产品构建或设备测试。此模块转为部分复核，不宣布全工程补偿业务完成；与已有控制器补偿、温漂、ETEL/固高映射专题分别追踪。

## 原类数值边界验证（2026-09-29）

`node scripts/test-axis-numeric.cjs`编译五个完整未修改原类，实际引用项目HintPath指定的`MathNet.Numerics.5.0.0/lib/net48/MathNet.Numerics.dll`。37项断言通过，[回执](axis-numeric-test.json)记录源码、测试支架及DLL哈希，并保留六组退化样本观察。运行环境为捆绑现代.NET，Singleton/FilePath与PathConfig只有惰性字段替身，不加载、不保存任何设备配置。这不是.NET Framework产品构建或现场程序集加载验证。

|检查范围|复现结果|
|---|---|
|开关与区间|默认false仍补偿；Start+0.5/End-0.5等号参与补偿；更外侧原值返回。宽度小于1的有限中间点不补偿，宽度等于1保留单个中点。|
|幅度与非有限值|正负0.5被接受，更大偏差抛出；NaN输入/系数返回NaN而未被幅度检查拒绝；正负Infinity输入由区间分支原样返回；有限输入的Infinity输出被幅度检查拒绝。|
|同名重复项|读取第一项；Add仅移除第一个同名项并将新项附到末尾，另一旧同名项因而继续优先生效。|
|两种拟合重载|同一组真实坐标→指令坐标样本得到相同线性输出，但单列表范围取指令坐标、多列表取真实坐标。不等长/空样本抛异常，失败前已有列表不变。|
|退化拟合|重复横坐标[1,1,1]对应[0,1,2]未抛出，替换出约1.4e31量级系数；NaN横坐标或Infinity纵坐标也未抛出，并将NaN/Infinity系数替换进内存配置。数值是本次库和运行环境的观察，不推广为所有平台固定结果。|
|平均与求值|不齐整矩阵按各列实际样本数平均；空矩阵返回空向量，null行抛出。空系数求值为0、null系数抛出；负一阶为空和，阶数超过系数长度抛出。|
|分段方法|写入标定样本后区间内外仍原值返回；null标定数组在低于Start时短路返回，其他被访问路径抛出。|
|私有圆拟合|通过反射直接调用完整FitCircle，四个已知圆点得到圆心(1,2)；共线点及空点集在当前MathNet路径下返回(NaN,NaN)，没有由原方法拒绝。未证明该私有方法存在生产调用。|

新增测试证明上述样本下的现有行为，并未修复产品算法。真实配置反序列化、持久化、现场MathNet运行版本、轴调用方安全契约、所有高阶拟合数值稳定性仍是剩余项。
## 高阶拟合与坐标尺度矩阵

已完成[108组人工样本矩阵](axis-fit-scale-review.md)：两种重载、三种已知曲线、六种样本数、三种坐标起点。验证多列表31点仍30阶、32点降15阶；所有组均返回系数，但非线性移位样本出现明显训练/中点误差。某15阶样本返回值修正为0.5、真实误差约0.690211，仍通过原幅度检查。该矩阵及六项行为断言不能替代全域稳定性或生产精度验收；噪声、条件数及实际配方仍需继续核验。