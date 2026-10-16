# 原检测仓库接完整启动、实体与输送组合

1303项受控检查通过。原PostBondInspectionRepository的单例、类型化查找与PR联动，BaseSettingRepository的构造、Load/Find/Filter/配方查询/Save，以及原BaseDsSetting初始化和配方成员，已接入原产品准备、两条UI、实体树、坐标、生产器、真实供晶Task/Stop与五阶段输送。独立统一回归及阅读器结果由验证回执登记。全16工程、29组、1436个C#文件及13项要求仍未完成。

同一Run重跑此前1209项，再执行44项原UI和50项仓库检查。七个原静态断言位置对应12个运行断言迁移，四个名称变化，其他原断言名称和顺序保留。原错误对象类型注入来自字典适配器，强类型列表不能直接包含任意object，因此改为原未教对象掩盖后续null；查找记录钩子改为实际列表/初始Load边界。498条提取记录对应497段唯一源码，含268方法、186属性、18枚举、24字段、2结构体及23信号契约。旧180个正式输入和186个准备输入保持原哈希。独立50/44准备不再额外相加。

## 单例、加载和原查找

原GetInstance持有BaseSettingRepository<PostBondInspection>.locker，在首次构造中调用原Load和虚GetFileName；构造失败不发布instance，后续调用重试。成功后缓存同一实例。显式Load替换当前列表，读取异常则在赋值前发生而保留旧列表；null读取创建新空列表。文件名随当前路径变化影响Save，成功的缓存不会自动重载。并发首次调用只构造并读取一次。

原Find按List<PostBondInspection>.Find取首个同名对象，不按Recipe或IsEnable过滤。null名称可匹配；早期命中掩盖后续null元素，缺失时访问null会抛异常。原Filter用大小写敏感Contains和启用状态；按当前RecipeID查询仍包含disabled对象。原BaseDsSetting名称/复制名、启用和编辑状态、时间及RecipeIDList初始化、原成员Add/Remove均编译；AOP通知基类仍是声明边界。

## 两条UI与完整旧链

两条原UI在首次单例Load/Find/原检测状态的共同路径上验证：默认未教、禁用backside却显式UnAble、null状态、缺失名称、null读取、初始读取异常、null元素及首个重复项未教都阻断模块、生产器和供晶，机器Stop且尚未进入TransportDomain.catch。已教、跨配方但同名已教、早期命中后null则启动原一焊点实体树；每次首次访问原单例只加载一次。跨配方通过属于源码行为，尚未认定符合配方隔离要求。

历史Items字典、Read返回钩子及Lookups记录字段在完整组合中移除。健康Setup/Grid仍明确设置示教输入，原构造/Reset默认值保留。此前原实体/坐标数值、16状态、异形缓存与递归、可选检测、Save早期失败与缓存重试、五Task/WaitAll、29节点树、五阶段连续输送、Refresh/异常前缀及Stop/Pause断言全部重跑。新增UI和仓库检查位于同一RunCore的资源finally之前。

## PR修改顺序与部分副作用

原Add按照视觉列表顺序寻找CopyName+1/2/Refer1/Refer2并复制，重复PR名称会重复复制；之后视觉Save，最后加入检测列表，不保存自身JSON。复制失败、视觉Save失败及null自身列表分别保留此前副作用。原Remove先移除检测项，再四PR删除和四视觉列表移除，不保存JSON或视觉库；删除失败不恢复已经移除的检测项，原列表不存在对象时仍尝试删除PR。

原GetPostBondPREntityNameList按配方枚举Name+1/r1，与Add/Remove所用2/Refer1/Refer2不同。上述PR复制、删除、视觉Save和列表扩展仍为动作适配器；未声称实际PR库、相机或SDK联动已经验收。

## SDK范围及下一步

完整1303组合的JSON、路径/配方上下文、PR/视觉扩展、产品单例加载/Save、VM、动作和硬件SDK仍有适配器。原成员保持原文，由合成类声明/别名连接；与独立50项直接编译三个完整原文件的范围不同，本组合不声称完整原工程构建。

另行完成[真实JSON/单例SDK数据验证](inspection-repository-json-sdk-progress.json)：两个独立Windows .NET Framework进程分别加载libs/bin DLL，对合成类型和隔离临时文件各执行相同26项断言，52次放置不是52种行为。两份DLL字节不同，所选16方法IL/方法信息一致，不能据此推断依赖或部署等价。真实成员错误被Handled=true后可能保存或返回保留默认值的部分对象；缺失列表文件创建为空并返回null，缺失对象不创建文件。目录创建失败位于有关catch外。根JSON语法错误的原生MessageBox路径、原模型默认状态/AOP/通知及原产品Singleton生命周期尚待集成验证。

下一步[8段原产品初始化声明及正确编辑枚举](transport-product-config-declarations-next-evidence.json)，再接实际SDK与原配置/仓库默认状态。原工程构建、部署配置/DLL、原生UI/设备及全部29组/13要求继续未完成。

验证命令：`node scripts/test-transport-inspection-repository-integration.cjs`、`node scripts/build-transport-inspection-repository-integration-audit.cjs --check`。SDK数据探针属于独立验收范围，不与本1303项相加认定覆盖。
