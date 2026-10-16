# 原取料动作链、台面控制器与单步门控

日期：2026-09-29。状态：受控验证通过；生产运行、原Stop整合和设备验收未完成。

## 执行与来源

`node scripts/test-wafer-action-gates.cjs`：210项互不重复断言通过，运行时.NET 10.0.11。在前一搜晶组合基础上加入完整原MoveDieToPickCenter、GetPickOffset1、IsNeedChangeCarrier、SetCurrentPosition、MoveWaferTableToG0PosWithSearch和WaferSystemDomain.SingleStep，共14个原方法和1个原属性。直接编译原Signal及机器枚举，逐字绑定需料、许可、系统2单步三处原信号声明。来源文件、原方法偏移/行号和哈希见测试JSON。未修改生产源码。

## 已确认的控制流

| 情形 | 受控结果 |
|---|---|
| 四种搜晶进入原取料移动后，在标记中心接口处改为Pause或Stop | 单步关闭时仍调用原台面控制器的X/Y命令接口并发送许可；此处已越过前一StopSearch |
| 原台面控制器连续模式 | 先关闭真空；在线时检查限位/顶针条件、转换坐标、先发X再发Y、最后等待双轴；本方法没有独立的Pause/Stop检查 |
| 离线 | 仍先调用关闭真空，随后返回；不消耗预置单步信号，不调用轴接口 |
| 开启单步且状态Pause或Stop | 等待真实AutoReset事件；事件释放后仍到达轴命令接口。原WaitSingleStep不读取机器Pause/Stop状态 |
| 等待过程中关闭单步开关 | 原WaitSingleStep返回false；SingleStep抛异常，本次轴命令未发出 |
| 原位置记忆 | SetCurrentPosition忽略传入的位置值，存储控制器当前G0位置，再保存；双点案例已验证当前位置不同于目标中点 |
| 保存抛异常 | 位置已写入内存，不回滚；消费者不发送许可并进入异常处理 |
| 晶圆图还有参考点且已标记换料 | 原IsNeedChangeCarrier返回false；已在完整消费者中验证不会进入自动换料 |

## 分支与故障覆盖

- 四模式 × Working/Pause/Stop的完整消费者取料链；三状态 × 单步开关 × 离线开关的控制器矩阵。
- Box限位检查开关与顶针检查跳过；静态料盘取料不移动台面、不记忆位置。
- 关闭真空、限位、顶针就绪、坐标转换、X命令、Y命令、双轴等待各处抛异常的截断顺序；X已调用不保证Y已调用，更不保证物理到位。
- 四模式的轴接口故障经完整消费者捕获、提示并调用Stop替身，不发取料许可。
- 四模式 × 双点配置 × 离线的偏移数值；四模式 × 换料标记 × 空/非空/缺省参考点列表；未知模式异常。
- 双点取料中点、非WaferTablet类型转换失败及非Box位置保存失败。

## 验证边界

原消费者、搜索分派、取料移动、位置记忆、台面动作控制器、单步控制与Signal均实际执行。视觉分析、九宫格位置计算、标定转换、限位几何、顶针就绪、轴SendAbsoluteMoveCommand和MotionService.WaitAxesArrival均为可观察夹具；测试证明调用控制流，不证明真实驱动在Stop下执行运动或能够正确急停。

Machine.IsStop读取受控状态，Machine.Stop仍是记录调用/改变状态的替身；原Stop重置单步开关及清理故障尚未接入。UI、自动换料、持久化、真实配置和现场并发未验收。所有状态切换均按测试回调/线程同步确定性注入，不能替代生产并发验证。

下一步：接入原AnalyseDie、CalculateDiesPosition、Machine.Stop以及下层轴与就绪检查；继续完整启动和模式分派、完整构建及现场配置/DLL核验。29组模块维持partial。

来源校验：`node scripts/build-wafer-action-gates-audit.cjs --check`。完整回归以集成验证回执为准。
