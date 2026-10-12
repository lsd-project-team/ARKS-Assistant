# 预热设置、真实保存与产品全局异常处理

日期：2026-09-29。61项检查和10个独立Framework异常进程场景通过。纳入55份原成员片段、完整原BondSubSectionProgram类、实际项目Singleton/JSON程序集；不等于55个成员全部分支覆盖。前置见[后台监控报告](background-monitor-review.md)。

## 预热输入到保存和后台判断

执行四个原加热窗口事件、原InitTemperatureInfo、TransportProgram原静态构造与重置，以及原后台温度判断。BondSubSectionProgram原类完整编译，默认PreheatTime为5；其基类和硬件设置仓库是替身。TransportProgram为只保留Bond配置字段的派生容器，继承实际项目Singleton，使用原文件路径初始化片段，路径指向测试临时目录。并非完整生产TransportProgram对象图或实际配方文件。

控制器的配置getter遵循原定义，实时从TransportProgram.GetInstance().BondSubSectionProgram读取；该原定义也单独绑定源码。原设置按钮执行(int)Value、修改内存、调用真实Save，然后显示成功。

| 直接赋给控件替身的值 | 实际保存/重读 | 已过65分钟时原倒计时 | 原后台预热完成 |
|---|---:|---|---|
| -3 | -3 | -8分钟 | true |
| 0 | 0 | -5分钟 | true |
| 5 | 5 | 0分钟 | true |
| 59 | 59 | 54分钟 | false |
| 60 | 60 | 55分钟 | false |
| 90 | 90 | 85分钟 | false |
| 1.9 | 1 | -4分钟 | true |
| -1.9 | -1 | -6分钟 | true |

每行清空Singleton缓存后用实际项目DLL重读磁盘，再进入原计时/后台代码；小数按原decimal到int转换截断。计时留5秒余量。结果补实上轮60、90等参数的事件提交和持久化可达性，不声称真实DevExpress控件允许用户输入所有这些值。主类和Designer没有针对SpPreheatTime显式设置MinValue/MaxValue；第三方默认值与原生交互尚未验证。

## 保存失败与标志保留

- 超过int上限的decimal在赋值前抛OverflowException，内存与文件不变，也不显示成功。
- 实际文件以FileShare.None锁定时，Save失败；内存已改成60，磁盘仍是原值7，未回滚。测试异常为项目帮助器包装后的Exception。
- 成功提示替身抛异常时，文件已经保存为60。
- 原预热设置按钮不调用InitTemperatureInfo：原有HeatingComplete、PreheatingComplete及起始时间均保留，改变阈值不会自行重启预热。

## 窗口加载、显示与开关

原加载事件先设置开关状态和预热值，再订阅Toggled；第一次初始化不会由本测试控件触发开加热命令。原计时器显示未加热、预热完成或Minutes分量倒计时，没有把负数夹到0。

显式事件替身只在IsOn变化时触发Toggled：关闭调用CLoseHeater而不清完成标志；打开先执行原InitTemperatureInfo再调用OpenHeater，打开失败时标志已清。两次直接Load会添加两份订阅；定时器同步设备开关也可触发该替身事件，从而清标志。以上是明确事件语义下的顺序证据，不认定DevExpress一定如此派发，也不认定窗口正常生命周期必然重复Load。

## 产品原全局异常方法

Program注册了Application.ThreadException与AppDomain.UnhandledException并设置CatchException。两个原处理器都只拼接异常消息/堆栈后调用AKRSXtraMessageBox.Show，没有Stop、Abort或任务等待。

直接调用原处理器时，UI异常与后台IsTerminating真假两种事件均产生一条提示；受控机器仍Working，Task仍Running。提示自身失败继续向外抛；App处理器直接把ExceptionObject转换为Exception，构造的非Exception对象触发InvalidCastException。直接调用不等于真实WinForms消息泵行为。

进一步把原AppThreadException订阅到独立Framework宿主的真实UnhandledException事件，再执行原后台Thread的9个故障点。全部先记录原后台异常，再执行原产品处理器的提示调用，提示替身返回后进程仍非零退出，后续后台服务未运行。第10个场景让该提示自身失败，同样记录异常并退出。原方法未添加恢复逻辑。

这补上上轮未接产品处理器的缺口，但仍不是完整产品EXE：产品Main初始化、实际UI弹窗、其他运行时配置或宿主策略未执行。不能保证现场弹窗阻塞时间、退出方式或设备停止行为。测试不驱动物理设备。

## 检查与来源

- 模型默认/初始加载：2项；8个输入×5项保存/重读/标志/显示/后台判断：40项。
- 溢出、真实锁文件及提示失败：3项；显示与受控开关事件：7项。
- 产品原处理器及错误边界：9项。合计61项，12条结构化观测。
- 另有10个独立进程场景，保留退出码和事件序列。

运行`node scripts/test-heating-host.cjs`；审计`node scripts/build-heating-host-audit.cjs --check`。回执绑定完整原配置类、55份片段、真实程序集、派生容器、控件替身及独立宿主的来源哈希；Designer绑定与Program异常注册另外记录。

生产源码和现场配置未修改。29组保持部分复核；原生控件、完整配置对象图、生产并发及设备验收仍待完成。下一步继续真实安全门输入和任务对Pause状态的响应，不把状态赋值当作机械停止。
