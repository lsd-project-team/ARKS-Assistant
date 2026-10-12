# 配方删除与视觉仓库备份：源码复核

更新：2026-09-28。聚焦自动工作依赖的配方/PR资源生命周期。仅分析源码；未调用删除、复制、设备或数据库操作。已有复制/重载链路复用既有证据，本轮补齐删除与备份失败边界。

## 工作步骤摘要

1. 用户打开配方管理，UcMainSystem将CopyOldRecipePR和DeleteOldRecipePR作为回调传入FrmRecipeManage，再显示模态窗口。窗口关闭后刷新界面。FrmRecipeManage属于外部配方库，仓库内没有找到其C#定义；不能推断其删除确认、回调次序或配方目录删除事务。见 [管理入口](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L930)。
2. DeleteOldRecipePR根据旧配方名称查ID，临时修改ProductConfiguration.FilePath，清缓存并读取旧产品配置。按异形/普通产品分支生成候选PR名称，再把路径改回当前配方并清缓存。没有finally保护路径恢复；中途抛异常可能留下临时路径或缓存。见 [删除选择](../../trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs#L1169)。
3. 将仓库实体名称与候选名作完整相等比较，收集实际存在的名称，逐个调用DeletePREntity，最后再次保存视觉仓库。Contains匹配为注释，不是这条删除链的当前行为。删除范围是列出的产品定位PR，不是按前缀删除所有配方资源。见 [筛选与执行](../../trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs#L1231)。
4. DeletePREntity先按名查实体；不存在直接返回。存在则计算.prc路径，文件存在时先File.Delete，再移除内存实体并Save。文件删除失败会阻止后续内存移除；保存失败则由Save内部记录日志吞掉，磁盘文件与内存变化不会回滚。见 [单PR删除](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L773)。
5. VisionEntityRepository.Save先写主JSON，若主文件存在，先删旧备份，再复制当前主文件到备份。备份是保存后的当前副本，不是保存前版本历史，也不包含.prc文件。复制失败时旧备份可能已经被删；catch只记录日志，没有成功返回值。见 [仓库保存](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L109)。
6. Machine.InitPR启动视觉初始化时，若内存PR列表为空且备份文件存在，会删主JSON再从备份复制。该代码块没有重新读取或替换已经缓存的VisionEntityRepository，后续Find仍查询内存列表；不能把文件复制成功当成内存恢复成功。见 [启动恢复分支](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L139)、[缓存GetInstance和Find](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L43)。

## 删除选择、状态与外部边界

|路径|源码实际行为|不能推断的保证|
|---|---|---|
|旧配方异形分支|对旧产品BaseConfigs的LocateConfig.Name，拼oldName + 名称 + Mark1至Mark4|不代表按完整引用图寻找共享资源，也未包含普通分支列出的全部类型|
|旧配方普通分支|固定TU左右/普通定位、基板和基岛Mark及ID识别；再枚举每个焊点的Mark1至4和ID识别1|本方法没有枚举全部供晶、顶针、吸嘴或其他业务资源；不是“删除所有关联PR”|
|路径恢复|恢复为PathConfig.RecipeDirPath/ProductConfiguration.json，再清缓存|恢复语句不在finally；没有锁保护整个临时路径操作。不能证明并发访问隔离|
|按名查找与移除|Find用List.Find返回首个相等名，RemoveVisionEntity只Remove该对象|不是按名称一次清空所有重复项；不检查其他配方是否共享同名PR|
|循环删除|每个实体删除后各自Save，最后再Save一次|中间失败可能留下已删和未删两部分，不存在全批事务或回滚|

以上依据 [TuService 1169–1255](../../trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs#L1169) 和 [VisionEntityRepository 101–139](../../trunk/AKRS.Galaxy2.PR/Resipository/VisionEntityRepository.cs#L101)。GetPRSavePath属于已复核的算法路径方法：可能创建目录，错误时返回null；删除方法本身未为Alg/null路径提供局部兜底。见 [算法保存路径](../../trunk/AKRS.Galaxy2.PR/Models/Algs/BaseAlg.cs#L325)。

## System1副本方法不能视为自动任务

- CopyTransportUnitPrToSystem1只是以当前配方名和追加System1的目标名调用CopyOldRecipePR。DeleteTransportUnitPrInSystem1则直接foreach仓库PR列表，对名称Contains(当前配方名 + System1)的实体调用DeletePREntity。与旧配方删除的相等匹配不同，这里仍是包含匹配。见 [System1副本方法](../../trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs#L1260)。
- DeletePREntity会移除同一列表的元素，因此该foreach存在集合修改导致枚举失败的静态风险；不是“稳定批量删除”。本轮只确认源码机制，未执行复现。
- 排除bin/obj的trunk C#检索只找到上述两个包装方法定义，未找到直接调用。此前LoadDispensePr函数体全为注释。因此不能把这两个方法画成每次生产/退出都会执行的自动步骤；反射或外部调用仍未排除。

## 其他仓库Remove的真实粒度

|仓库|实际次序|差异与遗留项|
|---|---|---|
|CarrierConfigRepository|先从配置列表移除载具，再依次DeletePREntity处理DieMatch、DieBlob、DieFrame、上下视Mark等，最后使用按条件Remove调用处理若干名称|DieMatchP2的DeletePREntity被注释；DipFluxMatch只有后面的列表Remove调用。因此该方法没有为这两个名称显式删除.prc，也没有在最后统一Save。按条件Remove为外部扩展，内部语义待核|
|EjectionConfigRepository|先移除顶针配置，再DeletePREntity(Name + EjectMatch)，然后列表条件Remove|顶针配置列表已经改变时，PR删除仍可能失败；本方法没有保存配置仓库的显式调用|
|PostBondInspectionRepository|先移除焊后检测配置，再依次删除Name + 1/2/Refer1/Refer2的PR，随后列表条件Remove|没有四个PR与配置仓库的一体提交；后续UI是否保存必须另查；本地基类Remove仅改列表|

依据：[载具Remove](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Repositories/Carrier/CarrierConfigRepository.cs#L69)、[顶针Remove](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Repositories/Ejection/EjectionConfigRepository.cs#L68)、[焊后检测Remove](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspectionRepository.cs#L88)。

## 本地配置基类与界面提交边界

BaseSettingRepository是仓库内源码，不是外部实现。构造函数调用Load；Load读取JSON，返回null才替换为空列表；读操作抛异常时不会进入该空列表兜底。Add/Remove只修改内存，Save才调用SaveGenericList；这些方法没有局部catch、事务或备份步骤。GetDataSourceByCurrentRecipe仅按RecipeIDList包含当前配方ID筛选。见 [基类45–126](../../trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs#L45)。JsonFormatHelper内部仍是未核实的外部边界。

BaseDsSetting.RemoveFromBelongRecipeIds只移除当前配方ID，不删除全局配置对象、其他配方归属或PR文件。顶针设置窗口BtnDelete_Click调用这个方法，随后保存EjectionBankConfigRepository，而非EjectionConfigRepository；这是源码可见的保存对象差异，不能认定顶针配置已经持久化。见 [归属移除](../../trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseDsSetting.cs#L87)、[按钮305–319](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/EjectionConfigurationTeach/FrmEjectionSetting.cs#L305)。

该窗口OK调用Save：设置顶针库程序名称→保存顶针库→保存顶针配置→重建顶针库运行实体→保存WaferSystemProgram，随后置DialogResult.OK；链上没有局部事务回滚。Cancel处理器只设置DialogResult.Cancel，没有撤销先前内存修改的代码。因此不能把取消按钮视为撤销全部编辑。见 [Save216–223](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/EjectionConfigurationTeach/FrmEjectionSetting.cs#L216)、[OK/Cancel327–340](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/EjectionConfigurationTeach/FrmEjectionSetting.cs#L327)。窗口关闭事件或外部调用者的进一步行为仍需另查。

## 交接验收与缺失项

- 已复核本仓库可见删除选择、PR文件/列表次序、单副本备份和启动恢复外层；外部FrmRecipeManage、JsonFormatHelper、Singleton及按条件Remove扩展契约尚未确认。
- 待受控测试：临时路径阶段异常、第二个PR删除失败、只读/被占用主JSON、备份复制失败、空内存列表恢复、共享名称/重复名称，以及System1包含匹配和枚举修改。使用临时测试目录和副本，不直接执行生产删除。
- 待继续追踪：各维护窗口的Remove→Save顺序、模板运行实例是否卸载、配置引用有效性与复制失败的补偿机制。
- 证据台账说明“已见源码行为”，不等于上述风险在现场一定发生；也不等于全部模块或配方生命周期已验收。
