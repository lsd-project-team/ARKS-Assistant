# 其余五类示教测试窗口导航复核

本轮读取五个主类的完整有效代码，并核对对应Designer事件绑定；不执行设备动作，不将注释中的采点/保存作为有效步骤。完整源码、行号与文件哈希见[审计快照](teach-test-navigation-audit.json)。

|窗口|有效页面顺序|Done的有效动作|
|---|---|---|
|ModuleAdjust，3项|选择Module→定位1→定位2|定位1/2均Close；处理器不递增索引|
|SubstrateAdjust，3项|选择Substrate→定位1→定位2|定位1置DialogResult.OK并Close；定位2仅Close；处理器不递增索引|
|ModulePosition，9项|旋转1→旋转2→原点1→原点2→首点→列末点→列数→行末点→行数|原点1Done跳过原点2；原点2Done进入首点；最后输入行数、置OK并Close|
|SubstratePosition，10项|旋转1→旋转2→测高→原点1→原点2→首点→列末点→列数→行末点→行数|原点1Done跳过原点2；原点2Done进入首点；最后解析行数、置OK并Close|
|TUPosition，5项，类名实际拼作FrmTUPoistionTeachTest|旋转1→旋转2→测高→原点1→原点2|原点1仅Close；原点2置OK并Close；处理器随后递增索引|

所有窗口构造均InitializeComponent→InitControl→强制隐藏Back/Done→选择首标签；InitControl设置首项说明，不调用统一SetUiControl。因此首屏不应凭后续刷新逻辑推断全部属性。

ModulePosition和SubstratePosition的原点1Done回调先递增一次索引，外层Done处理器再递增一次，从而跳过第二原点项。外层最后将索引限制在stepCount-1后刷新；最终Close后仍有这些语句。TUPosition外层Done没有此限制和刷新。下一步/返回均先调用当前Action，再改变索引和刷新；没有方法级上下界或异常保护。

## 输入与失败顺序

- ModulePosition列数输入为XtraInputBox.Show的整数重载：先赋columns，再选择行末点；最终行数输入后置OK并Close。取消/异常具体语义仍依赖DevExpress重载，未推断为零或默认值。
- SubstratePosition列数回调先切换到行末点，再int.Parse字符串输入。null、无效数字或溢出若触发解析异常，会阻止外层索引递增和刷新，可能留下已变页签与旧索引；此顺序已由完整原类配合控件替身动态复现；不代表真实DevExpress窗口测试。
- SubstratePosition最终行数先解析，再置OK/Close。输入1、0或负数没有本地范围判断；间距计算和数据保存被注释，不能据此宣称发生除零或写入生产配置。
- ModulePosition额外绑定TileBarTeach.Click和首旋转项ItemClick，但两个处理器为空。其余五窗体各四个导航按钮均有Click绑定，共22处绑定。
- 五窗体的Cancel均仅Close；关闭不等于设备停止，OK不等于完成了实际示教保存。

## 范围与剩余项

项目仍为Library。具名搜索命中这些类的主类和Designer，不证明存在生产入口或排除外部/反射加载。已补五个测试窗口的本地有效步骤，不改变生产示教的验收状态。真实控件生命周期、关闭取消、输入框返回契约、重复点击/越界和完整构建仍待验证。

## SubstratePosition原类隔离验证

[20项测试回执](substrate-navigation-test.json)由`node scripts/test-substrate-navigation.cjs`重建，编译完整未修改的窗口主类及AssistantConfig。仅替换Designer初始化、控件字段、输入框和窗体关闭；使用本机捆绑现代.NET，不是产品.NET Framework或真实UI。

- 非数字、null及Int32溢出分别抛FormatException、ArgumentNullException及OverflowException；列数步骤的页签已切到行末点，但索引保持7、说明未刷新。输入合法数字重试后恢复为索引8。
- 最终行数的三类非法输入均阻止OK和Close；合法重试设置行数、关闭并把索引限制在9。
- 原点1的Done跳过第二原点；原点2的Done正常进入首点。0、-1和1均被本地行列数处理接受，没有范围校验。
- 直接调用首步隐藏Back或末步隐藏Next处理器会分别将索引改为-1/10后抛越界异常。测试刻意绕过可见性，不证明正常用户点击可到达这些路径。Cancel只关闭，不置OK。

null为测试注入，不声称DevExpress取消必然返回null。真实事件派发、取消契约、关闭生命周期、重复点击及生产采点/保存仍待验收。
## 其余四窗口原类隔离验证

[35项测试回执](teach-navigation-windows-test.json)由`node scripts/test-teach-navigation-windows.cjs`生成。四个完整未修改主类与原AssistantConfig共同编译；Designer初始化、控件、整数输入和窗体关闭由最小替身提供，处理器通过反射直接调用。与SubstratePosition的20项检查合计55项，不是55项真实UI验收。

- ModulePosition输入调用在切换页签之前。注入输入异常时，列数、页签、索引6和说明均保持原值；合法重试后索引7。最终输入异常阻止OK及关闭，合法重试后关闭并将索引保持8。0、-1、1均无本地范围拦截。
- ModuleAdjust在两个调整点Done都仅关闭；SubstrateAdjust第一点Done设置OK、第二点Done不设置OK。二者Done处理器均不递增索引。
- TUPosition原点1Done仅关闭、原点2Done设置OK再关闭；处理器在Close返回后仍递增索引，末步变为5，说明不刷新。该结果不证明关闭后的真实控件仍可接受事件。
- 四窗体首步直接调用隐藏Back均先将索引变为-1，再抛越界。正常Next/Back往返及Cancel不置OK已核对。
- 给Close替身注入异常时，四窗体均传播异常并停在原索引；SubstrateAdjust第一点、ModulePosition末步、TUPosition末步已设置OK。这里只证明原方法赋值与调用顺序，不证明真实Close必然抛出此异常。

输入框的整数返回契约、取消返回值、真实事件重入、隐藏按钮可达性以及关闭后的控件生命周期仍须在实际DevExpress环境验证。