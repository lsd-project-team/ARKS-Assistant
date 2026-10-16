# 点胶模式切换、取消与表格刷新集成复核

2026-09-29。34项检查通过。回执：`mode-lifecycle-test.json`；脚本：`scripts/test-mode-lifecycle.cjs`、`test-mode-lifecycle.ps1`、`mode-lifecycle-harness.cs.txt`。原产品源码未修改。

## 范围与证据强度

36份完整原始源码参与编译，包括真实动作处理器、Curve、事件参数与异常类；另外逐方法原样提取17个控件方法、6个表单方法（合计23个），记录原文件与片段哈希及起止行。源码提取只把这些方法置入替身宿主，没有改写方法体。测试不是完整原控件/表单运行，更不是原生WinForms或产品构建。

Forms、焦点、坐标转换、绘图和大部分宿主服务仍为替身。真实表单ActionChanged回调运行，但标签、按钮、复选框及EnableCurveActions等辅助方法用内存替身；表格Rows/Layout和创建行辅助方法也为替身。对消息投递、原生SelectionChanged时序及真实UI异常恢复不作完成声明。

## 模式切换：双通知、失败与重入

- SetAction先调用OnActionChanging，再写actionEnum、清理高亮、调用新处理器SetMode，最后OnActionChanged。这两个方法都通知同一个ActionChanged事件。观察者第一次看到旧模式，第二次看到新模式，两次参数的Old/New相同。
- 真实表单订阅根据NewActionEnum提前改标签和按钮，并调用SetAttachable；控件却按当前actionEnum分派，所以进入AppendPoint时旧None处理器和新AppendPoint处理器都收到吸附值。结束可编辑模式时EnableCurveActions被调用两次。Designer第815行绑定此订阅。
- 相同模式和未注册模式不初始化、不通知。SetMode异常发生在模式字段写入之后，保留新模式且没有后置通知；再次请求同一模式不会重试初始化，先Reset再进入才会重试。
- 前置通知订阅者抛出可阻止模式字段赋值，但先执行的表单订阅已显示新模式；后置通知异常则保留已经初始化的新处理器。同步订阅者重入SetAction时，外层调用最终仍可覆盖内层刚设置的模式。
- PaintCurve初始化的CurveAdded订阅失败，空曲线和PaintCurve模式均保留；再次请求同一模式不新增曲线，也不重新初始化。

## 取消与曲线清理

- 原OnKeyPress仅在KeyChar为ESC时调用当前处理器退出；原右键菜单退出方法也调用同一退出入口。普通字符不退出AppendPoint，None处理器的ESC无动作。测试直接调用OnKeyPress封装，不证明真实键盘事件一定送达控件。
- Paint退出先清空不足两点的缓存曲线、RemoveCurrentCurve，再将缓存置null并ResetAction。ResetAction触发OnActionChanging，后者看到旧模式是PaintCurve时再次检查当时的当前曲线。
- 当此前保留一条单点曲线，再创建一条不足两点的新绘制曲线时，退出处理器会删掉新曲线，模式切换清理又删掉上一条单点曲线。若上一条有两点，则保留；如果直接SetAction(None)，只执行模式清理，保留上一条单点曲线。两种路径的删除数量不同。本样本证明该对象状态下的链路行为，不证明所有入口都能构造该状态。
- 两点的新绘制曲线退出后保留。

## 删除索引、异常与表格刷新

- RemoveCurve先从集合删除，再通知CurveDeleted，之后才修正当前索引。删除订阅异常会留下旧索引；删除最后一条当前曲线且仍有前一条时，GetCurrentCurve可抛ArgumentOutOfRangeException，再次退出可能抛IndexOutOfRangeException。
- 无订阅者修正时，删除当前索引之前的非当前曲线不会递减当前索引，本例留下越界索引。
- RemoveAllCurves先将当前索引置-1并通知索引事件，再清空集合。索引订阅失败时集合仍在、当前曲线不可用；集合清空后，任一删除通知失败又可能使后续删除通知未执行。
- 进一步运行真实CurveDeleted/CurrentCurveIndexChanged表单回调与三种Refresh方法：在不产生SelectionChanged的表格替身中，集合刷新完成后段表刷新读取旧索引而抛出，且段表SuspendLayout没有对应ResumeLayout。
- 加入受控的Rows.Add回调，在刷新中调用真实SetCurrentCurveIndex(0)，同一删除序列成功，布局计数平衡。这是展示事件先后顺序如何改变结果的实验，不是原生DataGridView行为模拟。真实SelectionChanged回调会读取SelectedRows、SetCurrentCurveIndex并ExecuteAction(None)，其完整同步重入时序仍需原生UI验收。
- 删除最后一条曲线时，真实表单回调禁用动作和集合按钮，并清空端点区域。表格Designer的SelectionChanged在第217行绑定，CurveDeleted/CurrentCurveIndexChanged在第813/814行绑定。

## 未完成与下一步

需继续核对ExecuteAction与实际表格选择重入、参数编辑往返、背景动作和完整取消恢复；当前测试对其他全部处理器及82个Dispense源文件不构成穷尽覆盖。完整产品构建、SDK、真实UI和设备验收未完成，29组模块继续部分复核。
