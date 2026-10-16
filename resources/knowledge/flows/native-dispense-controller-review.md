# 原点胶控制器坐标准备与插补失败边界

两轮独立Framework CLR STA宿主各40个不同检查通过。使用真实System1Domain中的原DispenseController及原模块，执行坐标/配方查找、10次真正InterpolationApplication入口调用，以及安全移动/压力/阀/蘸胶盘/插补群组的缺失依赖路径。24源文件字节SHA与原编码清单一致；162编译引用中10个源引用，运行16个源程序集，映射172项。原IL99个方法体/1源程序集，含45个提示重载及1个压力Task闭包仅静态捕获。父6594+新增59=6653冻结绑定，未改变正式1328回归或29组partial状态。

## 真正控制器入口的实际失败传播

每轮10次原InterpolationApplication调用，前9次收集原提示Action后返回ExcuteResult.Fail；第10次公开UI分发槽抛同一InvalidOperationException，原catch不能返回Fail。仅收集10个真正的Action及中文消息，没有执行Action、显示提示或伪造用户选择。

|调用|明确的公共fixture/原前提|实际失败层|
|---:|---|---|
|1|没有名为DispenseCoordinateSystem的坐标系|转换坐标解引用null，catch提示后Fail|
|2|添加真实SDK GeneralCoordinateSystem|两个原标定点仍null，坐标点运算失败|
|3|公共标定点赋值，配方选择不存在的点胶头|DispenserRepository.Find返回null，针偏移访问失败|
|4|原仓库加入未示教点胶头，胶型为空列表|仍执行末尾安全Z移动，真实点胶Z轴缺失|
|5|null胶型模型|原BinaryFormatter不能序列化null图|
|6|胶型列表null|原克隆预处理解引用列表Count|
|7|首条曲线长度0，蘸胶配置关闭|读取第一个点越界，尚未创建压力Task|
|8|同样空曲线，启用蘸胶硬件且点胶头为PrintingTool|原PrintEpoxy先停止盘，真实蘸胶T轴缺失；先于首点访问|
|9|null输入点|原SDK一般坐标转换解引用失败|
|10|空胶型+正常fixture，提示分发委托抛出|最终Z缺失触发catch，提示分发异常替代原Fail|

这不是旧静态DispenserMoveHelper.Interpolation的无操作Success，详见[策略核验报告](native-dispense-policy-review.md)。本轮确实进入真正控制器的try/catch，但均在创建压力Task之前或空列表跳过循环后失败，没有执行物理点胶、轴/阀动作或成功制程。

原IL确认顺序为PrintEpoxy、首点访问、new Task；压力闭包单独捕获，内部DryCycle/PrintingTool跳过或调用SetDispensePressure仅属静态证据。空列表跳过循环后仍调用AxisZAbsoluteMove，故不是“没有路径就成功返回”。原入口catch只提示并返回Fail；没有finally保证关闭阀、回安全位置或取消压力Task的本地逻辑，本轮未进入这些设备支路，不据此声称实际遗留状态。

## 坐标与仓库模型

名为DispenseCoordinateSystem的真实SDK一般坐标模型未接父级时，原G0PosToSelf/SelfPosToG0忽略其自身(10,20,30)/90度转换，输入(1,2,3)保持。添加真实父级引用后，机器点(1,2,3)转换成G0(8,21,33)，逆变换回(1,2,3)；根自己的(100,200,300)/180度不进入变换。两个同名模型同时存在时，原Find选择第一项，没有重复名拒绝。这是显式构造的公共SDK模型，不是实际机台标定或VM算法验收。

原标定点M(1,2,3)、H(4,6,8)下，GetG0VisionPos将输入(10,20,30)映射(7,16,25)，GetG0PosFromVision回到输入，输入点保持。选中原仓库点胶头的针偏移(2,3,4)、设备传感器高度5后，GetG0DispensePos输出(5,13,26)。点胶头IsAssistantSucceed=false，但直接坐标方法并不调用其就绪谓词；这不代表自动任务可以跳过就绪门。

