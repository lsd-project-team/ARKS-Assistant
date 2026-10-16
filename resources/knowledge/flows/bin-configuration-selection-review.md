# 料仓名称选择、参数加载与提交

2026-09-28。限定源码复核，补齐[层位参数来源](bin-layer-motion-persistence-review.md)所列Find/加载边界。尚未执行UI、文件异常或设备测试。

## 确认的执行顺序

1. 上下料设置控件Init调用RefreshCmb：清列表，仓库Filter(空字符串,false)，取Name填下拉框，再从TransportProgram当前名称回填EditValue。Designer禁用自由文本编辑并绑定SelectedIndexChanged。初始化回填是否触发第三方控件事件、触发几次，本轮未运行验证。
2. 名称选择事件直接Confirm：控件Text赋给CurLoaderName/CurUnLoaderName，然后TransportProgram.Save。该方法没有非空、存在性、配方归属或机器Working检查，也没有局部失败回滚。不能由此断言整个界面未作上层禁用；父界面门控待核实。
3. 程序模型LoaderBin/UnloaderBin getter按当前名称调用仓库GetLoaderBin，后者调用基类Find。Find是列表Find(bi.Name==name)，不检查IsEnable和RecipeIDList，不做Trim/别名规范化，不自动补建；无匹配返回null。同名时取首个匹配，不证明数据文件一定无重复。
4. 库单例首次构造调用基类Load：ReadGenericList(GetFileName())返回null才替换为新空List。此处没有catch，不能把损坏JSON或I/O异常自动等同于返回空列表。Save只调用SaveGenericList；写盘原子性、备份、异常传播取决于外部helper。
5. LoaderBinRepository.json和UnLoaderBinRepository.json位于DeviceDirPath；TransportSystemProgram.json位于当前配方目录。库参数与配方中名称引用是两类文件，所读代码没有跨两文件事务。

## 界面过滤不等于生产校验

Filter(空字符串,false)仅保留IsEnable=true，并不按RecipeIDList过滤。基类虽另有GetDataSourceByCurrentRecipe，但这两个下拉框并未调用它。生产getter又直接Find，因此“可见候选”“已保存名称”“生产取到对象”是三个不同环节；禁用或删除库对象后是否修复已保存名称，应单独验证。

## 库编辑与关闭行为

- 新建窗口校验空白、已有同名和文件名非法字符；选中参考对象时DeepGenericCopy，否则new T；赋Name/CreateTime、AddBelongRecipeIds、Add到内存列表。基类Add仅List.Add，本身不去重/保存，不能将UI校验当成所有写入入口的全局约束。
- 删除先确认，拒绝IsSystemConfiguration项，再Remove并可调用actionDelete；两个料仓控件构造FrmRepository时只传仓库，未传删除回调。所读路径没有显式修复CurLoaderName/CurUnLoaderName，但RefreshCmb触发的UI事件影响需验证。
- 保存按钮调用仓库Save后显示成功。FormClosed事件已绑定，执行CloseEditor/UpdateCurrentRow后Save；普通关闭不是回滚或放弃所有修改。helper可能的静默失败无法仅凭成功提示排除。
- 调用方仅在ShowDialog返回OK时把DsSetting.Name赋给下拉框Text。仓库双击行设置DsSetting并调用可选action，但设置DialogResult.OK的语句被注释；Extract也设置DsSetting、调用action并提示。不能把“双击必然返回OK并选中”画成确定路径；所有其他关闭入口仍待验收。

## 输入、输出与故障边界

输入：库JSON、当前配方名称引用、启用标志、用户选择/编辑。输出：内存库对象、当前名称及各自Save调用。生产未找到对象可能在后续层位参数解引用时抛错，需沿具体调用链判定；不能断言全部生产入口已经集中阻止此情况。

后续已补：[父界面运行/暂停编辑门控及两种启动入口差异](production-edit-gating-review.md)。这不等于运行并发安全验收。未完成：其他库导入/重命名入口；helper和Singleton真实保存契约；损坏文件/重复名称/删除当前对象/关闭窗口的隔离验证。

## 精确源码证据

- [trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs:45](../../trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs#L45)
- [trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcLoderSetting.cs:33](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcLoderSetting.cs#L33)
- [trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcUnloaderSetting.cs:34](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcUnloaderSetting.cs#L34)
- [trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcLoderSetting.Designer.cs:64](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcLoderSetting.Designer.cs#L64)
- [trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcUnloaderSetting.Designer.cs:64](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcUnloaderSetting.Designer.cs#L64)
- [trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs:113](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs#L113)
- [trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs:178](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs#L178)
- [trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs:294](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs#L294)
- [trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.Designer.cs:307](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.Designer.cs#L307)
- [trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs:253](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs#L253)
- [trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs:61](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs#L61)
- [trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs:56](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L56)
