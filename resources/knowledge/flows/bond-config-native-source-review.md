# 原产品与完整焊点配置原生数据验证

两份实际 Infrastructure/JSON SDK 在独立 Windows .NET Framework 进程中各执行 56 项断言，共 112 次执行。原生产品准备的 36 项断言按原名称顺序保留，随后执行 20 项完整焊点配置检查；不是 112 种行为，也不加入当前 1328 项完整启动组合。

23 个完整原文件保持不变，原 SingleBondPositionConfig 替换前次原生产品探针的焊点类适配器；包括源构造函数、所有属性/初始化、JsonIgnore、ResetAssistantStates、五状态列表与自身汇总。沿用 22 文件原产品/配置/仓库/状态/AOP/坐标源码、八个原检测示教成员与属性、实际 SDK Singleton/JSON/AKRSPoint3D。明确 Framework 引用下编译 26 个源输入和 8 个程序集引用；Fody 没有运行，未使用事件警告仍保留。新增 MeasureHeight 命名空间标记仅解决源文件未使用的 using，不是测高 SDK 执行证据。

新增实际运行结果：

- 原焊点构造函数创建三项 UnAble 和两项 Forbidden；点位、灯光字典、曝光 500/增益 1/伽马 40、UI 教学索引 1 和实际模型命名空间的 EditState.NewCreate 初始化。原继承层为 SingleConfig/BaseConfig；显式教好三项后，自身汇总与 BondPositionConfig 汇总通过。
- 原 ProductConfiguration 的 TU 就绪检查可以通过，同时原焊点汇总拒绝未教焊点。启用两系统测高标志不改变既有 Forbidden；ResetAssistantStates 替换全部助手对象，仍将测高置 Forbidden，三个必需步骤恢复 UnAble。
- 实际产品 Save 保留源 JsonIgnore：自身就绪 getter 和 UI 教学索引不持久化，加载后索引回到构造默认 1。缺少/无效的必需状态枚举保留 UnAble 并拒绝；可选测高的无效枚举保留 Forbidden 并通过；未知数字 99 通过；显式 null 助手状态经焊点的 null 判断返回 false。
- 无效 VisionExposure 数字字符串在焊点记录前部时，整个配置记录丢失，空焊点列表汇总通过；在记录末尾时，已读取的合格示教状态保留，通过汇总。该检查只描述所断言的焊点汇总结果，不能单凭它宣称整个原 UI 启动通过。
- 不兼容 Name 对象在此产品对象加载中使实际 ReadGenericObject 返回 null；实际 Singleton 随后恢复原默认产品，焊点列表为空且自身汇总为 true，但 TUPosition 未教，产品 TU 就绪检查为 false。这与此前独立仓库 ReadGenericList 的“记录丢失”范围不同，已通过直接调用实际 object helper 核对返回值。
- null 焊点列表、合法已教焊点之后的 null 列表成员，分别使原 foreach 或成员访问抛 NullReferenceException。重复名称的 GetConfigByType 取首项，而焊点汇总遍历整个列表，可被后续未教重复项拒绝。

初版探针对数值错误和 Name 错误后对象范围的猜测被原生运行纠正；最终两份 SDK 的 56 项检查均以实际退出码 0 通过。见 [测试清单](bond-config-native-source-test.json)、[来源审计](bond-config-native-source-audit.json) 和 [准备进度](bond-config-native-source-progress.json)。

仍待完成：完整启动/实体组合接实际 SDK Singleton/JSON；剩余检测配置字段、Fody/AOP、真实 Path/Recipe/PR/参数日志/UI 提示、TuService 蛇形映射与物料实体依赖。原项目构建、部署配置/DLL、原生 UI 与设备未验收；16 工程、29 源码组、1436 个 C# 文件与 13 项要求仍未完成。全部工作文件和 JSON 测试文件均在受校验的临时工作目录中，未改生产源码或部署配置。
