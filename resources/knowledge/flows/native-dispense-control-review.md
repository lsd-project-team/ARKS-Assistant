# 原点胶图形控件方法与事件提交边界

两个全新 Framework CLR STA 进程各35个不同检查通过，实际构造原 DevExpress EpoxyPatternControl，调用原图形、变换、尺寸、比例、动作及事件方法。43个原IL方法、11份源码哈希、每轮16个保真源程序集；父6111+新增52=6163冻结绑定。没有显示窗口，原控件 IsHandleCreated=false；未启动消息循环、操作真实或模拟鼠标、执行 OnPaint 或截图绘制。

## 原控件与真实屏幕缓存

首轮探针在2项通过后错误假定设计器写506×506就代表构造时运行尺寸。当前环境实际构造590×590、原点295/295、scale1、当前索引−1；AutoScaleMode.Font和设计器尺寸源记录保留，但没有单独证明590的唯一缩放原因。失败root primary、原Cases/Host/compile/EXE均保留，native exit1，属于探针预期错误，没有当作产品故障。

接受版先核对原scale1/索引−1/空列表，再明确通过公开Size先508后506，原OnSizeChanged回调把原点设253/253。SetFigure把两条曲线替换入原列表，当前索引0，直接使用原CreateEndpoint；逻辑(2,1)得到屏幕(255,252)、10×10端点框。输入、GetFigure输出点数据是值复制，改变输出不改原曲线。SetFigure不触发添加、删除或当前索引事件；空曲线和单点可保留在CurveList，GetFigure仅导出至少2点曲线，因此列表3条可能导出1条且当前曲线空。null SetFigure读data.Count即NRE，原列表引用和索引保留。

原公共变换验证弥补上一轮只有静态控件调用证据的限制：TranslateCurrentCurve原曲线变换后立即UpdateAllCurves，当前和其他曲线屏幕缓存都重建。RotateCurrentCurve/ScaleCurrentCurve真实调用原GDI矩阵，再同样重建端点，附加点原数组也变换。此处没有测试实际鼠标拖动或可视绘制。

显示scale低于1、NaN被忽略，无事件；scale2更新原屏幕坐标。ConvertToPixelPoint/ConvertToLogicalPoint以原点、scale及Y反向做往返；原命名ConvertToPixelSize实际除scale，ConvertToLogicalSize实际乘scale，按原结果记录，没有改写算法。公开Size200×100→原点100/50、端点重建；Size10×10使背景Bitmap被丢弃，但保留100/50原点，端点仍按旧原点重建。

## 列表、索引与回调异常

|原操作|原进程观察|
|---|---|
|SetCurrentCurveIndex切换|先提交索引、再事件；同索引返回false、不重复事件；无效索引抛ArgumentOutOfRange|
|索引事件抛同一fixture异常|索引已变，原方法未回滚|
|当前索引2，删除非当前索引0|3曲线变2，当前仍2，GetCurrentCurve实际ArgumentOutOfRange|
|删除当前曲线，CurveDeleted事件抛错|曲线已移除，事件读到旧当前索引，后续索引修正未执行，当前越界|
|当前删除事件成功|再选前一条并触发索引事件|
|RemoveAllCurves的索引事件抛错|当前先置−1、曲线列表仍2条|
|RemoveAllCurves的删除事件抛错|整个列表已Clear，当前−1，只是后续通知未完成|
|ScaleChanged事件抛错|scale3和全部端点缓存已提交，异常同一实例向上传播|

异常仅由公开事件订阅注入，用来暴露原执行顺序；内部current/remove/conversion接口以9个封闭原方法delegate调用，绑定真实控件receiver，没有反射写私有字段、重写控件或替换处理器。上述故障不是实际用户操作路径已经发生的断言；实际界面管理调用方是否规避这些边界仍需后续验证。

## 原动作与绘制模式初始化

原SetAction(PaintCurve)先通过OnActionChanging触发ActionChanged（回调观察旧None），提交action后调用原PaintCurveHandler.SetMode。原handler经AddCurve添加空曲线、设置current0、触发CurveAdded，最后OnActionChanged再次触发同一ActionChanged（观察新PaintCurve）。共2次，说明名称相同事件分别覆盖前后两段。

未在handlerDict注册的PaintPoint枚举被静默忽略，不触发事件或清理旧动作。切回None前，原OnActionChanging删除端点不足2的当前绘制曲线，成功后动作None/current−1。前段ActionChanged抛错→动作None且没有新增曲线；后段第二次抛错→动作PaintCurve且空曲线已存在。CurveAdded事件在原SetMode抛错→动作PaintCurve、曲线和current0已提交，后段ActionChanged尚未执行。没有把这些public事件异常理解为生产鼠标输入或画线完成。

## 验证和限制

失败b9cd97保留；接受版编译及primary-v2为31cb71，35项；独立重编译replay为79eddf，再35项。两轮Probe SHA、固定标签、结果及构造诊断相同，源程序集物理bound/replay路径分别核对。43原IL 9fdcd7核对RemoveAt→删除事件→索引事件，clear索引事件→Clear→删除事件，SetAction前事件→SetMode→后事件及曲线变换→缓存更新顺序。162编译引用含10直接源引用、runtime-map172项。

父几何/保真资源验证82847/f74456通过，ee1096预检/冻结/绑定通过，无独立session。调用原Dispose并观察控件完成释放，不据此声称所有GDI/handler资源均已正确释放；Designer.Dispose仅原源码/IL证据，资源所有权另待核验。

无生产C#/工程/私有写、SDK/算法替身、硬件/轴/相机/点胶/SQL、原完整生产Task、全MSBuild或部署。原控件已经实际构造和执行方法，仍未验收可视编辑、鼠标/键盘、背景仿射/绘制、预览、管理参数桥和AKRS.Galaxy2.Dispense全部82源文件。旧主阅读器及独立47专题4997快照保持；16工程/29组/1436文件/13项目标整体未完成。

见[测试](native-dispense-control-test.json)、[审计](native-dispense-control-audit.json)、[进度](native-dispense-control-progress.json)。
