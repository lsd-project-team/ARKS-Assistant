# 原顶针就绪检查与预顶移动集成验证

2026-09-29。110项受控断言通过；23个原方法、2个原属性、3个原信号构造绑定。来源记录见 wafer-eject-ready-test.json，审计见 wafer-eject-ready-audit.json。

## 本轮接入
在既有供晶消费者、四种搜晶、取料补偿、台面移动、单步及原Stop链上，新增原CheckEjectionAxisZAtReadyLiftPosition、MoveEjectToReadyLiftPosition、两个MoveEjectionAxisZToG0Pos重载、GetCurrentCarrier及EjectionAxisZG0Pos属性。阈值字段直接从原EjectController源码抽取，严格校验原声明range = 0.1，未改生产代码。

## 已验证行为
- 屏蔽顶针直接返回，甚至不读取槽位和位置。检查使用当前位置 >= 预顶位置 + 0.1；实际移动使用绝对差 > 0.1。在预顶0、当前位置0.1的可复现样本上会提示，但OK后不移动。
- OK进入预顶移动；Abort抛出异常；非预期Retry返回值直接落出检查。真实弹窗是否可能返回该值仍待原生UI验证。
- 空槽位和空字符串名称失败，null名称没有被同一判断拒绝。正常预顶要求晶圆载具；更换顶针分支不依赖载具，使用硬件速度。
- 配方速度分支设置Vel=速度、Acc/Dec=速度*10；硬件分支使用轴参数。负数和零速度在原包装层未被拒绝，仅证明传给替身驱动，未对设备执行。
- bool重载可关闭台面碰撞检查。离线下bool重载立即返回；double重载返回前仍读取机械位置并写日志，因此并非完全不触达依赖。
- 连续模式下Pause/Stop不独立阻断Z接口；预存单步事件在这两种状态下也可放行。无事件时真实单步等待不发轴命令，原Stop可取消等待并产生异常。
- 轴非Success返回和位置、日志、坐标、换针台/台面检查异常均按调用顺序传播；移动完成后的第二次日志异常可能发生于轴成功之后。
- Single、Mapping、Nine消费者通过就绪检查后完成两次XY调用并发出取料许可；Box路径不调用此顶针检查。前三种模式轴失败时调用原Stop，不发XY或许可。
- 在就绪弹窗或Z接口内注入原Stop，仍可在Stop状态调用XY。Single/Mapping随后停止搜晶且不发许可；Nine在该受控路径仍发许可。
- 当替身驱动返回Success但不更新位置时，本次检查不再次验证到位；后续检查再次尝试Z，三个消费者路径仍可发许可。此测试不证明真实驱动Success的物理含义。

## 覆盖与限制
110项分别覆盖阈值、弹窗、配置、速度、两重载、离线、状态/单步、依赖异常、四模式完整消费者、Z失败、Stop注入和无位置变化。原Signal与原方法从源码编译到.NET 10.0.11临时程序集；不是原产品完整Framework构建。

轴SDK、坐标标定、CheckEjectionBankAxisTAtWorkPosition、CheckWaferTableInCollisionCircle、视觉、日志、I/O、存储及UI均为明确替身。MoveEjectToSafePosition仍为替身。尚未接入真实轴到位契约、原视觉/九宫格计算、完整正常启动及生产并发；没有原生界面或实机安全验收。29个模块分组维持partial。

## 复现
运行 node scripts/test-wafer-eject-ready.cjs；随后 node scripts/build-wafer-eject-ready-audit.cjs --check。统一回归和阅读器验证以独立集成回执为准。
