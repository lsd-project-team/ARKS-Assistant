# 自动对焦：模块职责、执行链路与缺口

更新：2026-09-28。仅对当前源码作静态复核；不运行设备、不修改生产源码，不宣称全模块或实机验收完成。

## 简明流程

定位步骤读取当前物料P1/P2/P3/P4配置 → 按 Autofocus 开关进入对焦 → 控制器选择相机、Z轴和搜索范围 → 移到下界并粗扫采图 → 按清晰度选取粗扫位置 → 六轮变步长细调 → 方法正常返回后继续视觉定位。另有界面辅助、晶圆相机与标定入口。对焦是条件步骤，不是每次定位必做，也不是独立定时任务。

## 入口和上下游

- [GetVisionInfo，472–492行](../../trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs#L472)：四种定位类型分别读取 LocateUseConfig1–4.Autofocus，其他类型抛异常；具体生产配方值未核实。
- [System1Domain vision dispatch，229–243行](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L229)、[System2VisionByPos，444–465行](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L444)：将配置开关传入点胶/邦定视觉控制器；所引用调用分别位于 !alarm、!manuelVision 分支。
- [DispenseVision，123–169行](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseVisionController.cs#L123)、[BondCameraVision，159–235行](../../trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs#L159)：准备运动/光源之后，if(autofocus) 执行对焦并重取当前位置，然后才检查 DryCycle。故这些入口的空跑提前返回不能阻止已经发生的对焦调用。邦定视觉的重试循环在对焦之后，不能据此称对焦具备相同重试次数。
- [AutoFocus，269–280行](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseVisionController.cs#L269)：当前点胶Z位置±3，使用点胶相机与点胶Z轴。[AutoFocus，1000–1042行](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L1000)：邦定相机用BMC标定Z±3；上视相机用上视位置Z加吸嘴偏移±3；都驱动邦头Z，未知枚举抛异常。
- [AutoFocusAssistance and AutoFocus，916–972行](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs#L916)：界面按钮禁用变色，Task.Run 调用对焦，catch弹出错误，finally恢复按钮；该恢复仅处理UI，不是轴回退或资源清理。
- [Autofocus，1194–1202行](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L1194)：晶圆相机及其Z轴，以左标记标定Z±5为范围；本段证明控制器能力，不能单凭方法存在认定生产每周期调用。
- [AutoFocus dispatch，267–290行](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs#L267)：Bond和UpLook分支在当前源码均传入BondCamera和BondHead.AxisZ，参数顺序为endPos、startPos。这与枚举名称的预期可能不同，需继续结合标定调用方验证；不自动改写为上视相机。

## 算法执行顺序

1. [AutoFocus coarse scan，215–257行](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L215)：AbsoluteMove(nLimit)，distance=(pLimit-nLimit)/5，pulse=distance/5；循环先RelativeMove(distance)，再SnapImage(false,false)、评分并记录实际轴位置。下一步位置将超过pLimit时退出粗扫。下界本身没有先采样；实际次数取决于轴反馈，不宣称恒定五张。
2. 粗扫最大值使用 >= 比较，同分时选择后面的样本；AbsoluteMove 到选中的已记录位置。
3. [AutoFocus fine search，259–312行](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L259)：T递增、Round=6。每轮第一张之后先走pulse；第二张若更清晰则保持方向，否则pulse反向。后续评分继续上升就继续移动；不再上升且T<6则pulse乘-0.5、重新开始下一轮。
4. 第六轮不再上升时直接break。虽然注释写“返回峰值”，该分支没有回退到上一张较清晰位置的轴命令；也不返回最佳Z、评分或成功标志，接口返回void。不能把正常返回等同达到质量阈值。
5. [CalSharpnessVm，371–393行](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L371)：每次评分创建VisionDesigner CImageSharpnessTool和CMvdImage，配置SquaredGrad，Run后返回Result.Sharpness。[BitmapToCMvdImage，396–457行](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L396)：8bpp转换为Mono8，24bpp逐像素BGR转RGB，随后UnlockBits。其他格式无明确拒绝或初始化分支；UnlockBits没有finally保护。

## 失败、终止和外部边界

- AutoFocus方法没有本地catch、取消令牌、超时、总采样上限或nLimit<pLimit参数校验；细调阶段没有显式范围比较。六轮只限制出现下降后的轮次，不限制单轮持续上升时的迭代数。
- pLimit==nLimit时distance为0，粗扫的退出条件不会因该方法自身移动而满足；这是一条源码边界分析，不是已执行的设备故障复现。反向范围及反馈不更新也需验证。
- 没有独立的轴到位等待调用；AbsoluteMove/RelativeMove是否同步、是否含限位/超时保护，取决于外部Axis实现，不能从本方法断言无保护或已保护。
- 采图、运动、SDK评分的异常可离开算法；UI包装能捕获异常，但本轮未证明全部生产调用链的恢复行为。
- 采样Bitmap、评分工具、转换图像在所读路径未见Dispose/using；资源所有权和长期运行影响待结合SDK契约确认，不能直接宣称实测泄漏。
- 本方法不访问数据库、文件或持久队列；输入为相机、轴、上下界，主要输出是轴位置副作用。配置保存归属上层，不应虚构算法内保存步骤。

## 后续缺失项

- 完整展开标定、晶圆和UI调用方，以及异常如何沿生产任务栈传递；验证参数方向与相机选择。
- DoFocusing、DoFocusingNew、DoFocusingNew2另有实现；本次全文C#文本检索只找到其声明，未证明反射或外部程序集不调用，未将其混入已确认AutoFocus链路。
- 核实实际配方开关、搜索范围单位、相机像素格式、轴与VisionDesigner SDK版本及同步/资源契约。
- 在受控验证环境测试等边界、超范围、停止/急停、设备异常和最终焦点质量；不得直接在生产设备运行本审计。
- 本轮先落源码摘要和证据，新增专题图及与主图的交互整合尚待完成。
