# 点胶曲线几何与结构操作复核

日期：2026-09-29。十一份完整未修改原始源码在Windows现代.NET中编译，30项断言通过。旋转和缩放使用实际System.Drawing.Common 10.0.0.0矩阵，不是矩阵替身；仅提供EpoxyPatternControl的两个-1无效索引常量。产品源码、模板及设备配置未修改。

## 已验证行为

|范围|原始行为与验证|
|---|---|
|距离和投影|常规点距、段内及段外距离符合已知样本。零长度线段的海伦公式分母为0，返回NaN；直线投影不夹紧至端点；相同投影端点抛ArgumentException。|
|向量角度|acos结果不含上下方向符号：(1,1)及(1,-1)都为45度，零向量返回NaN。当前模块具名搜索仅发现CalculateVectorInclication定义，不据此宣称真实旋转使用它。|
|矩形边缘|x位于闭区间内时只判断上/下边；精确左边中点(0,5)对矩形(0,0)-(10,10)返回Unkown，略在左侧(-0.5,5)且容差1返回LeftEdge；左上角返回TopEdge而非组合角标志。|
|删点删段|两个端点删一个会清空剩余端点。四点曲线RemoveSegment(1)是空操作；首段删首点、尾段删尾点、仅剩一段删两点。此为直接方法行为，当前模块具名搜索仅发现RemoveSegment定义。|
|平移/旋转/缩放|平移保留点参数，重建Endpoint使实际坐标归零；实际矩阵验证90度旋转、非原点定点缩放及附加点同步；零比例允许曲线塌缩；null附加数组在缩放写回前失败。|
|命中|端点矩形左边界包含、下边界排除；直接ContainsSegment不检查Visible；平移后未刷新实际坐标时形成退化线段而不命中，刷新后恢复。|
|更新和导出|UpdateAllEndpoints回调第二次失败时第一个点已改、后续点未改；导出数组元素替换不回写原曲线。|

## 实际调用链限定

- EpoxyPatternControl.TranslateCurrentCurve、RotateCurrentCurve、ScaleCurrentCurve在原曲线变换成功后均调用UpdateAllCurves再Invalidate（769–817）；UpdateAllCurves用CreateEndpoint刷新每条曲线（1574–1581）。因此不能将直接函数的“实际坐标归零”报告为正常控件路径必然漏刷新。回调失败、事件重入和真实UI仍待验证。
- ScaleCurveHandler.HandleMouseDownEvent调用CheckPointOnRectangleEdge；左右边选择SizeWE，上下边选择SizeNS。鼠标移动使用当前位置/前一次位置的坐标比绝对值计算比例，并调用ScaleCurrentCurve。原点附近除零、缩放中心与比例参照、失败重试等鼠标序列尚未运行验证，不能用本次矩阵检查替代。
- InsertPointHandler使用ContainsSegment，ErasePointHandler在按下/抬起命中同一端点后RemoveEndpoint并发出删除事件。仅定位及读取这些路径，不宣称鼠标状态机已完成验收。

## 证据与剩余范围

[30项回执](curve-geometry-test.json)绑定全部编译源码及测试哈希；[审计](curve-geometry-audit.json)额外绑定控件与鼠标调用文件。执行node scripts/test-curve-geometry.cjs及node scripts/build-curve-geometry-audit.cjs --check。

本次是有限人工样本下的原方法行为复现，不是算法全域正确性或产品验收。大坐标/近共线数值稳定性、非有限矩阵、真实绘制、鼠标动作全过程、原.NET Framework产品构建及设备运行仍未完成。30项通过包括对不理想行为的复现，不表示这些行为已修复。
