# 自动换吸嘴与示教取放链路

更新：2026-09-28。范围：trunk源码静态追踪，不执行设备。

## 工作流摘要（先于绘图）

示教入口ChangeNozzleAssistance首先比较当前名称；名称相同直接成功。不同且目标已配置到吸嘴架、吸嘴架启用时调用ChangeNozzle，否则关闭工具真空、提示手动更换，确认后写当前名称并开启焊头真空。

自动ChangeNozzle在吸嘴架禁用时走人工确认；启用时比较逻辑/物理检测，按配置处理冲突，必要时PutbackNozzle，再TakeNozzle，最后MoveShelfToHome并返回true。这里最后的回原返回值未检查。

TakeNozzle：检查配置和槽位→Z安全位→异步吸嘴架伸出与焊头预取定位→等待架到位/角度检查→Z下压→开吸附→Z上抬→检测与有限自动重取/人工重新检测→可选后台吹气→Y退出→末次检测→槽位OnBondHead、当前名称、保存。

PutbackNozzle：配置/槽位检查→计算预还位并检查BMC高度→安全定位→异步伸架/焊头到预还位→关吸附→等待架到位/角度检查→Y送入→Z上抬脱离→Z安全位→检测/人工重新检测→槽位OnSlot、清空当前名称、保存。

示教结束PutbackNozzleAssitance另外封装人工与自动分支：人工提示取消仍可能返回true；自动分支没有检查PutbackNozzle的bool结果，却检查MoveShelfToHome的ExcuteResult。不能把返回true统一解释为设备确实完成取放。

[交互流程图](nozzle-exchange.html) · [29段原文/行号/源文件](nozzle-exchange-source.html) · [14项隔离测试](nozzle-exchange-test.json) · [节点/关系映射](nozzle-exchange.graph-evidence.json)。

## 入口与主链证据

