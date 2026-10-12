# 四种搜晶模式与停止门控受控验证

日期：2026-09-29。状态：专项受控测试通过，整体仍为部分复核。

## 执行范围

`node scripts/test-wafer-search-gates.cjs`：172项断言通过。运行时.NET 10.0.11。组合完整原供晶Dowork、IsNeedChange、Block.NextDie、SearchSingle、SearchNine、AnalyseDies、SearchMapping、SearchDieBox、StopSearch，合计8个原方法和1个原属性；直接编译原Signal和机器枚举，并绑定原信号池的两处构造声明。每段原文的文件哈希、UTF-16偏移、行号和片段哈希见测试JSON。生产源码未修改。

## 已验证行为

| 条件 | 受控执行结果 |
|---|---|
| 请求被接收后变为Pause | 四种模式均继续所选正常搜索路径，并发出取料许可；StopSearch仅判断Stop |
| 请求被接收后变为Stop | 九宫格在AnalyseDies入口拦截，未调用计算或取料移动接口；Single、Mapping和非静态Box先调用搜索移动/视觉接口，再由StopSearch抛异常，均未发出许可 |
| StopSearch正常清理 | 按吹气开启、延时、吹气关闭、顶针回安全位的原顺序执行，然后抛异常；消费者捕获并调用Stop替身 |
| 三处停止清理接口分别抛异常 | 后续清理被截断，未到达取料移动或许可发送；异常进入消费者catch |
| 取料移动接口处才变为Stop | 四模式所选成功路径没有返回后的状态复查，消费者仍在Stop状态下发送许可 |
| 九宫格计算接口内变为Stop | 本次AnalyseDies没有第二次检查，仍调用取料移动接口并返回成功 |
| Single/Box无下一位置 | 标记换料、保存并返回false，发生在StopSearch之前 |
| Mapping耗尽或PickRefEnd | 标记换料、坏料、保存、解锁并返回false，未经过StopSearch |

其余覆盖：单点跳过重试与重试前停止；Single/Box双点成功、第一点与第二点跳过；不支持的定位模式；静态料盘绕过视觉；Mapping跳板、预取、找不到路径翻译及参考点递归分派；Nine已有上方芯片、行耗尽初始化和递归上限处理；未知搜索模式；StopSearch(false)。

## 不能由本测试证明的事项

- CalculateDiesPosition、AnalyseDie、GetNextPosition/晶圆图库、几何转换、行标记以及MoveDieToPickCenter和底层轴/气缸均为可观测夹具；原方法包含并编译不等于所有算法分支已覆盖。
- Machine.IsStop是读取受控状态的替身；Machine.Stop仍为记录调用和修改状态的替身。本测试未整合原Stop失败清理，也未证明真实停止能否阻断驱动。
- 状态变化由确定性回调注入，消费者运行在真实Thread且使用原Signal；这不等于真实生产线程竞争或并发调度验收。
- 视觉、UI、实际配置/DLL、持久化以及设备动作没有现场验收；受控回归不能替代完整产品构建和设备安全验证。

## 下一步

继续接入实际MoveDieToPickCenter、CalculateDiesPosition/AnalyseDie的动作门控以及原Machine.Stop；核对TransportDomain.StartTask模式分派、完整正常Start与真实并发。完整构建、加载配置/DLL和设备验证仍待完成，29组模块维持partial。

来源校验命令：`node scripts/build-wafer-search-gates-audit.cjs --check`。统一回归结果以单独集成验证回执为准。
