# 晶圆地图运行链路：源码复核

更新：2026-09-28。范围是 trunk 内 Block 的地图加载、初始化调用、SearchMapping、参考晶粒补取和取晶后更新。本文说明已读到的调用与控制流，不替代地图库内部算法、设备运行或完整并发验证。

## 工作步骤摘要

换片初始化 → 本地地图复制/打开 → 设置及定位参考点 → 移至策略当前点 → 请求异步寻路 → 重置参考晶粒补取列表 → 按地图获取下一位置 → 视觉判断及移至取晶中心 → 取晶侧调用 RefreshMap → 更新已取状态并请求保存 → 继续搜晶；地图无可到达晶粒时，按开关补取参考晶粒或置换片状态并返回 false。

初始化的调用先后与模式条件见 [换片初始化复核](carrier-change-review.md)。取晶侧何时调用 RefreshMap 见 [供晶与取晶握手](wafer-bond-handshake-review.md)。

## 1. 文件输入与打开地图

[Block.LoadMap1210–1256](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1210) 把操作交给 MainForm.SendUiAction：

1. 仅 CarrierWithWaferConfig 进入文件路径；Waffle 或其他配置直接抛异常。
2. 初始目标是 WaferMapFilePath 与 fileName 的组合；目标已存在则先删除。
3. 从 WaferMapRepositoryDirPath 查找文件，按不带扩展名的名称匹配当前载具名称；匹配后，**filePath 被改为 Path.GetFileName(a)，不再是前面的组合路径**。
4. File.Copy(sourceFileName, filePath, true)，随后 WaferMapII.OpenFile(filePath)。匹配后的相对文件名由运行时工作目录解析；不能声称所有地图都写入配置目录。

[GetWaferMapRepositoryDirPath1611–1617](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1611) 返回程序目录下 Config1。`isDownload` 是参数名称，这个方法内未见网络下载调用；文件复制不能画成远程 API。无匹配文件时保留初始源文件路径，是否存在由 File.Copy 的实际结果决定，方法本体无专门缺文件恢复分支。

**UI 调度已经找到实现：** [MainForm50–71](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L50) 声明静态 Action<Action>，构造函数把 PostAction 加入委托；PostAction 直接 `this.Invoke(action)`，不是 BeginInvoke 或 Task.Run，本方法没有 catch。地图和向导调用应标成该 Invoke 调度路径，而不是后台投递后立即完成。委托绑定前调用、窗体释放及异常包装的实际表现没有运行验证。

## 2. 参考点、起点及寻路

|步骤|已确认行为|源码|
|---|---|---|
|SetReferencePoint1|设置地图间距，参考点列表为空则抛异常；无参版本将当前 G0 坐标乘 1000 后写入首个参考点；Point 重载直接使用输入 Point|[224–254](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L224)|
|FindReferencePoint|保存地图当前点；依次启动首点到首点、前一参考点到后一参考点的寻路；等待结果，非 Found 抛异常；沿中间点移动、匹配和更新坐标，到非跳板点结束该段；最后恢复原地图当前点、光标设到末参考点|[259–361](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L259)|
|MoveToStartPoint|取当前策略 CurrentPoint，找到最近参考点，启动到 CurrentPoint 的寻路；等待并检查结果，沿路径移动、匹配及更新物理坐标，直到地图位置等于目标|[366–446](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L366)|
|StartAsyncSeekingPath|仅在没有待补取参考晶粒时，SetStrategyCompleted(0,false)，调用库的 StartAsyncSeekingPath(false,ValidAndVoid,LocatedChip)|[204–211](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L204)|
|InitMapInfo|仅 SearchMode.WaferMap 时把 pickingRefDieInfo 设为 null；不是完整地图加载或准备检查|[1149–1155](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1149)|

**等待与失败范围：** FindReferencePoint 和 MoveToStartPoint 的等待体都是空循环，调用 WaitForAsyncResultBetweenTwoPoints(0,out result)，本地没有统一次数上限、延迟或 StopSearch。参数 0 的超时语义由库决定，不能在未读库实现时断言为非阻塞或无限等待。两个方法的视觉匹配失败并非都抛异常：失败且为跳板会采用当前位置；失败且非跳板没有专门抛错分支，随后仍可能写坐标。需以现场验证评估实际影响，不在分析任务中擅改控制程序。

## 3. 地图搜晶循环

[SearchMapping46–124](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L46)：

