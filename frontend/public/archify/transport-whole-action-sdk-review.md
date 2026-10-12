# 完整原动作控制器与流程模型接实际 SDK

两份 Infrastructure DLL 的独立原生 Framework 进程各通过 278 项检查，共 556 次执行、每份 40 次原启动调用。既有 187 项名称和顺序保持一致，另执行 91 项。54 个完整原文件按原字节编译，共 55 个编译单元、9 个引用；来源审计绑定 331 个冻结输入。见[运行记录](transport-whole-action-sdk-test.json)、[来源审计](transport-whole-action-sdk-audit.json)及[准备进度](transport-whole-action-sdk-progress.json)。

在前一轮 45 个完整原文件基础上，接入完整 S1ActionNodeController、S2ActionNodeController、ProcessDomain、SingleProcessStep、SystemProcess、ProductDomain、ActionNode、ActionNodeInformation 和 ActionNodeMessage。移除三个全局流程/注入夹具声明；实体 Init 的两条 InjectSteps 和捕获的启动方法所用 ProcessDomain.CheckIsReady 现在路由到完整原类。全部 512 段既有源码捕获和上一轮 8 段实体成员原样保持，生产源码未改。

## 已执行的真实源码行为

- 完整步骤和系统模型的默认值、实际 SDK 单例身份；ProductDomain 的原 getter 返回实际产品单例。
- S1/S2 注入先过滤禁用项，再按焊点名称匹配；重复步骤名称只加入一次、初值 false，重新注入保留已完成的 true，新增步骤继续追加。
- 流程实际 Save、清缓存、重载保留禁用标志与完整步骤模型；原 ChangeBpName 修改两系统的匹配记录并实际保存。
- 原 AutoGenerateProcessStep 按异形焊点配置生成点胶/胶检和贴片/焊后检测，保留禁用但有名称的功能记录，分别编号；完整实体仅注入启用项。该方法修改内存，不保存流程文件。
- 两种原启动入口各执行启用有效、禁用有效和禁用无效三种流程。有效计划启动后由完整控制器注入剩余步骤；禁用的有效计划不注入该步骤，禁用但 Index 为 0 的计划仍在任务启动前拦截。
- 两个完整控制器分别执行四种层级策略与两种优先方式，共 16 种排序组合。两基板、每基板两基岛、三个步骤涉及两个焊点；每组合生成 12 个工作消息与 8 个按焊点去重的前置消息。工作顺序与独立显式矩阵比较，功能分派及首次焊点分组也核对原消息模型。
- 原 ActionNode 基础 DoWork 的三个事件路径：正常调用、WorkStart 异常和 WorkStop 异常。开始回调在 try 前，抛错时跳过停止回调且状态保持 Idle；停止回调抛错时状态已为 Stop，异常替代 Success 返回。

动作目录与具名节点仍由受控边界提供，节点实际 DoWork 明确抛出未覆盖异常；排序验证不执行设备动作。原 ActionNode 基础实现的成功路径是纯基础类行为，不能代表派生动作或设备成功。其他域的就绪检查仍受控，完整 System2Domain 与 S2 SelfCheck 的实际启动关联尚未验收。

## 就绪和文件故障证据

原 ProcessDomain.CheckIsReady 遍历完整 S2 列表，未先过滤 IsEnable，禁用且索引无效的步骤仍拒绝启动；InjectSteps 与调度则过滤禁用项。它只比较步骤名称是否为空字符串，null 名称可通过；null ComponentName 与字符串 "Null" 不同，因而计为已选功能。空 S2 流程通过 ProcessDomain 检查，而完整 S2ActionNodeController.SelfCheck 拒绝空计划。上述行为已经运行核对，但尚未修改生产规则或验收完整域/实际窗口的行为。

SDK 写入实现先生成同目录随机临时文件，再通过 File.Replace 替换目标或 File.Move 创建目标。libs DLL 的二进制读取路径有 finally 释放 StreamReader 和 FileStream，未见该路径泄漏证据。本轮增加目标文件禁止删除共享的确定性故障：实际保存抛出原“文件保存失败”异常，旧文件字节保持，随机临时文件被清理，解锁后实际保存和重载恢复。两份 SDK 均执行该四项检查。

此前两次 274 项派生分支运行出现未预设的 File.Replace 保存错误，日志与实际 exit 1 保留在运行记录的 priorObservedSaveFailures。随后独立运行成功；没有冻结那两次失败的精确 DLL，故其原因与发生阶段证据仍有限。确定性文件锁用例证明一种失败机制，并不证明就是此前两次的唯一根因。文件写入可靠性继续待核实，不能据最后一次通过声称现场稳定性验收。

## 复现与后续范围

`node scripts/test-transport-whole-action-sdk.cjs` 对两份 DLL 重新生成、编译及运行，比较 278 项断言数组、20 条预期 JSON 诊断与编译产物哈希。`node scripts/verify-transport-whole-action-sdk.cjs --check` 核对输入、完整文件、既有捕获和冻结日志/产物。

本独立准备未加入冻结的正式 1328 项统一回归；旧 1328 项在此分支只编译，不与 278 项相加认定覆盖。历史 187 项和 142 项准备、正式 197 个输入及核心报告、40 专题/3817 段阅读器快照保持原哈希。整体 16 工程、29 组、1436 个 C# 文件及 13 项要求未完成。

下一步接入完整 DispenseActionNodes、BondActionNodeRepository 和实际动作节点，移除目录边界；展开 System2Domain/SelfCheck 的原启动校验、相对贴片/重做、PR/校准/测量和设备调用。Fody 织入、外部依赖、原工程构建、部署配置/DLL、原生 UI 和设备验收继续待办。文件写入的两次意外失败保留为未定位问题。
