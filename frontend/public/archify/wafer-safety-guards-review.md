# 原换针台、碰撞检查与安全位移动集成验证

2026-09-29。135项受控断言通过，26个原方法、3个原属性、3个原信号构造绑定。详见wafer-safety-guards-test.json及wafer-safety-guards-audit.json。

## 接入范围
在原供晶消费者、四种搜晶、取料动作、单步、Stop和顶针就绪链上，接入完整CheckEjectionBankAxisTAtWorkPosition、CheckWaferTableInCollisionCircle、MoveEjectToSafePosition及EjectionBankAxisTG0Pos。原range字段沿前一组合器从源码抽取，生产源文件不改。

## 验证结果
- 换针台检查在屏蔽时不读取配置。非屏蔽时逐槽检查绝对距离严格小于0.1；恰好0.1继续后续槽。未匹配与空槽数组均正常返回，因为原末尾throw已注释；null程序、配置、数组、槽或位置仍产生空引用异常。
- 换针台位置属性离线返回零且不读取轴SDK。在线位置与坐标转换仍使用明确替身。
- 台面碰撞圆将半径转long后平方，2.9按2处理；边界接受，负半径平方同样为正。已验证偏移圆心和零半径；不推断NaN或极大值。
- 超界提示OK继续、Abort抛异常，非预期Retry亦落出检查。Pause/Stop不绕过提示，也无独立状态拒绝。原生UI是否能产生Retry仍未验收。
- 安全位移动仅在绝对Z差大于0.1时调用Z的bool重载，明确关闭台面碰撞检查，再依IsNeedEjectZero调用GoHome。已在安全位置或恰好阈值时，即使要求回零也不调用GoHome。
- 屏蔽顶针只绕过换针台检查，不阻止安全位移动和回零。离线且安全目标Z=1时，位置属性给零，Z重载提前返回后仍可调用GoHome；目标Z=0则差值不触发。这里只证明原控制流调用替身接口，不证明实际回零运动。
- 位置、换针台读数、坐标、轴移动和回零异常按顺序传播。轴非Success阻止回零。单步无事件时安全移动等待，原Stop取消等待且不回零。
- 原StopSearch仅在Stop状态执行吹气开/关、安全位及可选回零，然后抛“已停止”。其清理失败会先抛依赖异常，正常结束后的停止提示不再执行。离线StopSearch也可到达GoHome。
- 四模式完整消费者成功路径通过。Single/Mapping/Nine的超界测试先选择预顶OK，再分别选择碰撞OK或Abort，断言确实到达两次提示；碰撞Abort阻止Z与许可。
- 空换针槽数组不能阻止三个晶圆消费者发许可；null槽数组导致原Stop且不发Z或许可。Z接口内注入原Stop，Single/Mapping随后执行第二次Z安全移动并回零且不发许可；Nine路径只有一次Z且仍发许可。

## 验证边界
原方法在.NET 10.0.11临时程序集内执行，真实Signal负责等待；不是产品完整Framework构建。轴SDK、GoHome、到位判定、坐标标定、视觉、UI、日志、I/O和持久化仍为替身；目标点IsInCollisionCircle也仍为替身，本轮新增的是当前位置CheckWaferTableInCollisionCircle原方法。真实设备安全、完整启动/并发与实际加载DLL未验收。29组继续partial。

## 复现与后续
运行node scripts/test-wafer-safety-guards.cjs及node scripts/build-wafer-safety-guards-audit.cjs --check。全套回归、阅读器与哈希以独立integration-verification回执为准。下一步接入原视觉AnalyseDie、九宫格CalculateDiesPosition及目标点环限位判断，并定位真实轴命令/到位实现和运行期依赖。
