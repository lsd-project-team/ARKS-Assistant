# 原界面停止事件与任务关闭恢复验证

两轮各572项检查通过，共1144项；每轮实际执行261次原Designer绑定的取消事件与离线Machine.Stop、570次原ChangeUiByState、8次实际原配方重载（4成功/4晶圆Save失败）。25项阶段绑定通过，155新增+12379=12534，481复用。整体目标未完成。

|真实界面行为|观察结果|验证范围|
|---|---|---|
|取消事件后刷新|Stop且控件禁用、提示恰为“设备正在停止，请稍后”才进入关闭检查|实际原控件/原标签/原事件，公开PerformClick程序化触发|
|八种Task状态×16持有者×2个S1配置|256行中225恢复/31等待；129个恢复行的Task尚未完成|Task状态矩阵是显式公开持有者夹具，和实际业务Task分开计数|
|实际S1 Task保持Running|原取消先改Stop，但不等待此Task；UI继续禁用|一个真正原S1 Task，公开WorkStart回调等待|
|S1配置关闭/重新打开|关闭配置使仍Running的S1退出检查并恢复UI；再打开配置，已恢复UI不会重新禁用|同一个原S1 Task句柄，重新检查原Machine闭合条件仍false|
|实际S1故意Faulted|重新取消后保持等待；回调抛出的同一异常对象令Task故障，随后UI恢复|故障是公开夹具注入，在节点原DoWork主体之前发生|
|配方Save失败且保留旧停止提示|Stop行可恢复UI，四个配置已部分更新且PrInitSuccess仍false|四行实际文件锁/保存失败，不把UI恢复当作配方完整或PR成功|
|Operate/Teaching/Preparing刷新|配方按钮保留此前Stop或Working的启用状态|两个起点×全部6个原状态枚举=12行|
|两个“加载产品”入口|BtLoadProduct原事件为空；BarBtLoad需要原模态FrmLoadRecipe|空事件实际PerformClick，主加载/新建模态事件本轮仅原源码/IL|

原UcMainSystem、Designer、本地化及16个原源/资源程序集在Framework STA宿主正常构造。取消分别经BarBtCancel与BtCancel的真实Designer订阅执行；两者均调用原BtCancel_ItemClick。公开DevExpress BarItem.PerformClick实际检查自身Enabled，允许时调用OnClick；它没有检查父控件Enabled。程序化事件激活不能推广为用户鼠标可点，未显示或渲染原主窗体、未运行消息泵。

矩阵开始前通过公开状态/控件属性恢复测试起点，再让原ChangeUiByState切到Working；原取消置Enabled=false、更新停止提示、显示标签、调用原离线Stop。其后原刷新遍历实际16个公开任务持有者（S1配置关时15个），只拒绝TaskStatus.Running。Created、WaitingForActivation、WaitingToRun、WaitingForChildrenToComplete尚未完成但会恢复；RanToCompletion/Canceled/Faulted也恢复。Running的31行被拒绝，S1配置关的Running行则被遗漏。另测旧transferLoadBeltToBondTask仍Running而不在原列表，UI也恢复。矩阵中8个状态持有者及附加子任务均在结束前终结，和一个原S1业务Task分开描述。

关闭检查拒绝时，原ChangeUiByState提前返回，连机器缓存状态、单步开关及连续上料刷新都跳过。31行中原Stop已经将机器IsSingleStepWork=false，但界面开关仍Checked=true；完成条件通过后才刷新。这证明界面提示与按钮不是通用任务终止证明。

实际S1入口沿用原产品/流程、原动作节点和原Start，公开WorkStart只保持事件并在释放后抛出指定InvalidOperationException。一次原Task启动/一次Faulted，未替换节点、未写私有字段、未执行节点主体成功或物理测高。原取消不Join该Task；关闭S1硬件配置会在它仍Running时恢复界面。配置再开后控件已Enabled，提示已隐藏，刷新不再调用关闭检查；原Machine.IsAllowTaskClosed仍false。通过另一个真实取消按钮重新进入等待，再释放回调，原Task保留Faulted持有者，原刷新仍恢复。故障来自夹具，不认定为原业务自然故障。

四个配方文件锁行分别覆盖Stop/Pause与初始切换提示/原取消遗留停止提示。为比较初始提示，前两行用公开Text属性恢复原Designer字符串；后两行先实际取消并恢复界面，标签隐藏但Text仍为原停止文字。ReLoadRecipe从未重置该文字。实际晶圆Save在try/finally之前失败，前4单例替换、后2保留、UI禁用、Pr=false；每行磁盘字节不变、原通用Exception无InnerException。原刷新只有“Stop+旧停止文字”的一行恢复Enabled并隐藏提示，Pr仍false、部分提交仍在。其他3行保持禁用。随后每行程序化私有重载重试才使六单例一致并将离线Pr标志恢复；不证明禁用界面上的物理点击可重试。

6个原MachineState枚举为Stop/Pause/Working/Operate/Teaching/Preparing。原刷新仅对前3种改变按钮；其余3种虽更新缓存状态，但没有对应UI分支，所以从Stop进入会保留配方按钮启用，从Working进入会保留禁用。原IsWorking只识别Working，且主加载/新建事件没有直接IsWorking/IsAllowTaskClosed检查；它们经ShowDialog后先SaveMachineConfig再重载，Dispose位于重载后，且没有异常处理器。本轮没有运行这些模态选择器，不把静态顺序等同于完整交互验收。

本轮实际SQL候选队列计数261，和261次原Stop状态变更一致；原SetState→ParameterChangeLogEntity→队列添加路径由原源码/IL绑定。没有启动SQL消费者或写数据库。原Load执行一次，创建隐藏句柄并登记一个SDK UI刷新记录；原热键注销和公开RemoveTask删除登记。SDK原基础线程的StartNew由IL确认，但Task句柄与正常终止未捕获。原固定D盘测试目录在成功宿主前后均已存在。

14份JSON中11份原字节两轮相同；两份Bond与晶圆设备参数只对原构造器5个精确时间路径模式/8个实际值做语义比较，所有原字节及SHA独立冻结。配方列表保留原未命名默认Recipe并加A/B，日期及ID使用公开固定夹具。源证据346声明/230原源文件，125原IL方法/7程序集；严格编码、UTF16位置及符号记录保持。原172项runtime-map及23精确SDK身份/16补充/1缺失保持父台账；缺log4net1.2.15，不进行版本替换或在线VM验收。

保留一次编译导入错误，失败宿主未进入CLR，原运行器拒绝记录也保留；成功两轮宿主未为文档或只读校验重跑。无生产C#/csproj编辑。

证据：[测试台账](native-ui-stop-recovery-test.json)、[观察审计](native-ui-stop-recovery-audit.json)、[进度](native-ui-stop-recovery-progress.json)。16项目、29组、1436文件、13项任务范围保持，29组仍partial，旧正式1328独立。主加载/新建模态交互、完整Program/MainForm、整机Start/Prepare/CleanFile、设备运动/视觉、SQL与完整MSBuild生产链仍待验收。下一步继续原加载/新建选择器及初始化事件的真实交互、任务故障与许可契约。
