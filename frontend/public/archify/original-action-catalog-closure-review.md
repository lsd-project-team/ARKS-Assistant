# 原动作目录与节点依赖闭包候选

本轮在 `.archify-work/whole-action-catalog-candidate/` 建立隔离候选：移除上一轮的两个受控目录声明，接入原始 `DispenseActionNodes.cs` 与 `BondActionNodeRepository.cs`，并加入 51 个实际动作节点/分部/公共动作源文件；原生产源文件仅作只读输入。两个目录构造函数均按原始 `List<string> processStepNames` 签名接入。

原始目录文件分别为 9556 和 12044 字节，动作属性和 `Init()` 注册顺序按源文件哈希冻结；目录中实例化的 37 个本地类型全部在仓库动作源文件中找到。候选编译输入共 108 个源、9 个引用，保留原 whole-action 的流程、配置、实体和控制器输入。

隔离 Roslyn 编译未通过：1585 个错误、28 个警告，主要缺口集中于 LogicHardware、VM、DevExpress、Wafer/Bond/Dispense 服务以及配置成员。该结果说明实际动作节点不能只靠当前 54/55 个流程模型源闭包直接发射；失败日志、输入和候选 Probe 均保留，未生成可运行 DLL，也未修改原工程。

下一步只扩展缺失的仓库依赖闭包，先让两个真实目录完成构造与 `Init()` 顺序核验，再进入完整 System2Domain/SelfCheck、相对贴片/重做、PR/相机/校准/测量及硬件边界。正式 1328 回归仍独立，整体目标未完成。
