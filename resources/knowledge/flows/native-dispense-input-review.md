# 原点胶输入分派、七类处理器与事件边界

两轮全新Framework CLR STA进程各44个不同检查通过，实际构造原控件并经11个封闭原方法delegate调用protected输入方法及只读索引/当前查询。真实原Paint、Append、Move、Select、Erase、Insert、Translate七类处理器执行，另有None空handler分派；84个原IL方法含3个仅静态Form方法，22源码哈希、16保真源程序集。父6326+新增54=6380冻结绑定。

本轮使用构造的MouseEventArgs、KeyEventArgs和KeyPressEventArgs直接调用原方法，所以合成事件对象确实执行。没有SendInput、SendKeys、系统鼠标键盘输入、显示窗口或消息循环；两轮控件Handle仍false。它验证原方法语义和事件分派，不等同真实用户拖动/键盘事件送达验收。

## 原分派和回调顺序

None模式下，提供像素110/70得到逻辑10/10和MousePointChanged。公开MouseMove事件在base方法中先触发；该事件抛同一fixture异常时，原handler和后段MousePointChanged都不执行。

MovePoint持有点时，原顺序实测base MouseMove事件→原ModifyEndpoint→EndpointChanged事件→原控件MousePointChanged。EndpointChanged抛错时新逻辑点/真实屏幕点已提交，最后MousePointChanged跳过；handler仍持有，下一次None按钮的move可继续移动。左键up释放持有后，下一次move只悬停、不改点。原MovePoint保留已有EndSpeed等点设置；原工厂重建真实坐标。

## 新点、吸附与事件坐标

|原操作|提供的坐标 / 原端点 / 原事件|
|---|---|
|PaintCurve左down|像素80/70→逻辑−20/10，屏幕点仍80/70；原DefaultInfo MaxSpeed77、HeightMeasurement及Dummied复制|
|PaintCurve右down|忽略，不新增点或事件|
|PaintCurve吸附第一点|提供像素81/70即逻辑−19/10，原点吸附到−20/10；EndpointAppended事件仍报告−19/10|
|AppendPoint靠近tail|提供119/80即19/0，不吸附尾点20/0，而新建19/0|
|AppendPoint吸附更早端点|提供81/80即−19/0，存−20/0，事件报告实际提交的−20/0|
|InsertPoint第一左down|命中原线段，只选择，不插入|
|InsertPoint第二左down|提供100/70即0/10，原线段在y0也允许离线段插入到0/10|
|InsertPoint第二down吸附首点|提供81/80即−19/0，原点存−20/0；EndpointInserted事件仍报告−19/0，原默认HeightMeasurement保留|

吸附通过原public SetAttachable控制；探针根据实际Control.ModifierKeys当前读取选择公开Attachable值，不替换系统修饰键。两轮起止读值都是None，未发送Shift/Ctrl等按键，没有验证所有物理修饰键组合。原Shift比较是精确Keys.Shift，代码/IL保留，不扩展成已执行Shift+Ctrl矩阵。

Append事件抛同一fixture异常，点及handler tail已提交，下一次down继续追加。Insert事件抛错也保留新点，但选中段在回调之前已复位；下一次段外down不会偷偷再插入。Insert右down取消已选段，之后段外down不提交。

## 命中、删除和状态残留

SelectObject原ContainsEndpoint使用EndpointRectWidth/2=5作为逻辑偏移，没有除scale。在scale4、端点真实矩形右边105时，像素116（逻辑4）仍命中、highlight0/Hand；像素125（逻辑6.25）才清highlight。证明本路径逻辑命中区随显示比例扩大，不是实际10像素矩形命中；没有声称所有选择/线段路径共用这个度量。

Erase要求down/up命中同一端点索引；down首点/up中点不删除。正常删除从3→2，再删除使原Curve只剩1点便全清，但控件CurveList仍1条空曲线、GetFigure导出0条。随后AppendPoint的SetMode GetEndpoint(−1)实际ArgumentOutOfRangeException，动作枚举已提交AppendPoint，说明空曲线残留和动作提交之间的直接边界。

另一个公开EndpointDeleted异常fixture：曲线0/1/2三点、在像素100/80 down/up删除首点后回调抛错，候选索引尚未复位。再次只提供同坐标up，没有新down，附近剩余点被命中为同索引0，又删除并将孤点全清，回调再次抛同一异常。两次删除是真实原处理器结果，说明reset位于事件之后；异常为测试订阅抛出，未声称实际现场回调已发生该问题。

## 平移、滚轮和Escape

原TranslateCurve.HandleMouseDownEvent没有读取Button。在曲线包围盒内提供Right down仍开始持有，之后None按钮move经原TranslateCurrentCurve改变逻辑点，并原UpdateAllCurves重建屏幕端点；任意Right up也结束持有。当前物理修饰键None，位移10/10；Shift/Ctrl限制路径只保留静态IL，不声明全组合执行。

KeyDown/KeyUp Escape不退出PaintCurve，普通KeyPress x也不退出；KeyPress的字符0x1B才分派原HandleExitActionRequest。两点完整曲线保留、一点未完成曲线删除且动作None。这个区别是直接原方法语义，不代表操作系统必须向控件生成Escape KeyPress。

原OnMouseWheel delta0走非负分支，scale1→1.1；负delta−600只缩小0.1，与幅度无关。原Zoom(100)先检查旧scale<16，因此1→101；随后正Zoom忽略，Zoom(−100.5)申请0.5被SetScale最低1规则忽略，仍101。已经通过公开SetScale恢复，未向用户真实编辑器发送滚轮。

## 参数桥的静态线索与下一步

3个原EpoxyPatternForm.SetContent/GetContent body仅源码/IL读取，未构造Form或执行参数往返。本轮静态核对SetContent在读取incoming MicronPerPixel并赋字段前，先以this.dieWidth/this.micronPerPixel和旧dieHeight计算SetDieSize；GetContent调用EPEData构造器但没有调用SetDefaultValues。必须下一轮以原Form及真实参数实际核验，不能仅凭此处静态顺序当作参数损失已经复现。

## 证据与范围

1cd5c0首次编译/primary 44项通过，348250独立重编译/replay再44项，没有失败候选；两轮Probe SHA、标签、结果及诊断一致，物理bound/replay源程序集路径分别核对。84IL d4f042；父原绘制/保真资源50599/ed86ac通过，6b829f预检/冻结/绑定通过，无独立session。162编译引用含10直接源码引用，runtime-map172项。原Dispose后探针仅只读收集并明确释放本轮观测的控件/handler GDI对象，生命周期证据见父原绘制报告；无私有写或替换handler/控制器。

无生产C#/工程/SDK修改、真实鼠标键盘输入/显示窗口/消息循环、实际设备/轴/相机/点胶/SQL、原完整生产Task/MSBuild/部署。原Form参数桥、管理器/ZX2200接入和全部82文件仍待验收。旧主阅读器及47专题4997独立源码视图保持；16工程/29组/1436文件/13项目标整体未完成。

见[测试](native-dispense-input-test.json)、[审计](native-dispense-input-audit.json)、[进度](native-dispense-input-progress.json)。
