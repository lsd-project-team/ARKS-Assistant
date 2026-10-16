# 原Bond坐标与重复定位验证

原Bond坐标读取/转换和重复定位循环接入后，49个原方法与3属性的99项受控断言通过。XY读取命令位置、Z读取编码器位置，依次读取非原子快照；精度比较包含等号，Retry重置次数，失败后OK访问null结果并由消费者捕获停止。校正期间Stop仍可继续XY；实际轴、标定SDK和硬件仍为替身，非设备验收。

## 来源与范围
99项断言、52段原方法/属性、32份来源哈希、3个原信号绑定。.NET 10.0.11受控编译执行，未修改生产源码。
新增原BondModuleController.GetG0RealPosition，BondModule.GetG0RealPosition/Get3DRealPosition/ConvertMachineToG0Pos，以及Block.ToRequiredAccuracy和MoveToCameraCenterWithThread(MatchResult[])全文。
轴命令/编码器读数、坐标SDK、相机标定与算法、原始晶圆台位置属性、UI和硬件仍为替身。离线返回new AKRSPoint3D()仅验证本测试点类型默认值，不据此证明外部坐标库默认值。

## 结果
- Bond三维原包装依次读取X命令、Y命令、Z实际编码器位置；G0再调用原转换包装。模拟读数在调用间变化时可得到混合时刻值，非原子快照。
- 离线工作模式绕过轴读取；转换null先于离线判断，SDK返回null不被修复。每个读取/变换失败均中止后续调用。
- 重复定位角度和XY绝对偏差与目标比较使用<=，含正负边界；非有限值和负角度目标测试保持原行为。
- 最大次数<=1时仍执行第一次采集，无校正；最多N次采集和N-1次校正。失败报警Retry回到初始化并重置计数，故外层重试不受该轮最大次数的总上限限制。
- 完整原采集失败返回null数组；重复定位失败对话框OK仍读matchResults[0]，产生NullReferenceException。Single/Mapping/Box完整消费者捕获、提示并Stop，不发取料许可。
- Ignore返回失败和中心，Abort抛异常；脚本Cancel没有switch分支，继续循环至次数限制，不表示真实UI提供Cancel。
- 相机中心校正先检查离线/空跑/不定位，再访问结果；正常路径取首匹配点和晶圆台原始位置，调用SelfPosToG0后执行原移动链。
- 连续模式Pause/Stop中校正本身没有统一阻塞；Stop发生在校正变换中仍可派发XY并继续下一次放行的匹配。单步等待和实际硬件停止不由本结论替代。
- 四模式正常消费者通过；轴读取包装中Stop且相机判断放行时，Single/Mapping/Box后续拦截，Nine仍可发许可；读数异常均在算法前被消费者捕获停止。

## 剩余任务
真实轴/标定SDK、晶圆台位置属性、墨点与图像处理、原生UI、完整启动并发、配置/DLL、原工程构建和设备验收仍未完成。29组保持部分复核。
