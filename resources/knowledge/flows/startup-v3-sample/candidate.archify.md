# 启动、回零与生产放行 {#zx2200-startup}

程序打开、回零完成和生产放行，分别由不同入口控制。生产启动检查返回 true 后，`Start` 才设置 `Working` 并调用各任务入口。

- 开机回零返回 false 后，`Main` 仍创建主窗体；`Load` 单独检查回零标记。[](source:boot-home)[](source:form-load-gate)
- 启动检查前会清理文件、复位信号；后续还可能请求安全位置。[](source:prepare-reset)[](source:prepare-motion)
- `Working` 先于任务调用设置，不能据此确认所有任务已启动成功。[](source:working-state)[](source:start-options)

@answer scope="ZX2200 当前源码 · 外层控制流 · 非设备验收"
@meta locale=zh-CN quality_profile=showcase repo_url=https://github.com/lsd-project-team/ARKS-Assistant.git repo_revision=07ad3c75e9ce100f274807f88e23bf11f2e4367d

@source boot-home title="Main · Program.cs L250–256" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=14:20
@source form-load-gate title="MainForm_Load · MainForm.cs L232–271" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=30:69
@source home-confirm title="AllAxisGoHome · Machine.Operate.cs L504–525" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=79:100
@source home-prepare title="AllAxisGoHome · Machine.Operate.cs L527–553" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=110:136
@source home-result title="AllAxisGoHome · Machine.Operate.cs L555–583" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=146:174
@source ui-start title="BarItemStart_ItemClick · UcMainSystem.Production.cs L68–110" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=184:226
@source prepare-reset title="PrepareMachineReadyToStart · Machine.Operate.cs L185–196" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=236:247
@source prepare-gates title="PrepareMachineReadyToStart · Machine.Operate.cs L198–232" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=257:291
@source prepare-motion title="PrepareMachineReadyToStart · Machine.Operate.cs L234–255" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=301:322
@source environment title="CheckOperatingEnvironment · Machine.Operate.cs L89–128" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=332:371
@source working-state title="Start · Machine.Operate.cs L261–290" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=381:410
@source start-options title="Start · Machine.Operate.cs L291–308" path=resources/knowledge/flows/startup-v3-sample/source-snapshot.md lines=420:437

## 打开程序后，什么时候加载主界面？ {#boot-panel}

@diagram workflow id=boot-flow source=boot.workflow.json title="开机回零与主窗体门控"

@steps id=boot-steps
| boot-option-step | 要求开机回零? | `Main` 读取 `IsAxisResetBeforeWork`。关闭配置时跳过回零调用。 | boot-flow | boot-option |
| boot-home-step | 调用开机回零 | `Main` 不判断返回值。回零返回 true 或 false，都会继续创建主窗体。 | boot-flow | boot-home |
| boot-gate-step | 非离线且未回零? | 非离线且 `AllAxisReset` 为 false 时，禁用主区域并返回。离线加载可越过此门控。 | boot-flow | boot-gate |
| boot-load-step | 加载并启动后台 | 门控通过且后续无异常时，加载数据、初始化界面、连接仪表、选灯并启动后台。 | boot-flow | boot-load |

@callout level=note title="主窗体加载与生产启动分开判断"
| 离线越过 Load 门控后，生产启动仍会检查 `AllAxisReset`。[](source:form-load-gate)[](source:prepare-gates) |

## 回零方法何时返回成功？ {#home-panel}

@diagram workflow id=home-flow source=home.workflow.json title="AllAxisGoHome 的正常返回路径"

@steps id=home-steps
| home-confirm-step | 确认回零? | 按翻转配置提示干涉检查或人员离开。只有 OK 继续；取消返回 false。 | home-flow | home-confirm |
| home-prepare-step | 准备回零 | 按配置收回气缸、关闭补偿、复位顶针系统气缸，并调用胶盘回零入口。 | home-flow | home-prepare |
| home-check-step | 轴回零成功? | 调用 `HardwareRepositoryService.OneKeyHome`；返回 false 时提示失败并结束。 | home-flow | home-check |
| home-success-step | 设置回零标记 | 轴回零返回 true 且后续无异常时，开启补偿，设置 `AllAxisReset = true`，再返回 true。 | home-flow | home-success |

@callout level=warning title="异常会结束本次回零"
| 方法内异常由 catch 提示并转为 false；此前气缸和补偿调用没有统一回滚。[](source:home-prepare)[](source:home-result) |

## 点击生产启动后，怎样进入 Working？ {#production-panel}

@diagram workflow id=production-flow source=production.workflow.json title="确认、准备检查与任务放行"

@steps id=production-steps
| production-confirm-step | 配方允许继续? | 启用配方提示时，Cancel 直接返回。继续后关闭手动面板、退出单步，再调用 `Machine.Start`。 | production-flow | production-confirm |
| production-reset-step | 清理文件与复位 | `Prepare` 先调用 `CleanFile` 和 `ResetMachineSignal`，再进入拒绝启动的各项检查。 | production-flow | production-reset |
| production-gates-step | 门控检查通过? | 依次检查回零、任务、初始化、安全门及 Working 状态。任一拒绝条件成立就返回 false。 | production-flow | production-gates |
| production-safe-step | 请求安全位置 | 按配置请求 S1 安全位，调用 S2 安全位及未屏蔽时的顶针 Z 移动。此处没有判断这些调用的返回值。 | production-flow | production-safe |
| production-environment-step | 六项检查通过? | 按供晶、S2、S1、载具、焊点、制程顺序检查。任一 false 会跳过后续检查并使 Start 返回。 | production-flow | production-environment |
| production-working-step | 设置 Working | 只有 Prepare 返回 true 才执行状态赋值。之后才按配置与工作模式调用任务入口。 | production-flow | production-working |
| production-dispatch-step | 调用任务入口 | 调用顺序见下表。Start 没有统一等待所有任务完成，也没有汇总各入口的成功结果。 | production-flow | production-dispatch |

@callout level=warning title="检查失败前可能已经发生动作"
| 后续 false 返回不会统一撤销清理、信号复位和安全位置请求。按钮处理捕获异常时调用 Stop，并在 finally 恢复控件。[](source:prepare-reset)[](source:prepare-motion)[](source:ui-start) |

## 放行后，各任务按什么条件调用？ {#dispatch-panel}

| 调用顺序 | 入口 | 调用条件 |
| --- | --- | --- |
| 1 | 输送、供晶 | 非补偿工作模式。[](source:working-state) |
| 2 | S1 点胶任务 | 配置 S1，且为非补偿工作模式。[](source:working-state) |
| 3 | S2 动作初始化、固晶任务 | Prepare 返回 true 并执行到此处。[](source:working-state) |
| 4 | 胶盘、翻转任务 | 各自模块已配置，且为非补偿工作模式。[](source:start-options) |
| 5 | 两类华夫盒真空检查 | 执行到 Start 末段，依次调用两个检查入口。[](source:start-options) |

@callout level=note title="怎样理解这里的放行"
| `Working` 是软件状态赋值；任务入口发起相应任务。各任务的完成结果与先后顺序，需要分别确认。[](source:working-state)[](source:start-options) |

各节点可以查看源码卡片；步骤列表会高亮对应节点。来源使用已逐字核对当前源码的固定版本快照。
