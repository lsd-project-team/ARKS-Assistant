# 原预点胶谓词、板位置分配和下层失败传播

两个全新 Framework CLR 宿主各30个不同断言通过，原来料 helper 的实际非 Success 预点胶分支已执行。父5571+新增90=5661冻结绑定；61个原方法 IL 包含45个静态 Xtra Show 重载，不能说61个方法均执行。18个原源码哈希、16个保真资源程序集物理加载；本轮没有启动完整生产任务。

## 原谓词与公开测试前提

完整原 S1/Transport/SDK 构造器、真实四实体载具树、一个启用步骤及真实空胶型仓库对象；Machine Working/OffLineWork、硬件仓库空、safeDoor=false、Belt。实际原 Init/InjectSteps/GetNext/FinishCurrent 选中原点胶节点；跳过其他消息不代表实际执行这些动作。公开配置就绪标志与状态是明确fixture，没有写私有消息、替换原动作、单例、线程或SDK实现。

原私有 IsDispense 绑定真实 receiver：Off/Off为false；manual=true在查找缺失点胶头之前返回true；Periodic的IntMax间隔尚未到期、负间隔-1为true（明确无效配置测试，不是实际频率等待）。BeforeComingFirst需要当前实际点胶节点和first标志；无当前或first=false为false。BeforeEveryDispense时机单独配置、Mode Off仍为false，整原DoWork返回Success，不更新LastDispenseTime。

实际空 EpoxyApplication 的 DispensePatternParas.Count=0，不代表有效物理胶型。原板公开 AssistanceFinish=true、Rows2/Columns3、起点(10,20,30)/终点(30,40,999)，原InitPre/Save产生2×3位置：按列优先分配(10,20,30)、(10,40,30)、(20,20,30)，Z取起点30。count0/-1返回空且Index不变；显式无效Index=-1和7分别先提交到0和8，再原数组越界。原仅在Index等于长度6时检测耗尽；DryCycle在这个等值边界重新初始化并返回首点，Index1，无报警。

## 原整预点胶和来料失败

每轮原PreDispenseAction.DoWork共5次：谓词未触发的Success一次，以及启用后4次Alarm。公开WorkStart/WorkStop各5次，原节点Stop且manual=false。失败之前板位置已被分配，最终Index4；私有LastDispenseTime仅反射读取，未写，失败前后保持。

|实际原前提|执行到的原失败|原结果|
|---|---|---|
|缺少命名DispenseCoordinateSystem|原ConvertG0ToMachinePos NullReference|Alarm|
|公开添加真实SDK GeneralCoordinateSystem，未设父系|原GetG0DispensePos缺标定点NullReference|Alarm|
|公开设置两个真实Point3D零标定点|空胶型数学/克隆后原AxisZAbsoluteMove缺Z轴|Alarm|
|已Set来料，再直接绑定原GetInputSignal|再次执行原预点胶，缺Z轴|helper false，来料State仍Set，设备Working|

真实SDK无父坐标系的转换为恒等，两个零标定点是明确公开测试模型，不能说取得机器实测标定。原AxisZAbsoluteMove没有OffLine短路，本轮因实际缺轴报错，没有运行轴。原插补控制器捕获缺Z轴返回Fail，原预点胶把它转为Alarm；原输入门先检查预点胶结果，再检查Stop或消费来料，故返回false并保留State。Working是观察点状态，fixture最后调用原Stop收尾；完整离线生产任务通常跳过输入门，本轮直接调用真实任务receiver上的原helper，没有声称整个任务经过这条链。

公开MainForm.SendUiAction收集4个Action，递归只读检查编译器闭包中的文本，没有执行这些Action或构造窗口。文本含两次真实NullReference和两次缺Z轴。原Xtra包装器路径下DBService Lazy始终未创建。

原AKRSMessageBoxExt.Alarm另有直接DBService.Insert→ExecuteCommand调用，不是排队；真实DBService构造器还连接本地SQL、创建表及CleanInfo。该IsAlarm=true分支本轮没有执行；收集UI委托不会阻断SQL语句。本轮明确配置IsAlarm=false，执行原Xtra路径，不据此声称SQL持久化或报警库已验收。

~~~mermaid
flowchart TD
  A[原IsDispense谓词] --> B{本次触发?}
  B -->|否| C[原Success / 时间不更新]
  B -->|是| D[原板GetEpoxy / Index先提交]
  D --> E[原坐标转换 / 缺坐标系]
  E --> F[公开真实坐标fixture / 缺标定点]
  F --> G[公开零点fixture / 原缺Z轴]
  G --> H[控制器Fail / 原预点胶Alarm]
  H --> I[原输入helper false / State保留]
  H --> J[收集UI Action / 未执行 / DB Lazy未创建]
~~~

## 失败记录与边界

前三版原CLR运行各21/21/25检查后exit1：初始错误预期直接缺Z轴，实际更早缺坐标系；递归闭包检查后取得真实NullReference；添加公开真实坐标系后实际仍缺标定点。三个独立失败目录及对应Cases/Probe/编译记录均保留。第四版与重编译分别在两个全新accepted目录各30固定检查成功；结果/标签严格一致，独立路径和stdout不宣称字节一致。

162编译引用含10个直接源程序集引用，runtime-map172项，两轮实际加载16个bound/replay保真源程序集。父原重做与保真资源在guarded流水线85770/0f8521通过；冻结后验证129d7e为无session完成，不为子命令虚构会话。

没有生产C#/工程修改、私有状态写入、硬件/动作替身、物理预点胶/点胶、轴移动、挤胶、相机、真实UI、SQL、完整原MSBuild或部署。补充图不更新正式1328、旧40专题3817或主阅读器。继续S2原安全/吸嘴架/清零/补偿前提，原整Retry传播、完整生产握手退出及工程/设备验收；16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-predispense-prerequisites-test.json)、[审计](native-predispense-prerequisites-audit.json)、[进度](native-predispense-prerequisites-progress.json)。
