# 原点胶策略预处理与模型校验边界

两轮独立Framework CLR STA宿主各51个不同检查通过，实际执行仓库原EpoxyPretreatment、原模型校验/计算属性、静态数值校验与旧静态无操作入口。12源文件字节SHA与已审计清单一致；运行16个保真资源源程序集，162编译引用中10个源引用、运行映射172项。所选原IL60个方法体/1源程序集，其中45个Xtra提示重载是静态捕获，3个控制器/编辑器入口本轮仅静态IL。父6535+新增59=6594冻结绑定，未增正式1328回归或模块完成数。

## 三种策略实际执行的范围

使用原模型的两个位置(-2,-1,3)/(2,1,4)，SizeX=8、SizeY=6、原模型角度30加外部角度60、偏移SDK点(10,20,30)、SpindleSpeedPercentage=50。这里只执行原纯数据预处理，未执行三种策略对应的物理动作。

|原策略|预处理第一点|第二点|实际差异|
|---|---|---|---|
|SingleDotOnly|(10,20,33)|(7,24,34)|长度2的曲线仅第一点改为两点XY中点，第二点保留|
|Drawing|(13,16,33)|(7,24,34)|归一化后旋转90度并加偏移|
|Printting|(13,16,33)|(7,24,34)|纯预处理与Drawing相同，不代表蘸胶硬件行为相同|

实际原ObjectHelper.Clone使用BinaryFormatter.Serialize/Deserialize深拷贝：模型、列表、数组、点对象与原输入分离，原坐标/速度保持。原点Speed40/Acc200/Dec300变成20/100/150，EndSpeed99及名字、序号、类型、开胶、延迟和高度补偿字段保持。模型OffsetX777/OffsetY888留在克隆模型中，但本函数位置计算不使用它们；点Z只加偏移点Z，不使用模型OffsetZ999。

多曲线使用全局边界，SingleDotOnly只对长度2曲线的第一点取中点，长度3不走该分支。竖线与重合点的0除0先得到NaN，再在旋转前清成0；竖线X落在偏移X，重合点XY落在偏移点。第一条曲线为空时，后续正坐标(10,20)/(20,40)的极值仍包含初始化0，输出(0,0)/(4,3)；相同点作为首条非空曲线则首点(-4,-3)。这个差异不是探针替代算法，均来自原方法输出。

全部空曲线可用null偏移点成功返回克隆；非空路径则在归一化后解引用null偏移失败。null模型在原BinaryFormatter序列化时报ArgumentNullException，null列表/数组/点在后续原循环解引用失败。非正Speed/Acc/Dec在克隆中先分别补100/1000/1000，再乘百分比，原输入不改；百分比0/-50/200无配置范围守卫，NaN/Infinity继续传播。负SizeX反射X、零SizeY压平Y。NaN源X污染极值后所有X被清0；NaN角度在清理之后重新产生NaN XY，Infinity归一化X与零角度的0×Infinity也会污染Y。这里只核验明确列出的样本，没有穷举全部非有限组合。

## 原校验行为与数据提交

|校验入口|零值处理|非末点速度上限|末点/单点|
|---|---|---|---|
|DispenserMoveHelper.CheckEpoxyApplication|只对传值参数临时把0当10，模型保持0|调用通用检查，允许10000|跳过范围检查|
|EpoxyApplication.IsDataReasonAble / EpoxyIsReasonable|先遍历所有点，将Acc/Dec0改100、Speed0改10|专用速度检查，允许1000|先改零值，再跳过范围检查|

原通用检查0及10000、专用速度0及1000均允许；负值或超上限不允许。NaN比较不满足负值/超限，因此两种检查及两个模型入口都接受NaN运动数据；通用检查拒绝正/负Infinity，但末点负值/Infinity/超限仍跳过范围。单点曲线也无被检查的段，可以保留负速度。

静态helper接受非末点速度1001且无提示，模型入口拒绝并收集原速度1000提示。模型先修复所有点再检查先前点，因此早处无效加速度不阻止后续末点Speed0先变10；后续null曲线会在第一轮修复期间抛NullReference，之前的100/100/10修复已提交。helper可跳过null末点，模型修复第一轮则解引用该末点失败。

原AKRSXtraMessageBox经公开MainForm.SendUiAction提交5个真正的提示Action，探针只收集它们及真实中文提示，不执行Action，没有弹窗或模拟用户选择。4条无效范围路径返回false；第5条公开分发委托抛同一InvalidOperationException，使原方法不能返回false，之前的零值修复保持。finally恢复公开分发槽；DB Lazy始终未创建，未写SQL。

## 静态旧入口与真正控制器入口

原DispenserMoveHelper.Interpolation的有效IL没有任何call，直接返回ExcuteResult.Success；使用null模型/三个轴/IO/点及NaN安全高度的显式fixture确实返回Success。原OpenSafeDoor/CloseSafeDoor同样无call、直接返回。大量注释中的旧移动代码没有被执行。这些结果只能描述旧静态方法，不表示真实安全门动作或点胶成功。

真正DispenseController.InterpolationApplication原IL在预处理后把克隆写入编译器生成的闭包字段epoxyApplication，后续轴/阀/坐标/气压链本轮未执行。UcEpoxyApplication.InitPatternData则把同一个预处理返回值pop丢弃；BtEditPattern_Click调用模型EpoxyIsReasonable。3个调用方本轮仅捕获静态IL，既有窗体实际转换证据见[native-dispense-form-review.md](native-dispense-form-review.md)，不混同本轮范围。

## 执行与失败证据

首次80242d在48个检查后因探针把实际5个提示计作6个失败，原Cases/Host/已成功编译Probe与失败root保留。修正摘要计数后331836原生51通过；诊断明确callbacks=5/texts=5。重放输入8d963e因PowerShell展开内联JavaScript替换的捕获变量而丢路径分隔符，元数据引用读取失败、尚未到Emit；原接受Probe SHA未变、无该尝试的CLR重放执行，失败输入/空输出与观测单独保留。改为回调替换后66ae53独立重放编译/原生51与60方法IL通过。

首次预检8d9f39错误预期真正控制器用starg保存克隆；原IL实际保存到闭包stfld。保留失败脚本/日志后按真实IL校验，f34c8e通过。上述均是探针或编排修正，生产实现、SDK、程序集和工程未修改。接受两轮Probe SHA、51标签、结果、中文提示和诊断相同，16源程序集分别从bound/replay物理位置加载且与映射一致。37512/f5481e父点胶阅读器/保真资源绑定流水线通过，03e73e冻结和绑定通过。

未创建真实窗口/发送OS输入，未执行提示Action、真实设备/轴/阀/相机/SQL、完整控制器插补、生产Task/Retry或完整MSBuild/部署。本轮没有替换原算法、注入私有状态或改变生产源文件。全工程16项目/29组/1436文件/13项整体目标未完成，全部参数组合与物理策略验收也未完成。派生阅读器仍52专题5257快照，此份新报告尚未接入其冻结文件。

见[测试](native-dispense-policy-test.json)、[审计](native-dispense-policy-audit.json)、[进度](native-dispense-policy-progress.json)；原始结果与IL位于.archify-work/native-dispense-policy/，包括所有保留失败候选。