- 示教窗口调用ChangeNozzleAssistance；高度/几何完成路径还调用PutbackNozzleAssitance，对准路径的放回调用被注释。调用方没有消费放回包装的bool结果。[页面调用者](nozzle-exchange-source.html#teaching-caller)
- 自动拾取节点先判断是否需要换嘴，ChangeNozzle返回false转Abort；随后读取当前吸嘴，若为null则抛异常。[拾取入口](nozzle-exchange-source.html#pick-caller)
- S2蘸胶策略先检查目标吸嘴及示教状态，再JudgeAndChangeNozzle；false转Abort。[蘸胶入口](nozzle-exchange-source.html#print-caller)
- 上述入口并不使用完全相同的包装。主图画JudgeAndChangeNozzle→ChangeNozzle的编排，不把编程页面this.Start误称为生产启动。[编排](nozzle-exchange-source.html#change)、[同名判断](nozzle-exchange-source.html#judge)

## 取嘴和放回的具体顺序

取嘴在Z到换嘴安全高度后，通过Task.Run伸出吸嘴架，同时焊头按目标槽位位置/角度运动；Wait后同时检查返回值和到位判断。随后慢速下压、开焊头吸附、上抬到放嘴高度、检测是否吸住、Y退出，最后再次检测并写状态。槽位检查可由人工Ignore跳到Continue，跳过这段机械取嘴动作。[定位](nozzle-exchange-source.html#take-position)、[夹持/重试](nozzle-exchange-source.html#take-retry)、[状态提交](nozzle-exchange-source.html#take-exit)

放回先检查配置和原槽位是否占用，计算预还位置并与BMC测高结果比较；Z抬起，必要时退到安全位置。伸架任务与预还定位并行，关吸附后Wait并核验到位。然后检查T角、Y送入、Z上抬3（源码数值，不据此推定设备单位）、Z回安全高度；检测、更新槽位和名称、保存。[前置](nozzle-exchange-source.html#put-gates)、[定位](nozzle-exchange-source.html#put-position)、[运动](nozzle-exchange-source.html#put-move)、[收尾](nozzle-exchange-source.html#put-exit)

## 分支、重试与异步边界

| 条件 | 实际行为 | 证据 |
|---|---|---|
| 当前名称相同 | Judge直接true；Take本身也有同名短路，不做物理复核 | judge / take-gates |
| DryCycle | 取嘴槽位检查只看配置；部分前后检测被绕过。中段吸附检测仍只受IsActiveToolDetection控制，不能说空跑完全不读硬件 | take-gates / take-retry / take-exit |
| 吸附检测失败且自动重试开启、次数未达上限 | 关吸附→抬到预取Z→次数加1→重新下压/吸附/上抬；不是整段重新定位 | take-retry |
| 人工Retry | 配置失败重新检查配置/槽位；吸附失败重读传感器；放回失败重新检测。不能统一画成完整机械重跑 | take-gates / take-retry / take-exit / put-exit |
| 人工Ignore | 某些检测失败允许继续并写逻辑状态，不代表硬件状态已被证实 | take-gates / take-exit / put-exit |
| 后台吹气开启 | Task.Run内置IsChangeToolBlowFinish=false→设置比例→开吹气→Sleep→关吹气→true；该任务没有在Take本方法等待或finally，调用方try/catch不覆盖任务体稍后的异常 | take-blow |

自动重试默认关闭，上限属性是double、默认2。这里描述的是源码默认值，不能当成现场配置。[配置定义](nozzle-exchange-source.html#retry-config)。上表证据ID均可在源码页搜索。

## 输入、输出与外部依赖

输入包括目标吸嘴名称、当前设备参数中的名称、配方选择的吸嘴架、库内槽位号/状态、G0取放位置和角度、BMC测高结果、真空/槽位输入、检测开关与重试配置、人工对话框选择。

输出包括AxisY/Z/T运动指令、吸附/吹气I/O、布尔或ExcuteResult结果、报警/日志、槽位OnBondHead/OnSlot和当前名称。SetCurrentNozzleName并非纯内存setter：写BondHeadParam后立即BondDevicePara.Save；取放收尾之后还调用NozzleShelfRepository.Save，两类保存不能当成事务。[setter](nozzle-exchange-source.html#name-save)、[读取来源](nozzle-exchange-source.html#name-model)

设备接口为轴运动、数字/模拟量输入与电磁阀输出。无HTTP或消息队列步骤出现在本专题方法里；不能由此断言整个项目无外部网络依赖。Save的实际写盘/恢复契约仍见[外部持久化边界](persistence-dependency-boundary.md)。

## 需要工程师优先复核的问题

1. **自动ChangeNozzle忽略吸嘴架回原返回值。** Putback/Take的false会中断，MoveShelfToHome的Fail/Abort不会阻止最后true；回原控制器本身可因单步许可返回Abort。此项已由原编排隔离执行证明。[编排](nozzle-exchange-source.html#change)、[回原控制器](nozzle-exchange-source.html#shelf-home)
2. **示教放回包装的成功语义不可靠。** 自动分支忽略PutbackNozzle的false，但回原非Success会抛出并被包装catch转false。人工分支中，Cancel未进入清名称块，却继续将找到的槽位写OnSlot并返回true。被找的槽位是第一个OnBondHead记录，不是按当前名称匹配。原包装已隔离复现上述结果。[人工](nozzle-exchange-source.html#teach-put-manual)、[自动](nozzle-exchange-source.html#teach-put-auto)、[槽位查找](nozzle-exchange-source.html#current-slot)
3. **到位判断的坐标分量不一致。** MoveShelfToChangeNozzlePos驱动转换后pos.Y；IsShelfAtChangeNozzlePos却拿当前Y与转换后.Z比较。源码差异已确认，是否导致现场误判需坐标配置与硬件验证，尚未修改。[原文](nozzle-exchange-source.html#shelf-position)
4. **物理检测有输出副作用。** 无参IsToolOnBondheadPhy先开焊头真空、等待200ms，再读数字输入或模拟值阈值；不只是只读查询。有参重载读取数值后直接return true，但本专题取放调用的是无参方法，不能混淆。[原文](nozzle-exchange-source.html#physical)
5. **方法名/注释不等于实际指令。** 模块MoveShelfToHome调用AxisY.AbsoluteMove(-1,true)，非等待版本发送0。槽位检测映射1–12号传感器，其他编号返回false。[回原](nozzle-exchange-source.html#module-home)、[槽位输入](nozzle-exchange-source.html#slot-inputs)

## 验证、覆盖与下一步

- 14项测试提取ChangeNozzle、JudgeAndChangeNozzle、IsNeedToChangeNozzle及两个示教包装原方法；为C#5兼容，仅把插值诊断字符串换成常量。取嘴、放回、运动、传感器、界面和保存均为替身。真实取放机械过程仅静态复核，未计入这14项执行验收。
- 29段源码保留文件、行号、原文和SHA-256；交互图11节点/11关系逐项绑定证据。图中重试边代表Take内部局部重取，并非递归调用完整Take；检测和Putback的全部提前退出保留在源码页而非堆入主图。
- 自动图由Archify生成，校验/交付与浏览器/人工视觉检查分别记录，不用一个绿色结果替代全部验收。
- 本轮没有修改生产源码、配方或设备参数。后续继续辅助视觉示教、位置信号/运动互锁和持久化契约，再做完整构建及实际配方/设备验收。整体仍为第2–3阶段，29组部分复核、0组完整验收。

本轮最终检查：verify-all通过；图交付、浏览器测量及人工查看分别留有回执。上游示教状态见[胶头/吸嘴专题](tool-teaching-state-review.md)，总体缺口见[项目计划](project-plan-status.md)。
