# 配置加载、保存与外部依赖：失败边界

2026-09-28。依据 trunk 源码和[随仓库 DLL 的静态 IL 快照](persistence-save-contract-review.md)；不加载或执行设备程序集。文件摘要见[persistence-dependency-boundary.md](persistence-dependency-boundary.md)。现场实际加载版本及运行行为未验。

## 三条配置路径不能混为一条

|配置入口|源码与随附 DLL 中已确定的处理|仍未确定的行为|
|---|---|---|
|MachineConfigContext.GetInstance|instance 为空时先 IsExistFile；存在才在 try 内 ReadGenericObject；不存在才 new 默认对象。随附 DLL 的 ReadGenericObject 对捕获范围内的读取/反序列化异常弹窗并返回默认值，而不是向外抛出|实际加载 DLL 和现场文件/权限；IsExistFile 在该调用方 try 外，读取 helper 的 File.Exists 也在其 catch 外|
|BaseSettingRepository.Load|随附 DLL 的 ReadGenericList 会先准备目录/缺失文件，读取捕获范围内异常弹窗并返回 null；调用方把 null 转为空 List，且没有本地 catch|目录/文件预创建的异常在 helper 读取 catch 外；现场版本、权限和真实数据行为|
|TransportProgram|继承 Singleton；静态构造设置 FilePath；初始化重设路径并清 instance。随附 DLL 的 GetInstance 锁内调用 Load、若仍为空则创建 T；Load 构造并读 JSON，Save 的顺序见 IL 报告|实际加载版本、路径求值、磁盘保证及失败后的设备状态|

## MachineConfigContext 的故障分支

1. 文件不存在：new MachineConfigContext，RecipeID保持Guid.Empty；该分支没有自动保存调用，不能宣称已创建JSON文件。
2. 文件存在且helper返回对象：缓存对象供后续使用。
3. 文件存在且helper返回null：没有空值补建，方法返回null；下一次调用仍可能重新进入加载流程。
4. 随附 DLL 的 ReadGenericObject 捕获范围内发生读取/反序列化异常：helper 弹窗后返回 null，不会触发调用方的 catch；instance 仍为空时返回 null。helper 捕获范围以外的异常若进入调用方 try，则调用方 catch 只弹窗，没有补建或重抛。不能称为可靠恢复或生产启动成功。
5. IsExistFile在try外；它的异常不会被这个读取catch捕获。
6. 类中虽声明locker，但GetInstance没有使用lock。这里只能证明该方法没有使用该锁，不能断言现场已经出现重复加载。

## 对后续工作步骤的影响

- PathConfig.RecipeDirPath直接读取GetInstance().RecipeID；该表达式没有空条件运算。如果GetInstance返回null并且走到此表达式，会发生空对象解引用；外围是否捕获要按具体调用链判断。
- 主界面编程入口读取MachineConfigContext.GetInstance().RecipeName，不是只靠ProductConfiguration非空就保证配置上下文存在。不能据此断言所有UI入口都无外层异常处理。
- TransportProgram.InitTransportSystemProgram先取得当前配方文件路径，再令instance=null；路径求值失败时不能把后续缓存清除画成必达步骤。
- SaveMachineConfig 只把当前对象交给 SaveGenericObject，没有局部重试或跨文件事务；仓库 Save 交给 SaveGenericList。随附 DLL 的单文件写入顺序可查[IL 审查](persistence-save-contract-review.md)，但跨库文件和配方名称引用的原子性尚未证明。

## 外部依赖证据边界

- 项目声明引用libs/AKRS.Galaxy2.Infrastructure.dll且SpecificVersion=False，MachineSupport项目也声明该本地路径。声明引用和文件存在不是运行时加载证明。
- 当前 1436 个 C# 文件的声明词法搜索没有找到 Singleton、JsonFormatHelper、BackgroundThreadService 定义；该搜索有明确范围和语法限制，不冒充完整符号解析。随附 DLL 中前两者的选定方法已有[静态 IL 证据](persistence-save-binary-evidence.json)，后台服务的选定方法另见[调度契约](background-task-contract-review.md)；这些都不等于现场实际加载版本已核对。
- DLL、PDB和随附DLL.config均固定文件摘要。PDB存在不等于源码已经导入；DLL.config的bindingRedirect也不能当作主程序实际生效配置。
- 不把 namespace 或 DLL 文件名当成现场类型所有权的最终证明；已登记随仓库 DLL 静态方法体，仍须匹配构建和现场实际加载版本。

## 工程师接手验证清单

|输入/场景|先确认的接口行为|后续观察|
|---|---|---|
|MachineConfig不存在|文件检查false，默认对象建立|Guid.Empty如何影响配方选择；是否由其他路径保存|
|MachineConfig损坏、JSON null、权限拒绝|对照随附 DLL 的 ReadGenericObject 捕获范围，核对现场版本|当前上下文是否 null；哪一层提示/停止/恢复|
|料仓库缺失、损坏、重复名称|对照随附 DLL 的 ReadGenericList 预创建和 null 兜底，核对现场版本|空列表、预创建异常、旧缓存和名称解析的差异|
|并发保存或进程中断|对照随附 DLL 的 SaveGenericObject/List 写入次序，核对现场版本|部分写入、备份和重启恢复|
|配方切换时路径无效|FilePath求值与instance清空顺序|旧对象是否继续保留、哪个调用方捕获|

以上均未运行验证，不接触设备配置或生产进程。下一步需要在隔离目录、匹配 DLL 下设计故障测试，不能用自建替身冒充原库。

## 源码溯源

- [MachineConfigContext.GetInstance / SaveMachineConfig](../../trunk/AKRS.Galaxy2.MachineSupport/Config/MachineConfigContext.cs#L55)
- [PathConfig.RecipeDirPath](../../trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs#L88)
- [BaseSettingRepository.Load / Save](../../trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs#L82)
- [TransportProgram 静态构造与重载](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs#L63)
- [编辑入口的配置读取](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L368)
- [Infrastructure声明引用](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L265)
