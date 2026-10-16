# 完整受控组合的原生 Framework 与实际 SDK 启动准备

1328 项完整受控组合已在 Windows PowerShell 的原生 CLR `4.0.30319.42000` 中通过，断言名称、顺序与已冻结的正式 1328 项结果完全一致。另建 SDK 接入分支，在仓库 `libs` 与 `bin/Debug` 两份 Infrastructure DLL 的独立进程中各通过 58 项检查，共 116 次执行。来源、编译产物、选定 DLL 路径及运行日志见[机器记录](transport-full-framework-sdk-test.json)、[来源审计](transport-full-framework-sdk-audit.json)和[准备进度](transport-full-framework-sdk-progress.json)。

这两种运行范围独立：原生 Framework 的 1328 项仍使用既有外部边界适配器；实际 SDK 分支编译完整组合，但只执行新增的 58 项启动检查。后者没有把原 1328 项全部迁移为实际 SDK 测试，也未加入[已完成的统一回归回执](transport-product-declarations-integration-verification.json)。阅读器仍为 40 专题、3817 段专题快照，29 组均为 partial。

## 原生 Framework 中执行完整组合

编译采用现有 Roslyn 和六个明确的 .NET Framework 实现程序集引用。输入包含完整组合探针、三个原坐标文件、原 Signal 和 MachineEnum 文件，共六个编译单元。兼容处理只替换探针中两处泛型 `Enum.GetValues<T>()` 调用，并为夹具字典增加 `TryGetValue` 实现的 `GetValueOrDefault` 扩展；原断言表达式保持，512 条提取记录、511 段唯一源码在编译输入中逐段核对，原源码正文未修改。

这证明现有原启动、实体、坐标、生产者、真实供晶 Task、五阶段输送及配置/检测受控组合可在原生 Framework 进程执行。隔离 DLL 编译没有完成原工程的 MSBuild、依赖还原或 Fody 织入。

## 实际 SDK 进入原启动方法

SDK 分支将重建的产品类接到实际 `Singleton<ProductConfiguration>`，GetInstance 调用 SDK，Save 调用其基类实现；保留旧夹具计数和异常钩子，并以反射桥接实际单例缓存字段，供原 Clear 方法和场景隔离使用。原仓库的 Load/Save 方法通过既有边界转发到实际 `JsonFormatHelper<T>.ReadGenericList/SaveGenericList`。对象与列表分别落盘，随后清缓存重载。两份 DLL 分别编译、在独立原生进程中运行，并核对实际加载程序集的绝对位置。

28 项产品启动检查覆盖两个原入口，每个入口验证缺失产品、已教普通产品、未教焊点和显式 null TU。检查实际产品单例发布、对象保存、重载及缓存；已教空焊点产品进入原五次回零、生产者和真实供晶启动，其他场景在任务创建前停止。

另 30 项仓库组合检查覆盖两个入口和缺失检测、已教检测、未教检测、null 检测状态。产品保存和重载保留异形单叶树及胶检/焊后两个开关；原类型仓库保存并重载实际 JSON 列表。已教检测使原单叶实体树启动，其他数据拒绝启动。两个检测开关共用原仓库缓存，每个启动场景只有一次实际 SDK 列表读取。

## 序列化与复现边界

SDK 分支移除历史同名 `JsonIgnoreAttribute` 替身，使用实际 Newtonsoft 属性；从原源码恢复六处已捕获属性上的 JsonIgnore。运行检查具体 JSON 属性路径及本次保存的计数增量。开发时发现，缺失文件的默认实例加载可先保存，广泛搜索同名 JSON 字段也会误中其他类；修正只涉及本轮夹具及断言。列表 JSON 使用类型元数据包装时，从 `$values` 检查记录。

坐标单元在命名空间内显式绑定既有全局点适配器；产品、配置和检测的类组成仍按受控组合重建。独立[23 个完整原文件/56 项数据准备](bond-config-native-source-review.md)的完整类与实际 SDK 点类型尚未整体迁移进本分支。配方路径、PR、AOP、VM、动作与设备依赖仍有适配器；第三方控件、实际窗口和设备没有在本轮运行。

复现命令：`node scripts/test-transport-full-framework-sdk.cjs`。来源检查：`node scripts/verify-transport-full-framework-sdk.cjs --check`。脚本分别编译和执行原生受控组合及两份 SDK 分支，比较完整断言数组，保留每次复现的产物与日志。所有临时配置只写入工作区内带独立前缀的目录，退出时检查绝对路径后清理。

下一步迁移完整原配置/焊点声明和序列化属性，继续扩大实际 SDK 分支对原断言的覆盖，核对类型身份、Fody/AOP/PR/VM/动作与实际外部依赖；随后完成原工程构建、部署配置/DLL、原生 UI 与设备验收。整体 16 工程、29 组、1436 个 C# 文件及 13 项要求仍未完成。
