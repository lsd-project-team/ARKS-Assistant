# 手动试胶：执行步骤与验收边界

更新：2026-09-28。范围仅为 UcEpoxyApplication 的两个按钮处理器及已登记的 Confirm。手动试胶不是自动生产循环，也不代表全工程完成。

## 简明流程

两个入口都先 Confirm：写入当前胶型对象并依次委托胶型库 Save、System1Program Save，然后才检查运动条件。普通试胶在 try/catch 内调用；预点胶板试胶没有本地 catch。

系统选择条件相同：当前为 System2，且启用 System2 点胶，或启用 System2 蘸胶工具且胶型策略为 Printting。其余情况走 System1。

1. 普通试胶：选择焊点 → 校验胶头或蘸胶吸嘴与载具 → 新建相应系统 TransportUnit → 基板、基岛、焊点依次执行视觉定位和测高 → 按策略预点胶 → 计算并补偿目标点和角度 → S2 蘸胶按需换嘴 → InterpolationApplication → 仅 Success 才移动相机观察位置并显示视觉画面。
2. 预点胶板试胶：Confirm 后置 IsFirstDispense=true → 校验胶头或蘸胶吸嘴（S2 蘸胶先尝试换嘴）→ 校验预点胶板 → GetEpoxy 取位置，null 则返回 → InterpolationApplication → 未检查返回值就执行后续移动和画面切换。正常返回 Fail 不阻止该处理器后续代码；抛出异常则不能据此说仍会继续。
3. 普通试胶存在多个提前 return；catch 提示并记录后重新抛出。两个按钮本身没有自动重试循环。源码中的“重试”提示文字不是循环证据。

## 系统差异与重要边界

|环节|System1|System2|源码位置（同一 UI 文件）|
|---|---|---|---|
|普通试胶前提|焊点、DispenserProgram.IsReady、现有载具非空|焊点、蘸胶吸嘴存在且示教成功或 S2DispenserProgram.IsReady、现有载具非空|610–646；790–813|
|新载具与分段|新建后 SetSystem1OffSet；Divide 时按 IsTuInDispense1 分支检查 Back/Front 索引，另一分支调用 System1MoveDistance|校验原载具后新建，不直接沿用原对象|646；811–844|
|逐层定位测高|基板→基岛→焊点；该处理器没有逐层 Find 结果显式 null 门控|基板→基岛→焊点，每层先检查 Find 结果非空|656–726；819–879|
|预点胶|调用 PreDispenseAction.DoWork，未检查返回值|非 Printting 才调用 S2PreDispenseActionNode.DoWork，未检查返回值|735–741；884–886|
|目标与出胶|焊点偏移、点胶补偿、设备 DispenseOffset；DryCycle 参数 isDrip=false|焊点偏移、点胶补偿；DryCycle 参数 isDrip=false；Printting 换嘴失败返回|747–769；892–902|
|普通试胶结束|Success 后计算观察点、MoveToG0Pos3D、VmVisionShow|Success 后关测高气缸、VisionMoveToG0Pos、VmVisionShow|768–780；902–911|
|板上试胶前提|只显式检查胶头非空且名称不为空，再检查板 IsReady|蘸胶检查吸嘴和换嘴；其他策略检查胶头非空且名称不为空，再检查板 IsReady|980–1025；1042–1061|
|板上试胶参数|传 true,true,0|传 true,true,false,0；此处没有 DryCycle 判断|1028；1063–1068|
|板上后续动作|MoveZToSafePos，观察点叠加 PrePlantOffSetZ，移动、显示、切换 DispenseCamera|关气缸，位置 Z 叠加 PrePlantOffSetZ，移动、显示、切换 BondCamera|1030–1038；1070–1079|

## 输入、输出与外部边界

输入：UI 胶型与焊点/基板/基岛选择、当前系统、硬件配置、MachineWorkMode、产品载具配置、胶头/吸嘴/板示教状态。输出：内存胶型修改、Save 委托、视觉/测高/运动委托、日志与观察画面。源码没有在这两个处理器中建立“设备物理动作完成”的独立回读验收。

外部持久化、完整产品对象构造、Vision SDK、运动控制卡、实际配方和机械动作不在本图验收范围。普通试胶中的 RecordTime“完成”文本不能用作硬件完成证明。GetEpoxy 可能有板位分配副作用，不能把它画成无副作用的读取；其内部详见既有预点胶分配专题。

## 源码入口

- `trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs`：Confirm 483–546、普通试胶 595–922、板上试胶 968–1081。
- `trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.Designer.cs`：按钮绑定 1018–1034。
- [既有源码阅读器](config-production-gates.html)：epoxy-confirm、epoxy-teach-preplant、epoxy-teach-s1-return、epoxy-teach-s2-return。
- [项目计划与剩余工作](project-plan-status.md)。29 组仍部分复核，0 组完整验收。

下一步优先剩余示教委托和持久化类型边界，随后完整构建及可获得的真实配方验证。本专题仅做源码静态解释，不操作设备。

## 图示与完整源码索引

[Archify 双路径工作流](manual-epoxy-trial.html) · [节点与关系源码阅读器](manual-epoxy-trial-source.html) · [机器可读映射](manual-epoxy-trial.evidence.json)。

上游准备状态来源已补充：[预点胶板示教步骤与保存边界](plate-teaching-workflow-review.md)。板的 IsReady 只读取 AssistanceFinish，不能从这个标志推导真实写盘、清理和板位初始化均已完成。
