# 点胶图形编辑、配置回写与模板文件

更新：2026-09-28。本轮覆盖AKRS.Galaxy2.Dispense的编辑器输入输出、模板读写，以及ZX2200的胶路配置桥接。未执行点胶、运动或生产文件写入。82个源文件未全部复核。

## 实际工作步骤

1. UcEpoxyApplication.BtEditPattern_Click由维护界面进入；将当前DispensePatternParas转成EPEPointData，再创建EPEData，传入EpoxyPatternForm.SetContent并ShowDialog。这里的图像为新建500×500位图，像素比1，Die尺寸3500×4200，并非本入口实时采集的相机图像。见[编辑入口238–283](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L238)。
2. 出站转换将X/Y乘1000，回写除1000；携带加速度、速度、时间、开胶标志等参数。出站包含EndSpeed，但InitPatternData回写没有给EndSpeed赋值，Dec则取Info.Acc，不能将编辑往返称为全部参数无损转换。见[出站291–328](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L291)、[回写334–369](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L334)。
3. 编辑器SetContent将曲线与背景交给控件，GetContent从GetFigure取回曲线并构建新EPEData。EPEData校验像素比、宽高大于0；逐个复制点数组。EPEPointData和EndpointSetting为struct，但背景对象的资源生命周期不能从数组复制推出。见[编辑器接口1219–1279](../../trunk/AKRS.Galaxy2.Dispense/EpoxyPatternForm.cs#L1219)、[数据构造](../../trunk/AKRS.Galaxy2.Dispense/EPEData.cs#L61)、[点结构](../../trunk/AKRS.Galaxy2.Dispense/EPEPointData.cs#L9)、[参数结构](../../trunk/AKRS.Galaxy2.Dispense/EndpointSetting.cs#L6)。
4. DialogResult.OK时先清空原胶路，再GetContent并InitPatternData回写；随后读取EpoxyIsReasonable，不合格goto RetryCommand重新打开编辑器。此处为人工编辑重试，不是生产任务自动重试。第二次窗口若取消，前一次已回写数据没有在此处理器中恢复；初次取消则不进入OK回写块。异常也没有finally保证释放编辑器。见[确认与重开266–283](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L266)。
5. IsDataReasonAble先将所有点的零Acc/Dec改为100、零Speed改为10，再对每条曲线末点以外的点校验：加减速度0–10000、速度0–1000；失败弹框返回false。它会修改数据，不是纯检查；没有在本方法排除空曲线或显式检查有限数。见[校验282–332](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Repositories/Pattern/EpoxyApplication.cs#L282)、[阈值513–545](../../trunk/AKRS.ZX2200/DispenseSystem/Services/DispenserMoveHelper.cs#L513)。
6. InitPatternData调用EpoxyPretreatment但忽略返回值；该方法先ObjectHelper.Clone、末尾return epoxy，不能将此调用描述为已经用返回结果替换原胶路。克隆内部语义仍属外部边界。见[调用366](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L366)、[克隆327–330](../../trunk/AKRS.ZX2200/DispenseSystem/Services/DispenserMoveHelper.cs#L327)、[返回445](../../trunk/AKRS.ZX2200/DispenseSystem/Services/DispenserMoveHelper.cs#L445)。
7. 编辑窗口OK不等于落盘。UcEpoxyApplication.Confirm另行写入界面参数，最后依次调用EpoxyApplicationRepository.Save和System1Program.Save；没有一体事务。本轮进一步确认了参数变化事件和两个测试按钮的Confirm入口，见下节；其他宿主窗口的确认/取消语义仍待核实。见[Confirm483](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L483)、[保存544–545](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L544)。

## 模板文件支线

模板库位于执行程序集目录下PatternRepository，不等同于当前配方目录。添加模板：选择文件→GetContent→PatternFile.SaveFile→写Snapshoot_名称.bmp。SaveFile若有背景图先写同名.bmp，再通过SXml写.ep文件，包含尺寸、矩阵、默认参数和每段点参数；没有局部catch或跨文件回滚。任一步失败可能留下部分文件。见[路径130–136](../../trunk/AKRS.Galaxy2.Dispense/EpoxyPatternForm.cs#L130)、[添加1187–1206](../../trunk/AKRS.Galaxy2.Dispense/EpoxyPatternForm.cs#L1187)、[文件保存46–108](../../trunk/AKRS.Galaxy2.Dispense/PatternFile.cs#L46)。

取回模板：ReadFile无条件先将同名.bmp复制成tmp_时间戳.bmp并打开，再读XML重建EPEData；异常Console.WriteLine并返回null，调用界面弹失败提示。因此缺失背景BMP可使读取失败，即使.ep本身存在。ClearTmpFiles可删除tmp_*.bmp且吞掉逐文件删除异常，但本次在该模块只找到定义，不能宣称已经自动清理临时图。见[读取110–198](../../trunk/AKRS.Galaxy2.Dispense/PatternFile.cs#L110)、[清理27–44](../../trunk/AKRS.Galaxy2.Dispense/PatternFile.cs#L27)、[读取界面1153–1177](../../trunk/AKRS.Galaxy2.Dispense/EpoxyPatternForm.cs#L1153)。SXml内部序列化与资源释放需另核。

## 与生产链的关系及剩余工作

本专题追踪维护编辑器到业务配置的数据桥接，不把图形控件当作设备控制器。生产运动另见[点胶运动源码复核](dispense-motion-source-review.md)、[点胶模块复核](dispense-system-module-review.md)。S1与S2的显式名称解析及生产消费均已在下节连通；宿主界面隔离和全部字段的运行结果仍待验收。不能预设所有路径都必须重建独立运行实体。

待验收：EndSpeed/Dec编辑往返、校验失败后取消、空曲线/非有限数、模板BMP缺失、XML写失败、截图失败和临时图锁定。鼠标动作处理器、曲线几何操作、模板管理删除、全部字段持久化与构建运行尚未覆盖。所有静态风险均未现场复现。

## 补充：保存入口到S1生产消费

- UcEpoxyApplication_Load在Init和预览刷新之后，为SpSizeX、SpSizeY、SpComponentX、SpComponentY、SpAngle绑定EditValueChanged；该处理器调用Confirm再刷新预览。BtTest_Click和BtTestInPrePlant_Click也先调用Confirm，随后才进行各自的测试检查和分派。因而修改参数或点击测试即可触发保存，不是只有某个最终确认按钮才落盘。见[绑定98–112](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L98)、[事件1146–1150](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L1146)、[测试595–614](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L595)、[预点胶测试968–976](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L968)。此处没有推断运行中编辑一定被允许，权限/互锁由上层另查。
- EpoxyApplicationProgram保存名称列表；EpoxyApplications为JsonIgnore的计算属性，每次读取通过名称查仓库，返回对象列表，没有在该Find方法内Clone。找不到名称时会RemoveAt(i)，同时for继续i++，因此相邻缺失项可能在当次查询被跳过；读取这个属性具有修改名称列表的副作用，且该方法未保存修改。见[程序列表17–53](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyApplicationProgram.cs#L17)。这是列表解析行为，不能误认为每次都建立隔离的生产快照。
- S1ActionNodeController.CurrentEpoxyApplication直接用CurrentProcessStep?.EpoxyNameApplicationName查EpoxyApplicationRepository。不是读取上述计算列表后按索引取值，也没有在这个getter内等待保存或重新读取磁盘。见[当前胶型98](../../trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs#L98)。仓库Find返回对象的定义见[本地基类100–105](../../trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs#L100)。找不到时返回null，getter不提供默认胶型。
- S1DispenseActionNode在单步等待、预点胶及WaitStart检查之后取CurrentEpoxyApplication，再读取OffsetX/Y生成目标，叠加焊点和设备位置补偿，按DryCycle生成isDrip并计算角度，交给InterpolationApplication。非Success转Alarm；成功才标记步骤完成并刷新统计。见[生产消费87–116](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs#L87)。这里证明调用路径，不证明真实胶阀动作或运动已验收。
- InterpolationApplication转换坐标并将EpoxyPretreatment返回值重新赋给局部epoxyApplication，再按预点胶/普通路径调整Z，循环DispensePatternParas。与维护界面忽略返回值不同，这个生产调用确实消费预处理返回结果。见[控制器300–340](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs#L300)。预处理开头调用外部ObjectHelper.Clone；克隆深度、并发一致性和数据是否可被同时编辑仍未证明。

S1显式配置消费路径已连接；S2的缓存更新见后续补充。名称选择/删除、运行中编辑隔离、缺失胶型的全链错误呈现和所有轨迹字段仍需验收。

## 补充：S2动作选择、缓存与点胶消费

### 实际服务归属

System2Domain.ActionNodesService明确声明为S2ActionNodeController并直接new该类型；S2DispenseActionNode也以该类型访问。不能因为目录下存在System2ActionNodesService，就把同名GetCurrentEpoxyApplication方法当成生产调用目标。见[Domain113](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L113)、[动作43](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs#L43)。

### 执行顺序

1. GetNextActionNode从WorkMessages选第一个未完成项，更新CurrentBondActionNode并ChangeNameToActionNode。后者查动作对象，再InitCurrentMessage，最后返回动作。没有剩余项时返回null。见[调度1042–1092](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1042)。
2. InitCurrentMessage按当前消息的ProcessStepName找ProcessStep，非null时用EpoxyNameApplicationName查仓库并赋给this.EpoxyApplication；GetCurrentEpoxyApplication只返回该字段。因此S2在动作选择阶段缓存对象引用，S1则在CurrentEpoxyApplication getter中即时查名；两者不能统一描述成每次getter都重新加载配置。见[更新930–941](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L930)、[返回1016–1019](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1016)。
3. S2DispenseActionNode先单步等待，再WaitStart；预点胶非Success转Alarm，随后再次WaitStart。再取当前焊点和缓存胶型，计算带胶型OffsetX/Y的G0目标，叠加焊点点胶位置补偿；按DryCycle生成isDrip，计算坐标系角度与焊点旋转补偿。见[前置50–100](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs#L50)。
4. 策略为Printting时，先查PrintNozzleName；吸嘴不存在或未示教抛异常，JudgeAndChangeNozzle返回false则Abort。之后S2DispenseController.InterpolationApplication非Success转Alarm；成功才标记S2步骤完成和刷新统计。见[分支104–135](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs#L104)。
5. S2控制器将G0转机械坐标；Printting叠加当前吸嘴偏移，其他策略换算到点胶头位置。将EpoxyPretreatment返回值赋回局部胶型，选择预点胶或普通Z偏移，再循环胶路点组。见[控制器226–284](../../trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs#L226)。这与S1共用预处理方法，但机械坐标/工具分支不同。
6. 动作try内异常记录日志并弹窗，返回Exception；finally设置State.Stop并触发WorkStop。WorkStart在try外；该finally没有统一关胶阀、回安全位或回滚配置。见[开始50–53](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs#L50)、[异常177–187](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs#L177)。不据此推断物理设备最终状态。

### 缺失和静态风险

- ProcessStep为null时，InitCurrentMessage不进入胶型赋值块，也没有else清空旧胶型；在此前存在缓存的情况下可能保留旧引用。ProcessStep存在但胶型名未找到时则赋null。后者在动作读取OffsetX/Y时无局部空值检查，try内异常会进入Exception返回路径。是否可由正常配置触发，仍需构造离线案例及追踪上层防护。
- ChangeNameToActionNode先调用ActionNodes.Find，再检查ActionNodes本身是否null，没有检查找到的actionNode是否null；不能把其错误提示视作完整的动作不存在保护。见同一调度证据。
- 此缓存是对象引用，不是已经证明隔离的深快照。在缓存后替换仓库对象与修改原对象字段，会有不同引用可见性；源码此处没有版本绑定、锁或原子配置切换保证。上层编辑权限和线程调度仍待核实，未声称现场一定发生竞态。
- 本轮覆盖S2显式参数消费与策略分支；驱动回执、异常停止安全、S2预点胶全部路径及运行中编辑隔离仍需独立验收。未执行设备程序。

## 2026-09-29 管理删除补充

两类管理窗口及8处Designer事件绑定已复核，20项原类/临时文件隔离断言通过。详见[删除管理报告](dispense-repository-delete-review.md)。图像索引仅为List替身验证；原生控件、曲线算法、鼠标处理及完整产品构建仍待验收。
