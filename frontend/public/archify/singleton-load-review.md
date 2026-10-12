# 真实Singleton配置加载、缓存与保存复核

27项检查通过。本次使用项目libs中的AKRS.Galaxy2.Infrastructure.dll、AKRS.Base.dll、Newtonsoft.Json.dll，在本机.NET Framework及独立临时目录实际执行Singleton<T>.GetInstance/Load/Save和其调用的JSON文件帮助器。未修改生产源码或实际配方文件。

## 真实与替身范围

完整SystemProcess原源码、ProcessDomain.InitProcessProgram原方法、两份原枚举参与编译。轻量ProcessDomain派生包装器保留S1SystemProcess/S2SystemProcess结构并继承真实Singleton；步骤载荷类型和ZX2200PathConfig路径提供器是夹具，不是完整ProcessDomain生产类。原类的业务校验、静态路径初始化和整套配方域未运行。

通过Roslyn面向本机.NET Framework编译，Windows PowerShell执行；三个DLL加载路径逐个验证，并记录文件哈希。收据另记录真实GetInstance/Load/Save方法IL长度与哈希。所有测试文件位于受控临时目录，结束后清理。

## 加载与对象身份

- 原InitProcessProgram更新FilePath并将真实静态instance设null；不会创建目标目录或立即读取文件。
- GetInstance读取缺失文件后返回新默认对象，不创建文件；随后返回相同缓存对象。
- 已缓存时修改磁盘文件，GetInstance不会自动重读；执行原重置方法后再GetInstance才读取新内容。
- 显式Load会重新读取并替换已有缓存。Load缺失文件本身可留下null缓存，而GetInstance还带创建默认对象的后备分支。
- 只修改FilePath不清缓存时，仍返回旧缓存；随后Save会把该缓存写到新路径。正确切换必须结合调用方的重置与重载时序理解。

## 非正批次的真实文件证据

使用真实Singleton加载临时ProcessProgram.json：开启按次数执行、TransportFirst模式、WorkCycleNumber=0能完整进入配置对象。将其改为-3，经真实Save、重置、GetInstance后仍为-3且开关开启。

真实帮助器还接受Int32.MinValue、未知枚举99、ProcessSteps=null及S2SystemProcess=null；空JSON对象保留构造默认值，根JSON null经GetInstance回退为新默认对象。

这一步比[上一轮默认JSON验证](cycle-config-review.md)更进一步：真实Singleton与实际JSON设置未拒绝这些有效JSON值。仍未执行完整生产ProcessDomain、全部启动门控、实际用户配方及随后任务调度；不能据此宣称设备故障已经复现。

## 保存的接收对象与静态缓存

- Save使用静态instance而非调用该方法的接收对象。旧对象被改为99后调用Save，落盘的仍是当前缓存的-3。
- 重置instance=null后，不先GetInstance而直接调用旧对象.Save，真实文件内容变为null。后续GetInstance返回默认配置。此为明确构造的调用顺序，不代表正常界面一定这样调用。
- Save可创建缺失的父目录和文件，临时新路径的保存与重载通过。

## 文件失败与清理

- 以FileShare.None锁住已有目标文件时，Save抛异常；已改为6的内存值保留，原文件仍为5。失败替换产生的随机临时同级文件在本样本被删除。
- 释放锁后再次Save成功，重读得到6。
- 路径指向目录时，加载按缺失文件回退；保存失败。
- 本轮不测试损坏JSON及读取锁定异常：只读IL检查显示读取帮助器异常路径可能调用WinForms消息框，不能将未执行的交互路径当作无界面异常测试。

## 二进制观察与限制

只读IL显示GetInstance和Save使用同一locker进入/退出Monitor；公开Load未显示相同外层锁。Load先创建对象，再调用ReadGenericObject，随后订阅嵌套属性变化。JSON帮助器设TypeNameHandling、TraceWriter和错误回调，因此上一轮直接JsonConvert默认设置不能代替此文件链验证。

锁存在不证明整个配方或跨域操作事务安全；未运行并发Load/Save、原生属性织入、完整事件订阅效果或全部错误回调。本轮也未运行非正批次下的无限循环。

## 验证与下一缺口

node scripts/test-singleton-load.cjs
node scripts/build-singleton-load-audit.cjs --check

已把“实际单例是否能读入非正批次”推进到真实DLL临时文件证据；仍需连接完整生产门控、S2排序及任务启动时序，并补原生UI、真实依赖构建、设备闭环。27是本专项断言数，不是整个持久化模块验收。29组保持部分复核。

后续已补[加载到启动排序的有界集成](startup-config-review.md)：真实DLL加载后运行原制程检查、完整原启动/环境检查、S2自检和排序，63项检查通过；8种非正批次样本在明确依赖替身条件下到达分批代理停止点，状态已设Working且已调用三个前置Start。危险循环未执行，生产任务内部、硬件和完整现场依赖仍未验收。
