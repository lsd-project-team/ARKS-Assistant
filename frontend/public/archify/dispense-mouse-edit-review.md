# 点胶插点、删点及缩放鼠标序列

日期：2026-09-29。22份未修改原始源码，包括InsertPointHandler、ErasePointHandler、ScaleCurveHandler及完整基类、Curve和事件参数；27项隔离断言通过。System.Drawing矩阵使用真实实现，Forms事件、控制器及坐标转换为替身，像素/逻辑坐标设置为恒等。不是原产品UI自动化验收。

## 插点

1. 第一次左键按下选择线段，MouseUp为空；第二次左键按下才插入。第二次坐标无需在线段上，使用DefaultEndPointInfo。
2. 吸附时实际新端点可复制已有端点，但EndpointInsertedEventArgs携带未吸附的mouseLogicalPoint。本次(1,1)点击吸附到(0,0)，事件仍为(1,1)。原表单订阅只刷新段表格，没有使用该事件坐标直接回写；不能由载荷差异断言界面数据损坏。
3. InsertPointHandler.SetMode未调用基类，已有Attachable不被重置；Shift单独按下反转吸附，但Shift+Control不等于Keys.Shift。右键取消选段不插点。
4. 处理器缓存SetMode时的Curve；替身切换当前曲线但不重设模式后，处理器仍修改旧曲线。真实模式切换是否阻断该序列仍需验证。
5. 插入回调抛错前，点已加入、选段索引已清空、光标已复原；回调之后的Invalidate不执行。原事件发布器无局部catch，异常源在本实验中人工注入。

## 删点

- 按下命中端点设置候选；抬起未命中或命中另一端点，不清候选。下一次在空白按下再在旧端点抬起，仍可删除旧候选。
- 删除事件回调发生于RemoveEndpoint之后、候选清空和Invalidate之前；回调失败留下已经删除的数据与旧索引。直接再次抬起可删到移位后的端点。两点曲线再删一点会清空曲线。
- ErasePointHandler.SetMode调用基类，会Focus并重置Attachable，与插点不同。
- 原表单epoxyPatternControl_PointErased先刷新表格，再在当前曲线为空时执行BtDeletePoint.PerformClick及RemoveAllCurves。这些表单副作用不在替身中，故不能把隔离重复抬起结果等同于实际窗口全过程；其事件重入、模式切换及全部曲线删除范围需继续验证。

## 缩放

- 精确左边框中部返回Unkown而不启动；略在左侧容差内可启动。HandleMouseDownEvent不检查按钮，右键也可进入保持状态；保持时不要求MouseMove携带按键，右键抬起也结束。
- 因子取当前位置坐标/前次坐标的绝对值，实际Curve.Scale围绕曲线中心应用。曲线(10,10)-(20,20)的上边拖动y=8→16给2倍；整体平移100后相同拖动108→116给116/108倍，因子随坐标原点变化。
- Shift单独按下启用双轴同比例，Shift+Control不会触发该分支。前次坐标为0时原处理器会把正无穷因子传入控件；该断言在控件边界注入InvalidOperationException，不宣称实际矩阵接收无穷后的结果。
- 前次鼠标位置在调用控件前已更新。InvalidOperationException被捕获并停止保持；ArgumentException等其他异常逸出，保持状态保留。失败8→16后重试到24使用24/16而非24/8。
- 保持状态下当前曲线消失，抬起时RefreshCurveBounds抛错，后面的保持标志清空不执行；真实界面可达性仍未证实。

## 分派与验证边界

EpoxyPatternControl.OnMouseDown/Up/Move先调用base，再按actionEnum取处理器直接分派，所读三段没有按钮过滤或局部catch。MouseMove处理器异常也会阻止后续OnMousePointChanged。原表单Designer第807/808行绑定插入、删除订阅；源码绑定见审计。

执行node scripts/test-mouse-edit.cjs；[27项回执](mouse-edit-test.json)绑定源码和测试哈希，[审计](mouse-edit-audit.json)绑定真实控件、表单及Designer。所有通过均指行为复现，没有修改产品算法。

未完成：真实坐标比例/DPI、鼠标捕获与键盘分派、表单事件重入与清空副作用、模式切换和取消恢复、其余追加/移动/绘制/旋转/平移处理器、完整产品构建及设备验收。
