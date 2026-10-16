# 胶头与吸嘴示教：状态产生和生产门控

更新：2026-09-28。限定范围：trunk内的S1/S2胶头向导、吸嘴高度/对准/几何完成委托，以及直接调用者和状态消费者。生产源码未修改；未连接设备。

[项目入口](index.html) · [27段带行号源码](tool-teaching-source.html) · [6项原代码隔离测试](tool-teaching-test.json)

## 工作流摘要

这组逻辑是由用户进入示教窗口、点击下一步/完成推进的设备准备流程，不是定时任务。结果包括设备位置参数、胶头补偿、吸嘴几何及示教状态；后续不同生产/试胶入口按各自条件读取这些状态，不能合并成一个统一的“已准备好”。

| 子流程 | 源码执行顺序 | 结果与边界 |
|---|---|---|
| S1胶头 | 进入→换胶位置→记录换胶/挤胶/擦胶位置→按胶型选择印胶步骤→测高并打标定胶点→相机对点→计算补偿→保存→完成 | 7个配置步骤；Dispenser类型在擦胶步骤额外增加索引，跳过印胶步骤。测高非Success减索引后返回；保存失败会抛出。 |
| S2胶头 | 检查硬件开关/胶头→换胶位置→记录换胶位置→记录挤胶位置→测高/打标定胶点→相机对点→保存/置完成 | 实际5个AssistantConfig；stepCount字段为6不代表6个实际步骤。测高失败可立即重试；选择No或异常保持当前步。 |
| 吸嘴高度 | 更换吸嘴入口→打开高度向导→手动/激光/真空测高→完成按钮调用DoneAction→写状态→保存 | 内部正常return不等于失败传递，外层仍会写ToolHeight=Able。 |
| 吸嘴对准 | 采样对准位置→计算圆形/矩形补偿及旋转中心→置对准状态→外层保存 | 矩形对准会将几何状态重置UnAble；离线委托提前返回，外层仍保存/返回OK，但未强行写对准Able。 |
| 吸嘴几何 | 矩形两点计算尺寸/偏移，或圆形三点FitCircle→委托返回→外层写几何状态/保存/OK | 圆形拟合异常的取消/重试返回，会继续进入外层完成逻辑。 |