未发送坐标到硬件，没有修改SDK算子或控制器实现，也没有私有字段赋值/Singleton替身。配置、坐标列表、父级、原仓库选择、标定点和设备参数均为本隔离宿主的公开fixture，未执行示教/实际标定或完整生产任务。

## 模式、压力与缺失硬件

OffLineWork的GetG0Pos直接执行原GetRanDomPos，原IL三次Random.Next(0,100)，当前观察值在0至99范围；没有把它当真实轴位置，也没有测试随机分布。OffLineWork的MoveToSafePos/MoveZToSafePos提前返回，未要求气缸或轴。DryCycle的GetG0Pos则访问真实轴并在点胶X缺失处异常；MoveToMachinePoint同样在读取当前轴Z之前的X查询失败，后续安全移动比较分支尚未执行。

非离线且配置气缸时，安全Z移动触及实际缺少的测高气缸依赖；配置激光测高会跳过气缸，再在点胶Z缺失处异常。GetIpolGroup在点胶X查询失败，尚未读取ETEL驱动或建立DsaIpolGroup。没有提供假Axis/控制卡或替代硬件。

IsLinkDispenser=false时，原SetDispensePressure即使传NaN/Infinity也直接返回；开启链接后，实际模块因没有点胶控制器失败，外层catch转为普通Exception“设置点胶阀参数出现问题，请修改后重试”，InnerException为空。上/下气压钳制源码/IL已捕获，但本轮没有在硬件测得最终压力、真空或串口命令，未确认实际气压限制行为。阀开/关/读取都在原缓存电气IO缺失处失败；蘸胶盘运行/停止/状态都在真实T轴缺失处失败。

## 原硬件名称声明

原GetHardWareNames在系统1禁用时返回空列表。启用时四种分支实际执行，名称数量如下；这只是声明列表，不是连接/可用设备数量。

|光源配置|激光测高|返回名称数|
|---|---|---:|
|MonochromaticLight|true|12|
|MonochromaticLight|false|15|
|TrichromaticLight|true|16|
|TrichromaticLight|false|19|

四组都把“点胶相机”列两次，激光/气缸分支按配置变化；即使IsSystem1ConfigPrintingTool=true，列表仍不包含“蘸胶T”。这与前述真实PrintEpoxy尝试取得T轴的失败入口分别核对，不意味着当前声明函数是全部设备依赖清单。

## 冻结与范围

首轮42509/28f610编译与原生40通过；独立重放71471/ed4f1d原生40及初始98方法IL通过。97db57加入原压力闭包静态IL为99，原98输出与提取器保留，本轮没有失败候选或重新执行压力闭包。68050/e108ac父策略/保真资源流水线通过，811859预检，5bef8d冻结与绑定通过。两轮Probe SHA、40标签、结果、中文提示及诊断相同；16源程序集分别从bound/replay物理路径加载且与映射一致。

原SDK日志时间记录可能启动其后台日志设施；本轮没有证明全部后台线程优雅关闭。原生产DispenseTask始终null、未创建压力Task，两个宿主实际退出0；这些是不同范围的观测。

本轮没有真实设备运动/相机/气压/IO/用户提示执行/SQL、成功插补、完整生产Task/Retry/安全收尾或完整MSBuild/部署验收。尚未覆盖所有轴分支、视觉结果转换与自动聚焦、压力Task时序及设备成功链。全工程16项目/29组/1436文件/13项整体目标未完成。旧主/保真/原生/点胶阅读器均保持冻结，最新派生仍52专题5257快照，此份新报告尚未接入。

见[测试](native-dispense-controller-test.json)、[审计](native-dispense-controller-audit.json)、[进度](native-dispense-controller-progress.json)，原始结果/日志/IL位于.archify-work/native-dispense-controller/。
