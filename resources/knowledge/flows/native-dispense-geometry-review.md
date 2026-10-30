# 原点胶编辑器曲线几何、数据复制与模板文件

两个全新 Framework CLR 宿主各50个不同断言通过，实际调用保真源程序集中的Point2D、Curve、内部Utility、EPEData、BackgroundImageInfo与PatternFile，以及真实GDI矩阵和厂商SXml。没有创建编辑窗口、模拟鼠标、发胶或运动。61原IL方法含7个仅静态控件/处理器方法，15源码哈希、16保真程序集；父6043+新增68=6111冻结绑定。

## 点与几何工具

Point2D.Translate返回新值，原点不变；Point整数转换向零截断（1.75/−2.75→1/−2）。NaN点不等于自身，(1,2)/(2,1)的sum哈希相同但Equals仍不同；哈希碰撞本身没有当作错误。内部Utility不是public类，探针按精确Point2D参数签名把5个原静态方法绑定为delegate，执行原body，没有复写算法或反射写状态。

原3/4距离为5；点到线段的内部垂距和端点距离正确。零长线段通过海伦公式/AB除0返回NaN；直线投影同点参数抛ArgumentException。倾角用acos得到上/下竖直同为90°、零向量NaN，不能据此解释为带符号旋转角。

## 原曲线操作与缓存更新

|原调用|实际结果|
|---|---|
|GetEPEPoints|返回数组/值结构复制，改输出不改原点|
|ModifySegmentInfo(末端点索引)|接受没有出发线段的末点索引，写该点参数|
|RemoveSegment(内部段)|不删除或拆曲线，保持4端点|
|RemoveSegment(首段，后面还有段)|仅删除首端点|
|RemoveEndpoint后只余一个点|同时清空单点|
|Translate/Rotate/Scale|逻辑点更新，重新Endpoint使RealPoint/RealRectangle归零，点参数保留|
|RotateAt(中心1,1，90°)|原GDI把(2,1)/(3,1)→(1,2)/(1,3)，附加点(1,2)→(0,1)|
|Scale(中心1,1，2/3)|前述点→(1,4)/(1,7)，附加点(0,1)→(−1,1)|

Rotate/Scale虽然ref数组，实际修改同一附加数组而非换引用。Scale NaN原验证在写回前抛InvalidOperationException，原曲线/附加点保留；Rotate附加数组null在提交前NRE。原ContainsEndpoint逻辑矩形包含左/上、排除右/下；屏幕点全零后ContainsSegment遇零长段NaN，返回false和−1。

公开CreateEndpoint数值fixture将逻辑点×10映射屏幕并设置矩形，仅给原Curve依赖提供测试坐标，没有替换原控件。调用原UpdateAllEndpoints后屏幕点恢复，线段命中成功；第二个factory调用抛同一测试异常时，首点屏幕值已提交、后点仍零。null factory在迭代前拒绝。

不能据直接Curve缓存归零声称实际编辑器命中已经坏。原Translate/Rotate/ScaleCurrentCurve均先Curve变换，再UpdateAllCurves和Invalidate；UpdateAllCurves把原控件CreateEndpoint交给每条Curve.UpdateAllEndpoints。三种鼠标处理器分别调用这些控件入口。这7个UI方法只读源码/IL，没有实例化控件或实际鼠标验收。

## 数据复制与背景对象

EPEData文档称背景可null，实际构造BackgroundImageInfo拒绝null；0像素比/负宽/0高拒绝，而NaN/Infinity维度通过<=0检查。输入包含null曲线数组则复制阶段NRE。原点数组/Point/EndpointSetting是值复制，包含HeightMeasurement标志；输入矩阵值复制。Bitmap保持原引用，复制BackgroundImageInfo仍共享同一Bitmap而矩阵另存。

MatrixElements getter暴露live数组，外部写立即可见；短数组setter逐项复制，前三项已变后第4次索引失败，留下部分修改。没有把共享图像描述为独立资源所有权，fixture持有并明确释放自己创建的2×2 Bitmap。

## 实际模板保存、读回和失败

原PatternFile.SaveFile通过厂商SXml创建sample.ep和sample.bmp；ReadFile真实复制tmp_Ticks.bmp、Bitmap加载，再SXml/float.Parse读回1.25/−2.5等小数、EndSpeed3、Acc2.5、Dummied、原像素红色及矩阵dx10。模板AddInfo不写HeightMeasurement，RetrieveInfo通过原EndpointSetting构造器重建false；原data标志仍true，读回逐点和DefaultInfo均false。这是原模板往返损失，未扩大为所有工艺参数丢失。

读回产生1张临时BMP；原ClearTmpFiles尝试删除但原Bitmap仍锁文件，catch吞异常，文件实际保留。调用方明确Dispose读入Bitmap后再次调用原ClearTmpFiles，临时文件删除、源sample.bmp保留；不能说模块已自动清理或其他UI入口已释放。

独占锁sample.ep后调用原SaveFile，先把fixture背景从红改蓝并写sample.bmp，再XML写失败。原XML字节保持旧值，BMP实际已经蓝色，证明这两个文件不是事务保存。原顺序IL也显示Image.Save早于SXml.SaveAs；没有向现场文件注入锁或改生产路径。

公开把BackgroundImageInfo.Image=null再SaveFile，可以写出no-background.ep而不写.bmp；原ReadFile却必须先拷贝同名BMP，真实FileNotFoundException被原catch写Console并返回null。两轮各2XML/1BMP，完整文件SHA相同，临时文件最终0；没有用XML/图像类型替身或回退读取器。

## 保留诊断与验证范围

367d4b初次编译因PathConfig命名空间和internal Utility失败，零字节emit未执行；wrapper最后打印诊断exit0不能当编译通过。增加正确namespace并绑定原方法后，初次CLR启动3762504530，stdout空、未建立case-progress，stderr仅报告Exception.ToString失败，295d55记录器随后JSON读取失败。原编译/启动目录和产物保留。

接受版只把原Utility的typed delegate静态字段绑定移到Run内、原加载映射之后，未改SDK/生产程序集；44dd58 50项通过，3f546b独立重编译/replay再50通过。该迁移与前后差异定位了探针加载边界，但失败日志没有具体缺程序集身份，不宣称唯一启动根因已证。两轮emit/固定标签/结果/3文件SHA相同，stdout含不同路径的原失败诊断不声明字节一致。

最终61IL b8c78b；父阅读器/保真资源45975/4bf8c9通过，339411预检/冻结/绑定通过，无独立session。162引用中10直接源引用，runtime-map172项，每轮16源程序集物理bound/replay路径核对。无生产C#/工程/私有写、SDK/动作/算法替身、实际UI/鼠标/轴/相机/点胶/SQL、完整Task/MSBuild/部署。

本轮未验收AKRS.Galaxy2.Dispense全部82源文件。接下来继续编辑器控件/鼠标交互、仿射背景、预览/绘制、管理/资源释放和ZX2200参数往返，以及原生产运动/设备、构建运行依赖。旧主阅读器及独立47专题4997快照不改；整体16工程/29组/1436文件/13项目标未完成。

见[测试](native-dispense-geometry-test.json)、[审计](native-dispense-geometry-audit.json)、[进度](native-dispense-geometry-progress.json)。
