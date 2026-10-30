# 完整原程式/仓库的原生就绪与保存验证

独立原生CLR4.0.30319.42000检查58项通过。宿主绑定全部16个资源版原源码程序集的实际物理位置，业务方法来自1137份原Compile源码的完整Main产物。只有宿主和断言是新测试代码，原源码/源码程序集声明未改写。宿主EXE的Application.StartupPath自然使原PathConfig定位隔离Settings；未替换Root字段、PathConfig、SDK Singleton、仓库或程序实现。16个程序集的加载位置核验不表示对16个项目都执行了业务方法。

原Nozzle/NozzleShelf构造、原仓库初始化与配方关联、NozzleShelfProgram就绪/选择、位置参数查找、PostBondProgram和完整BondProgram.SelfCheck以及WaferSystemProgram的静态华夫盘载具遍历已执行。3个原仓库通过实际SDK JSON Save/Load；锁住目标文件时保存抛IOException，解锁后旧字节保留且再次保存/重载恢复。此确定性锁测试不解释此前278项准备中两次意外File.Replace失败的唯一根因。

## 已复现的就绪逻辑差异

1. [NozzleShelfProgram.SelfCheck](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs#L224)在两个OnBondHead槽位时仍true；[取工具方法](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs#L131)却抛“超过一个”异常，当前槽位选择返回第一个。只读IL确认自检实际调用LanguageExt的Find→Option.Count，得到的是0/1；另一个方法才调用Enumerable.Count。真实仓库保存重载后仍复现，TouchDown系统工具未示教也在原自检排除范围中。
2. [完整BondProgram.SelfCheck](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L162)对实际载具的零坐标上视/下视拍照点均true。实际SDK两份独立零点的Equals为false，Main的IL绑定System.Object.Equals两次；在力控关闭、真空延时满足等明确前提下执行完整原自检，零坐标拒绝分支未进入。选下视时上视点null仍先异常；下视点null也异常。关闭静态华夫盘或载具名称不存在，会在遍历前排除配置。未验证弹窗分支/真正示教或相机，不能据此宣称现场生产通过。
3. [PostBondProgram.Find](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/PostBondProgram.cs#L78)边遍历边RemoveAt(i)。配置ghost-a/ghost-b/post/ghost-c首次查找留下ghost-b/post；随后CanWorkProperly删除ghost-b并跳过未完成post，返回true；下一次无失效前缀时返回false。null名称列表视为空配置而通过；重复名会重复对象及模板名。真实仓库重载保持正常已完成配置的就绪与补偿标记。

以上是隔离数据上的实际原程序集结果，未证明部署/设备发生对应事故。其余边界包括无效示教枚举可通过、空helper拒绝、找不到吸嘴时列表筛选异常、配置8个槽但位置数组仍7个时越界，以及位置方法按数组下标而SlotPosition按存储Index；均在58项中单独登记。

## 证据与范围

首轮测试编译有两处错误路径属性名，实际exit1/两个CS0117，原脚本和输入保存。随后宿主启动失败exit-532462766，终端仅有Exception.ToString失败提示，未拿到完整初始堆栈；将JSON格式化延后至NoInlining方法后可以先安装程序集解析器，未将推断写为已证明异常类型。之后30项通过时“Equals可比较零点值”的测试假设失败；修正零XYZ断言并保留实际Equals差异，进一步用完整Bond自检复现零点放行。49项早期范围的名称/顺序是当前58项前缀，其JSON时间差异未误报为相同；最终测试显式指定CreateTime和耗材LastAlarmTime，再冻结、重编译与运行。

最终原生58项与重放都actualexit0，测试EXE哈希及全部结果逐字相同，3个保存JSON字节哈希一致；6个已知数据文件在隔离宿主中重置，不删除原工程/全局目录。44项新增冻结绑定父3215项，共3259项。见[测试](native-program-readiness-test.json)、[审计](native-program-readiness-audit.json)、[进度](native-program-readiness-progress.json)。

本58项不同于历史SDK启动58项，不合并旧1328/278/119/98/124或40专题3817快照。未执行原Program.Main、窗体/报警UI、PR复制/删除/算法、真实目录具体节点DoWork、轴/相机/设备或织入；现有许可证5次exit1、Fody兼容性2次exit1及VM依赖5次失败保持，资源388/1498通过保持。完整域/动作、就绪负分支、校准/测量、文件IO稳定性、原构建/部署/UI/设备仍待验收，16工程29组1436文件13项整体未完成。
