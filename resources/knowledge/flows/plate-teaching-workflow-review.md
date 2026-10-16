# 预点胶板示教：执行顺序与状态提交

更新：2026-09-28。范围：S1/S2 预点胶板向导及生产准备状态的衔接。静态源码复核，不操作设备。

## 已确认的 S1 顺序

Load 将当前系统设为 System1，将测高类型设为 TouchDown，先移动安全位置，再打开测高气缸，初始化三步委托。

1. 下一步调用测高。Success 写入局部 height；其他结果设置 DialogResult.Abort，但该委托没有 return，后面仍读取当前位置、赋 Z 并尝试相机移动。仅移动调用位于本地 try/catch；移动失败提示手动移动。
2. 记录预点胶板起点。
3. 完成时记录终点，循环询问列数和行数；TryParse 失败 goto 重问。Math.Abs 处理负数，没有大于零判断。Save 先写两端坐标、Z、高宽数量及 AssistanceFinish=true，再调用设备参数 Save；之后关气缸、移动安全位置、InitPre。

按钮调度没有把 NextAction 设计为返回状态：正常返回就 stepIndex++；DoneAction 正常返回后 Close。取消仅 Close，FormClosed 仅 Dispose 移动控件。不能据此认定取消会撤回状态或必定关气缸。

源码：`trunk/AKRS.ZX2200/DispenseSystem/Controls/Assistant/FrmDispensePlateAssistant.cs.cs`，96–357。

本轮已核对 S2 差异、测高包装、调用方退出清理和状态消费方，见下文。
## S2 执行顺序与 S1 差异

S2 Load 将当前系统设为 System2，先关闭点胶测高气缸，再初始化三步委托。第一步直接调用 BondHeadController.MeasureHeight(当前Z, WithTDSensor)，解构得到 Ret/value，却没有检查 Ret；将 value 转 G0 高度，然后尝试相机移动。此 try 内抛异常才进入 catch，提示后 stepIndex--；外层 BtNext_Click 随后 stepIndex++，使索引保持在原步。此处是用户再次点击触发，不能画成自动无限重试。提示写“激光测高失败”，但实际传参为 WithTDSensor，结论应以调用为准。