步骤证据：[S1位置与分支](tool-teaching-source.html#s1-positions)、[S1测高](tool-teaching-source.html#s1-height)、[S2位置](tool-teaching-source.html#s2-positions)、[S2测高](tool-teaching-source.html#s2-measure)、[高度](tool-teaching-source.html#height-action)、[对准](tool-teaching-source.html#alignment-action)、[几何](tool-teaching-source.html#geometry-steps)。

## 保存与退出顺序

S1最终委托计算针头补偿，可询问是否清除已有全局偏移；随后依次System1Program.Save、DispenseDevicePara.Save、DispenserAssistant.State=Able、DispenserRepository.Save、DialogResult.OK。[原文](tool-teaching-source.html#s1-finish)

S2最终委托记录观察位、计算针头偏移与Z补偿、关闭测高气缸；随后也是System1Program.Save与DispenseDevicePara.Save，再写当前S2胶头Able并保存胶头库。这里明确记录源码实际调用，不替换成BondProgram.Save。之后移动安全位，可询问重置胶水寿命/累计次数。外层完成按钮再次移动安全位。[原文](tool-teaching-source.html#s2-finish)

S1进入时胶头为空只设置Abort，未立即return；S2对应检查会return。S1关闭处理释放定时器和引导控件；S2还调用关闭测高气缸。上述关闭代码不等同于全局异常finally保障；本轮没有实际运行WinForms关闭时序。[S1入口](tool-teaching-source.html#s1-load)、[S2入口](tool-teaching-source.html#s2-load)、[S1退出](tool-teaching-source.html#s1-close)、[S2退出](tool-teaching-source.html#s2-close)。

## 已证实风险及证据级别

1. **圆形拟合失败仍被标记完成。** FitCircle异常进入catch；选OK重置stepIndex后return，选Cancel写DialogResult.Cancel后return。但BtDone_Click继续写ToolGeometryAssistant=Able、Save、DialogResult.OK。隔离提取原委托及原按钮，已复现取消覆盖、重试索引与完成并存、离线完成、内层保存失败后外层再次保存、外层保存失败留下内存Able等6种场景。[委托](tool-teaching-source.html#geometry-circle)、[按钮](tool-teaching-source.html#geometry-button)。这是控制流缺陷证据，不代表已经在设备上复现。
2. **高度完成状态不是测量成功的严格证明。** DoneAction在离线、手动取消、测高非Success等路径正常结束；按钮仍写Able。该项为源码静态复核，本次6项执行测试仅覆盖几何完成，不包含高度向导。[原文](tool-teaching-source.html#height-button)
3. **保存、内存状态和界面结果并非事务。** 多个Save及状态赋值顺序不同，异常可能保留部分内存变化；实际写盘原子性、恢复行为由外部持久化实现决定，尚未验收。[外部依赖边界](persistence-dependency-boundary.md)

## 完成状态由谁消费

| 调用或门控 | 实际语义 | 源码 |
|---|---|---|
| 产品编程页面高度/对准回调 | ShowDialog返回OK可调用this.Start；该Start属于产品编程树/示教项分派，不可称为整机生产启动。几何回调刷新界面后执行放回吸嘴；对准路径放回调用被注释。 | [调用者](tool-teaching-source.html#nozzle-callers)、[Start](tool-teaching-source.html#program-start)、[分派](tool-teaching-source.html#program-dispatch) |
| Nozzle.IsAssistantSucceed | 读取高度、对准、几何三项；拒绝null或UnAble，并非严格要求每项都等于Able。 | [状态定义](tool-teaching-source.html#nozzle-states) |
| S1 DispenserProgram.IsReady | 检查胶头存在及IsAssistantSucceed。 | [S1](tool-teaching-source.html#s1-ready) |
| S2DispenserProgram.IsReady | 只检查胶头存在；提示文字“未示教”不代表检查过示教状态。不能据此断言所有生产入口都忽略示教。 | [S2](tool-teaching-source.html#s2-ready) |
| S2预点胶IsAlarm | 无S2硬件或两项预点胶设置均Off提前返回false；其余路径检查胶头示教、图形名称与板状态。 | [预点胶](tool-teaching-source.html#s2-pre-gate) |
| S2蘸胶生产路径 | Printting策略才查找指定吸嘴并检查IsAssistantSucceed，再换吸嘴；失败Abort，插补非Success为Alarm。 | [生产节点](tool-teaching-source.html#s2-print-gate) |
| 吸嘴架准备检查 | 排除TouchDown与BMC后判断未示教；构造错误名称的Find仅排除TouchDown，两处谓词不一致。 | [准备条件](tool-teaching-source.html#shelf-gate) |

## 可重跑验证及接手事项

- `node scripts/test-tool-teaching.cjs`：6种几何委托/按钮隔离场景。只为兼容C#5提升out变量声明、去除常量字符串插值前缀；未修改trunk源码。拟合算法、硬件、保存和UI均为替身。
- `node scripts/build-tool-teaching-review.cjs --check`：27段原文件、行号、原文、SHA-256和测试来源一致性。
- `node scripts/verify-tool-teaching-browser.cjs`：入口导航、搜索、27段原文/文件链接及多宽度页面检查。
- 工程师优先评审几何/高度完成协议：内部失败应如何通知外层，持久化和完成状态何时提交；修复生产代码、重新示教和真机验证均尚未执行。
- 待继续：剩余示教委托与辅助视觉搜索、运行时关闭/移动互锁、外部保存/重载实现、完整编译、真实配方和硬件验收。不能以本专题或测试数量替代完整验收。

## 当前项目进度

仍处于第2–3阶段的源码链路梳理与专题复核。本次补齐胶头/吸嘴示教状态到直接消费条件的一段链路；全局仍为29组部分复核、0组完整验收。新增27段是独立专题，不计入既有134段配置索引或552条代表关系，也未声称增加全模块覆盖率。[全项目计划与状态](project-plan-status.md)

本轮校验：27段证据与测试来源一致性、6项隔离场景、页面导航/搜索/文件链接、三种宽度及verify-all均通过。最终页面截图已人工查看。

关联后续专题：[自动换嘴与示教取放](nozzle-exchange-workflow-review.md)已补齐ChangeNozzleAssistance及PutbackNozzleAssitance内部真实动作链、返回传播和局部重试；仍未完成真机验收。
