# 点胶追加、移动与绘制动作复核

日期：2026-09-29。AppendPointHandler、MovePointHandler、PaintCurveHandler完整原类及依赖共29份原文件编译，24项隔离序列通过。[回执](draw-edit-test.json)列出全部源码和测试哈希。原产品源码不变。

## 追加端点

- SetMode调用基类，重置吸附并Focus，再缓存当前曲线末点；空曲线会在读取索引-1时失败。
- 左键直接追加默认参数点，再发布EndpointAppended，最后Invalidate；事件异常发生时数据已写入，但最后重绘未执行。右键处理器无动作。
- 吸附后事件携带已吸附坐标，与插点/绘制分支不同。只跳过命中当前末点的吸附，不拒绝精确重复点。多个端点容差重叠时ContainsEndpoint返回最早匹配，追加后再次同位置点击可能吸到较早端点。
- HandleScaleChanged只重建鼠标端点，没有重建缓存_tailEndpoint。测试中曲线末点实际坐标由20改为200后，处理器缓存仍为20；绘制预览使用该缓存。控件OnScaleChanged先UpdateAllCurves，再调用该处理器，因此曲线端点已刷新不代表缓存同步。未做真实像素截图验收。

## 移动端点

- SetMode不调用基类，已有吸附设置保留。按下命中后保持；后续移动不检查按键，可实时修改坐标并保留点参数。启用吸附时也可能命中正在移动的自身端点。
- 右键按下/抬起均不会结束移动，尽管文件顶部注释写着右击结束；左键抬起只释放，不提交抬起事件的坐标。是否有宿主右键菜单另行切换模式不能由此测试排除。
- 移动事件异常发生在坐标已经更新之后，保持标志保留，后续Invalidate未执行。HandleExitActionRequest调用ResetAction并清除缓存曲线引用，但不恢复坐标，也不直接清保持标志；后续SetMode会清标志。真实ResetAction有模式切换与事件，本替身仅记调用，故不宣称旧保持标志会持续影响正常界面。

## 绘制曲线

- SetMode立即AddCurve并赋本地曲线，再发布CurveAdded。订阅异常会留下已加入的空曲线与本地引用；真实AddCurve也直接添加列表并设当前索引。
- 退出时少于两点就先Clear，再RemoveCurrentCurve；两点即保留，包括两个完全相同的点。注入RemoveCurrentCurve失败时，Clear已经执行，后续ResetAction和Invalidate未执行。注入点代表调用边界，不等同于原控件内部具体失败位置。
- 绘制点击先追加、更新缓存与计数、Invalidate，再发布EndpointAppended；因此其事件异常时已请求重绘，与追加处理器不同。
- 吸附后端点可为(0,0)，但绘制发布的追加事件仍携带原点击(1,1)。原表单追加订阅读当前曲线并新增段表行，不直接用事件坐标更新端点，不能据此宣称产品数据损坏。

## 宿主证据及未完成项

EpoxyPatternControl.SetAction先OnActionChanging，再写actionEnum、清高亮、SetMode、OnActionChanged，SetMode异常后不会自动回滚动作枚举。ResetAction转入None；这些真实事件链仅静态核对，未由本测试宿主完整执行。

原表单Designer第806/809/812行绑定追加、改变和曲线新增；追加订阅使用固定EndpointSetting(10,10,100,0,0,false,0,0)建立新段表行，未在此读取真实段参数。表格后续是否回写这些默认值仍需跟踪，不把显示默认值直接认定为模型参数覆盖。

命令：node scripts/test-draw-edit.cjs；node scripts/build-draw-edit-audit.cjs --check。宿主使用恒等坐标转换、记录式事件和简化曲线列表，未执行真实Forms分派/捕获、完整表单、设备或原Framework构建。已有29份编译源并不代表29个文件所有分支已验收。

剩余：旋转/平移及选择处理器、模式切换与键盘取消链、表单事件重入/表格参数往返、真实缩放预览、数值全域稳定性及产品设备验收。