底层 MeasureHeight 包装取得搜索位置后进入另一重载。该重载调用 entity.DoWork；非 Success 弹 Retry/Cancel。Retry 跳回 ReMeasureHeight 再执行，Cancel 不改成异常，最终返回原 ret。因此向导未检查 Ret 的路径与 catch 重试路径不同；此处没有全局重试次数上限的证据。[底层源码](plate-teaching-source.html#s2-measure-return)

记录起点、终点及输入行列与 S1 基本同形；默认行数 S1 为5、S2为3，默认列数均10。两者 TryParse 失败都会重问，未见取消专门分支；零值可以通过 TryParse/Math.Abs，Math.Abs(int.MinValue) 则会抛异常。并不把反复提示称为有次数上限的自动重试。

S2 Save 修改 BondDevicePara.S2DispenseDevicePara.S2PreDispensePlatePara，设置 AssistanceFinish=true，然后调用 BondDevicePara.Save。返回后关气缸、MoveToSafePos、InitPre，DoneAction 正常返回才 Close。

## 退出清理必须结合调用方

- S1 手动页创建向导并 ShowDialog；对话框正常返回后，调用关闭测高气缸、MoveToSafePos。因此普通取消路径仍有调用方清理委托，不能只看 FormClosed 就断言“不清理”。这些语句不在 finally 中，异常退出时是否到达要另判。
- S2 手动页在 ShowDialog 后没有额外清理；向导 FormClosed 先 ucGuideMove.Dispose，再关闭气缸，未放 finally。不得声称所有异常情况下都能清理。
- 两个向导的 Load 会改全局 CurrentMachineSystem，在这些处理器中未见还原先前系统；没有在开始示教时将旧 AssistanceFinish 清零。取消不应被解读为清除旧示教资格。
- 两个 Designer 都存在 Back 按钮；在已读窗体实现与 Designer 中未见 BtBack.Click 绑定，也未见调用 BackAction。不能把可见按钮画成已实现的回退步骤。

## 状态如何进入生产门控

Save 的顺序是内存参数 → AssistanceFinish=true → 保存委托 → 后续清理/移动 → InitPre。S1/S2 PreDispensePlateProgram.IsReady 都只返回 AssistanceFinish，并不在此检查参数维度、真实文件状态或硬件位置。InitPre 按 Rows/Columns 分配网格，维度大于1才计算间距。不能把 IsReady=true 等价为“保存、清理和板位初始化全部成功”。

16项原方法隔离检查已通过：两个系统分别验证正常保存时的标志/引用顺序、保存抛异常后保留内存字段、Save 接受零维度、Next 正常推进、Next 委托异常不推进、UI 刷新异常后索引已推进、Done 正常关闭、Done 异常不关闭。[测试回执](plate-teaching-test.json)。原始 Save/Next/Done 方法未改写；模型、保存和UI是替身，不包含真实 WinForms 生命周期、完整三步委托、硬件或实际写盘。

S1 保存路径由 DispenseDevicePara 静态构造指定 DeviceDirPath/DispenseDevice.json；S2 的宿主 BondDevicePara 指定 DeviceDirPath/BondDeviceParaPath.json。Singleton 保存契约仍属于外部依赖边界，未加载运行设备程序集。

## 输入、输出与下层范围

输入：当前系统、测高类型、设备坐标、相机/焊头偏移、测高结果、用户选择的端点和行列数。输出：板参数、示教标志、保存委托、运行板位网格及UI/运动委托。

TUAssistantHelper.AssistantMeasureHeight：OffLineWork 直接返回 Success/0；S1 TouchDown 路径把底层结果直接返回。GetPosBySystem：OffLineWork 仍调用 S1 GetG0Pos；在线按当前系统读取位置并按相机类型补偿，非空坐标系再做转换。因此“离线”不能一概扩写成所有入口都无控制器调用。

尚未完成：所有胶头/吸嘴及其他示教窗口的完整委托、测高实体驱动运行、全程异常注入与WinForms事件时序、实际配置写盘/重载、全工程构建和设备验收。本专题不提升29模块组的整体验收状态。

[源码证据阅读器](plate-teaching-source.html) · [项目总入口](index.html) · [试胶调用衔接](manual-epoxy-trial-summary.md)

## 工程师复核索引

|问题|源码证据|
|---|---|
|从哪个按钮触发，退出后谁清理|[S1入口](plate-teaching-source.html#s1-entry)、[S2入口](plate-teaching-source.html#s2-entry)|
|测高失败是返回还是重试|[S1委托](plate-teaching-source.html#s1-height)、[S2委托](plate-teaching-source.html#s2-height)、[底层重测](plate-teaching-source.html#s2-measure-return)|
|行列输入、保存、移动的先后|[S1完成](plate-teaching-source.html#s1-finish)、[S2完成](plate-teaching-source.html#s2-finish)|
|何时设置示教完成|[S1保存](plate-teaching-source.html#s1-save)、[S2保存](plate-teaching-source.html#s2-save)|
|如何推进步骤和关闭窗口|[S1调度](plate-teaching-source.html#s1-dispatch)、[S2调度](plate-teaching-source.html#s2-dispatch)|
|实际事件绑定与取消|[S1按钮](plate-teaching-source.html#s1-bindings)、[S2按钮](plate-teaching-source.html#s2-bindings)、[S1生命周期](plate-teaching-source.html#s1-load)、[S2生命周期](plate-teaching-source.html#s2-load)|
|生产准备如何判断|[S1 IsReady](plate-teaching-source.html#s1-ready)、[S2 IsReady](plate-teaching-source.html#s2-ready)|
|参数保存到哪里|[S1宿主](plate-teaching-source.html#s1-owner)、[S2宿主](plate-teaching-source.html#s2-owner)、[S1路径](plate-teaching-source.html#s1-path)、[S2路径](plate-teaching-source.html#s2-path)|