1. GetNextPositionInfoAndForwardTo 获取当前晶粒信息，转换物理坐标。
2. 实际实现仅覆盖 IsPositionSearch + StandardSearch + 非两点定位；两点定位、MultipleSearch 或未开启位置搜索均抛异常，注释内的两点算法不能作为可用功能。
3. 移动至搜索位置，AnalyseDie(IsSpringboard,out isSkip,DieMatchName)。启用预取且跳过普通晶粒时，再调用地图 Forward 接口。然后写入当前晶粒物理坐标。
4. StopSearch；跳板或被跳过时继续循环，否则 MoveDieToPickCenter，返回 true。true 表示本次搜索走到成功出口，不是实际完成取晶。

跳过判断的内部规则见 [供晶复核中的 AnalyseDie](wafer-bond-handshake-review.md)。

## 4. 正常晶粒与末尾参考晶粒的不同状态

[GetNextPositionInfoAndForwardTo453–491](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L453)：

- pickingRefDieInfo 为 null：走正常地图；启用预取则 PreGetNextPositionInfo，跳板才立即 Forward；未启用预取则直接 Forward。
- 列表非空：读取第一个参考晶粒，**这里不移除元素**。
- 列表存在但为空：抛 PickRefEnd。null 与空列表不是相同运行状态。

[SearchMapping130–186](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L130) 捕获 NoApproachableChipException 后：若 IsWaferMapPickRefInEnd 开启，创建列表，从参考点中筛选类型属于 GetSelectedChipTypeSet(0) 的晶粒；非空则递归调用 NextDie 进入补取。不开启或没有可补取项时，置换载具及换地图标志，当前 SlotState=Bad，保存设备参数，Unlock 地图，返回 false。PickRefEnd 使用同样的结束动作。NotFoundException 转成“晶圆图未找到路径，请重置当前点”异常；其他异常继续抛出。

这解释了 [IsNeedChangeCarrier1161–1188](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1161) 对参考晶粒列表的检查：当内部换片标志为 true、模式为 WaferMap，列表非空仍返回 false。列表移除依赖取晶后刷新；只重复调用 NextDie 不能证明已消费参考晶粒。开关在 Block 中的初始值为 false：[1675](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1675)。本轮在 trunk 的 C# 文本中搜索此完整标识符，只发现声明与上述读取，没有显式赋值入口；因此补取应标为条件能力，不能宣称默认启用。反射或外部调用是否改变属性未验证。

## 5. 取晶后更新与输出

[RefreshMap859–913](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L859) 先按非 StaticWaffle 且非离线条件等待 BondHead Z 与取晶高度之差满足阈值；循环检查 StopSearch。Wafer 配置还调用顶针回预顶起位并吹气。WaferMap 分支随后依次执行：

1. [RemeberPickedDieInfo510–521](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L510)：启用预取时才在此 Forward 并写入 dieMarkCenterG0Pos；最后记录 lastPickedDieInfo。该预取分支没有额外排除参考晶粒补取模式，不能擅自补画排除条件。
2. [RefreshPickedDieStatus526–546](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs#L526)：仍有参考晶粒则 RemoveAt(0)；否则 SetChipType(lastPickedDieInfo.Position)。SetChipType 异常在局部捕获并提示，之后仍调用 AsyncSaveFile。

AsyncSaveFile 是保存请求；这里未等待保存成功。其异常、线程、文件格式和完成回执不能从方法名推断。

## 外部边界与未完成项

- 主项目显式引用 AKRS.WM.WaferMap、WaferMapForm、WaferMapHelper 等程序集：[csproj77–84](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L77)。对应三个 DLL 在 trunk/AKRS.ZX2200/libs 实际存在。本轮 trunk 的 C# 搜索未找到 WaferMapInterfaceImplementer 类定义；这是源码实现边界，不是宣称缺少 DLL。未反编译库，不虚构内部算法。
- 待核实：地图文件选择/解析内部；异步寻路和保存的完成/取消语义；预取与参考晶粒补取组合；设备互锁与现场运行。UI 委托绑定已经读到源码，运行生命周期异常仍未验证。
- 本文尚未同步为新的 Archify 图及完整逐边语义台账，不把已有图形数量作为完成证明。
- 快照存入 [carrier-change-evidence.json](carrier-change-evidence.json)，由现有统一校验检查哈希、行号和精确原文；不表示动态验证通过。
