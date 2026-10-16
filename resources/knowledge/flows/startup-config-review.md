# 真实配置加载到生产启动与排序：有界集成验证

日期：2026-09-29。63项检查通过，执行29份原方法/构造函数/枚举片段，原SystemProcess与ActionNodeMessage完整类，以及项目实际Singleton与JSON帮助器DLL。此为原方法有界集成，不是整机运行或现场故障复现；生产源码未修改。

## 本轮补上的链路

临时ProcessProgram.json → 实际Singleton.GetInstance/项目JSON设置 → 原ProcessDomain检查 → 原Machine.CheckOperatingEnvironment/PrepareMachineReadyToStart/Start → 原S2自检及初始化排序 → 分批帮助器入口。

ProcessDomain类型容器、产品几何与仓库仍是测试包装器；原静态构造、重置、CheckIsReady、IsEnableToWork直接提取。S2 CheckIsReady为完整原方法，其他依赖按场景提供固定返回值。任务Start、轴移动、真空、弹窗是调用记录替身；本测试没有创建生产线程或驱动硬件。

## 非正批次可达性与顺序

开启按次数执行，批次0或-3，TransportFirst/SubstrateFirst及StepFirst/PositionFirst四种组合，共8种临时文件样本。两个原ProcessDomain检查、完整原环境检查均放行；原Start随后到达分批帮助器入口。

收据保存全部8份真实调用轨迹。0/TransportFirst/StepFirst轨迹末段为：

State.Working → Transport.Start → Wafer.Start → S1.Start → batch:2:0。

因此在本依赖配置下，分批排序发生在状态改为Working和三个前置Start调用之后；Bond.Start、Slide.Start及两个晶圆真空检查尚未执行。不能把Start调用记录等同于真实线程已经成功运行。

**安全边界：**测试MathHelper代理记录实参，totalNumber>0且cycleNumber<=0时抛BatchBoundary停止；其余参数委托完整原GetCycleList。没有执行原无限循环，也没有把代理异常当作生产异常。原方法非正批次不推进循环的静态结论见[action-sort-review.md](action-sort-review.md)。本轮证明的是在明确替身条件下到达危险入口，现场仍依赖真实配置、全部业务依赖与线程行为。

## 通过的检查

| 场景 | 断言数 | 结果 |
|---|---:|---|
| 8组非正批次 |16|真实加载后门控放行，到达代理停止点，验证状态和前置调用|
| 8种正批次排序模式 |16|每组4个点胶和4个检测动作，完整后续启动与真空调用|
| 关闭按次数开关 |4|0被几何数量2替代，原帮助器执行完成|
| ModuleFirst/BondPositionFirst |4|本样本负数未被使用，不调用分批帮助器|
| 补偿模式 |1|仍设Working并排序，但跳过输送、晶圆及S1启动|
| 9处前置返回false |9|均阻断Working和任务启动|
| 其他门控、异常与空队列 |13|详见下文|

## 已确认的其他行为

- 未总复位时，文件清理和信号重置已经调用，随后返回，未进入日志准备。
- 安全门未关闭时，缺陷计数已重置，尚未调用安全移动或任务启动。已经Working时同样阻止重复启动。
- S2安全移动异常发生在S1安全移动之后、环境检查之前，并向外传播。
- Wafer.Start替身抛异常时，已调用Transport.Start且状态留在Working；后续S1/排序/Bond不执行。
- Bond.Start替身抛异常时，原排序已经完成；Slide及真空调用被跳过。第一个晶圆真空检查异常发生在任务启动调用之后，并跳过第二个检查。
- 空步骤时ProcessDomain.CheckIsReady返回true，IsEnableToWork返回false。生产Start走CheckIsReady路径；开启S2自检会在已调用焊头真空后拒绝空步骤。关闭S2自检后，本样本可调用Bond.Start且动作队列为空。
- 临时JSON中的未知WorkProcess=99通过这些门控，原排序switch不生成动作，随后仍调用Bond.Start。
- Index=0由最终制程门控拒绝；关闭S1硬件配置会跳过其安全移动和Start，但原环境检查仍调用S1.CheckIsReady。

## 证据与复现

- [测试收据](startup-config-test.json)：63项名称、8份调用轨迹、实际加载程序集、DLL方法IL哈希、原源码片段与全部测试输入哈希。
- [审计收据](startup-config-audit.json)：报告、测试及源码漂移校验。
- 执行：node scripts/test-startup-config.cjs
- 校验：node scripts/build-startup-config-audit.cjs --check
- 浏览器与统一回归另有独立日志；不把这63项代替页面或整体验收。

## 原源码定位

| 文件 | 原成员 | 行号 |
|---|---|---|
| trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs | public enum WorkProcessEnum | 379–404 |
| trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs | public enum WorkProcessModuleEnum | 409–422 |
| trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs | static ProcessDomain() | 29–32 |
| trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs | public void InitProcessProgram() | 37–41 |
| trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs | public bool CheckIsReady() | 179–252 |
| trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs | public bool IsEnableToWork(string useName) | 58–173 |
| trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs | public bool CheckOperatingEnvironment() | 89–128 |
| trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs | private bool PrepareMachineReadyToStart() | 185–256 |
| trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs | public void Start() | 261–309 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | public bool SelfCheck() | 1359–1404 |
| trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs | public bool CheckIsReady() | 594–771 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | public void Init() | 155–175 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private int GetSubstrateCount() | 134–139 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private int GetModuleCount() | 145–150 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void SortActionNodeByModule(WorkProcessEnum workProcess, WorkProcessModuleEnum workProcessModule) | 182–234 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private List<ActionNodeMessage> GetActionNodeMessageByProcess(SingleProcessStep singleProcess, int substrateIndex, int moduleIndex) | 715–875 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private List<SingleProcessStep> GetWorkBondPosition() | 881–885 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | public void RemoveOtherStep() | 1498–1548 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void SortTransportFirsAndStepFirst() | 241–313 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void SortTransportFirsAndPositionFirst() | 318–390 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void SortSubstrateFirsAndStepFirst() | 395–458 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void SortSubstrateFirsAndPositionFirst() | 463–520 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void SortModuleFirsAndStepFirst() | 525–568 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void SortModuleFirsAndPositionFirst() | 573–611 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void SortBondPositionFirsAndStepFirst() | 616–659 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void SortBondPositionFirsAndPositionFirst() | 664–704 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | private void RemoveDisableActionNode() | 1554–1628 |
| trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs | public void SortRelativeBond() | 1440–1493 |
| trunk/AKRS.ZX2200/Infrastructure/Utils/MathHelper.cs | public static List<List<int>> GetCycleList(int totalNumber, int cycleNumber) | 575–595 |

## 仍未完成

完整生产类依赖、真实产品配置/仓库、DevExpress交互、读取错误消息框、任务内部和并发、SDK、缺失项目的完整构建与现场设备闭环仍未验收。分批代理是测试安全停止点，不是交付给生产的防护或修复。29个模块组继续部分复核；下一步应核对真实启动入口的异常承接及配方切换与工作状态的互斥，而不能宣布整条设备链完成。

后续已补[启动入口与配方界面保护](startup-entry-review.md)：43项检查把两个原启动事件、原Stop、原配方事件和六个UI状态方法接到本脚手架。按钮捕获异常后会Stop，Stop再失败时finally仍恢复UI；普通Stop刷新可重新启用配方按钮而不查任务关闭。真实线程结束、原生事件调度、实际配方重载及互斥仍未验收。
