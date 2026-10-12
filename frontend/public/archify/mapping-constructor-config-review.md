# Mapping恢复：生产载具构造与配置副作用

更新：2026-09-28。本轮分析trunk原始源码，未运行生产构造器、设备或配置保存。

## 工作流摘要

码值读取方法先读取文件，再new TransportUnit(字符串原因)。该构造器先Init，再赋时间名称；Init从当前ProductConfiguration取配置，创建坐标及子实体，执行ModifyMatter，再注入S2/S1步骤。读取方法在构造返回后再次注入，最后才写文件头信息和恢复网格。因此文件格式处理前已有对象构造和配置相关调用；不能将此入口解释为纯文件解析器。

## 已确认的配置修改

- TransportUnit.InitSubstrateCoordinateSystem（285–343）：直接取得当前SubstrateConfig。当IsMultiple为false时，把Count/行列设为1，清空坐标列表并加入默认坐标；手工输入间距模式会以首坐标重建整张坐标列表。实体创建使用Count，行列标签仅在Matrix分支设置。
- Substrate.CreateModule（104–162）：对当前ModuleConfig做类似处理，再按Count构造Module；此方法显示的常规分支没有先清空Modules，不能脱离调用条件声称重复调用幂等。
- TuService.ModifyMatter（887–956）：异形分支从每个焊点OppositeSex取状态；普通大数量分支用基板/模块索引定位状态列表并按焊点名称查找；普通非大数量分支只在匹配项存在时写状态。
- ModifyMatter的catch调用OtherConfig.ClearInformation及ProductConfiguration.Save。这证明有清理和保存调用，不证明外部保存一定成功；若清理或Save再次抛错，该catch没有新的保护。已写入部分实体的状态也不能据此视为自动回滚。

## 证据与验收边界

源文件：TransportUnitSystem/Module/Matter/TransportUnit.cs 73–125、285–357；Module/Matter/Substrate.cs 51–175；Service/TuService.cs 887–956、1953–2079（均位于trunk/AKRS.ZX2200）。精确片段已登记在下方源码阅读器链接。

现有25项编解码测试使用受控构造替身，不覆盖这里的生产构造副作用。下一步核对Module/BondPosition创建、ClearInformation具体范围及仓库配置样本；真实配置加载/保存和实机恢复仍未验收。

## 子实体构造的进一步核对

Module常规构造先按当前配置计算WorkIndex，再用ElementCoordinates[index-1]创建坐标、创建ModuleInfo，最后CreateBondPosition。该方法清空BondPositions，并按SingleBpPositionConfigList每项的名称和序号创建焊点。BondPosition按名称经BaseMatter.GetConfigByType查找配置，再读取坐标与IsMirror；缺少同名配置时这里没有自动补默认值。异形分支则逐层沿DownConfigs创建，并取各层OppositeSex坐标及配置。

ArrayConfig中的Count、RowCount、ColumnCount是分别可写的属性；本轮已读构造循环按Count创建，Mapping按行列循环恢复。不能从这些定义推导三者始终一致：仍须核对编辑/加载路径与真实配置，不能凭这一局部差异宣称必然故障。

## 原始状态处理方法：14项隔离测试

命令：`node scripts/test-mapping-constructor-state.cjs`；[结果](mapping-constructor-state-test.json)。原样提取ModifyMatter和ClearInformation，使用源码中的状态结构体和枚举；仅为C#5编译器在两个结构体构造器补 : this() 初始化，其余实体/配置采用最小内存替身；Save仅计数并可抛出受控异常。没有运行完整构造器、AOP、真实单例、坐标、磁盘保存或设备。

验证普通列表匹配/不匹配、索引赋值、完整大数量配置、缺名/空数组、异形状态、空焊点配置及catch内二次异常。索引越界样本中，第一个实体已被设为Disable，随后访问不存在的模块状态数组触发catch，配置重建为Enable，但第一个实体仍是Disable；catch没有回滚或重新套用配置。ClearInformation清MatterProductInfo并按当前数量重建全部Enable的二维状态列表，但不清BpSingleSeparates。清理异常阻止Save；Save异常在配置已清理后向外传播。测试通过表示行为符合这些预期，包括风险表现。

这些配置副作用曾在模块复核中静态记录；本轮新增原方法实验和子实体构造证据，不重复宣称新发现或扩大覆盖率。

## 可用材料与下一步

[材料盘点](mapping-material-inventory.md)扫描trunk内5525个文件（含bin，排除.git/.vs/obj/packages与符号链接），得到22个JSON/TXT/CSV候选；未发现七类指定核心配方文件同名项。这不是任意扩展名、归档、仓库外资料或现场文件的全面搜索。不能把调试目录下设备参数及零GUID统计文件当作已认证生产配方。

下一步需实际配置的Count/行列/坐标/焊点名称/制程键一致性材料；继续静态追踪配置编辑路径与构造调用方。整机恢复是否无重复、无遗漏仍需R01–R12记录，保持未验收。

[恢复验收清单](mapping-recovery-acceptance.html) · [Archify恢复图](mapping-restore-workflow.html) · [模块复核](transport-unit-module-review.md)

## 源码阅读器直达

- [tu-construct-init](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=tu-construct-init)
- [tu-coordinate-create](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=tu-coordinate-create)
- [tu-modify-matter](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=tu-modify-matter)
- [tu-clear-config](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=tu-clear-config)
- [restorebuild-sub-mod](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-sub-mod)
- [restorebuild-module](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-module)
- [restorebuild-bp](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-bp)
- [restorebuild-config](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-config)
- [restorebuild-array](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-array)
### 测试结论更正（2026-09-28）
上一版把生产结构体错误模拟成类，导致“缺名触发catch并清理”的断言无效，现撤回。生产MatterProductInformationMin为结构体，Find缺名返回默认值，MatterProductState默认Enable；更正后测试确认缺名不触发catch/Save，并可将实体原Disable覆盖为Enable。部分写入保留改由真正的模块数组越界用例验证。14项隔离断言通过，不等于生产运行验收。
