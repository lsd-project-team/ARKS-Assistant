# 原点胶背景绘制、预览文件与GDI释放边界

两轮全新Framework CLR STA进程各42个不同检查通过，实际调用原DevExpress EpoxyPatternControl.OnPaint、原背景/Curve/Utility绘制以及原SaveSnapshoot。每轮生成14个真实PNG，逐文件完整SHA相同；45个原IL方法、6类型元数据、12份源码哈希、16个保真源程序集。父6163+新增163=6326冻结绑定，包含全部失败候选和图像。

本轮已执行原绘制，不再是上一轮只构造控件/方法验证；绘制目标是探针自己创建的Bitmap与Graphics，没有显示窗口、创建控件Handle、启动消息循环或操作真实/模拟鼠标。4个封闭原控件delegate调用OnPaint、PaintBackgroundImageAndCurves、选择、删除；GDI资源只读字段观察，没有写私有状态。

## 背景变换与缓存

公开Size200×160使原点100/80。调用方创建72×48纯绿色Bitmap，原背景setter保持同一Bitmap引用而复制矩阵。getter给新的BackgroundImageInfo和数组，修改其Image/null或矩阵不会直接改控件；图像引用仍共享。

原InitBackgroundBitmap先清白，再按scale放大图像、平移到背景中心，最后Append乘backgroundImageMatrix；绘制绿色背景后再画灰网格、黑坐标轴、可选红die矩形。实际原OnPaint输出验证居中、平移、90°旋转及scale2的颜色位置；仿射矩阵RotateAt是在屏幕原点执行，平移20/10后旋转90°得到[0,1,−1,0,170,0]。scale2下Translate20/10仍是20/10像素，不再乘scale。

实际旋转输出：

![原OnPaint旋转背景](/C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-dispense-rendering/primary-v5/render-fixture/rotated.png)

公开把BackgroundImageInfo设为默认空图像，图像状态变null，但setter仅在Image非null时重建，旧缓存的绿色仍被原OnPaint绘出。公开Resize先202×162再200×160后才清掉绿色。本轮证明缓存与公开状态可暂时不一致；没有断言实际管理界面一定采用这个清空路径。

背景Matrix替换前只读保存旧对象；setter新建Matrix后，旧Matrix.Elements仍可读，说明该替换没有主动Dispose它。探针随后明确Dispose旧Matrix。反之，公开尺寸变化的原RebuildBackgroundBitmap确实Dispose旧背景Bitmap：旧GetPixel实际ArgumentException、字段换为新对象。不能把所有GDI对象归为同一所有权行为。

## 原曲线、绘制事件和故障

两条原SetFigure曲线的屏幕坐标来自原工厂。OnPaint先画其他蓝曲线，再画当前红曲线及原高亮/端点形状；选择切换后红蓝角色交换。Visible=false的曲线跳过端点和线/箭头绘制。原Curve通过Utility.DrawVector/DrawArrow画线和箭头，当前高亮路径经FillVector/FillArrow；这些原辅助body包含在45方法中，未声称所有重载/分支都执行。

![原OnPaint当前和其他曲线](/C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-dispense-rendering/primary-v5/render-fixture/curves.png)

公开Paint事件的fixture在角落填Lime，正常回调后原缓存背景把它覆盖为白；说明base公开事件位于原缓存绘制之前。fixture事件抛同一个InvalidOperationException时，Lime像素保留、后续缓存绘制未执行。vendor base已经把其他区域画成240/240/240灰，不能说事件抛错前Graphics完全没动；这正是第二次失败探针纠正的预期。

原设置Graphics.SmoothingMode.HighQuality，GDI getter实际读AntiAlias；PixelOffsetMode getter仍HighQuality，调用方Translate1/2被保留。直接原PaintBackgroundImageAndCurves也核对了相同行为，它在Graphics.Save之前设置高质量选项，所以Restore后这些选项仍存在。此处记录实际native getter，没有根据枚举名字臆测Half或原HighQuality getter。

上一轮原删除较早非当前曲线造成stale current index，本轮进一步进入原OnPaint：背景和其他曲线已画蓝后，访问当前越界，实际ArgumentOutOfRangeException，输出有蓝无红，证明部分绘制。原小尺寸10×10会丢弃背景Bitmap；再调用原OnPaint的DrawImage(null)抛ArgumentNullException。没有将直接原绘制方法调用当作OS消息循环已触发实际用户故障。

## 实际原预览保存

|原SaveSnapshoot路径|原文件/异常结果|
|---|---|
|die40×24、scale1|真实40×24 PNG中心裁剪，红die边界可见|
|相同die、scale2|文件仍40×24，红边界已随显示scale放到裁剪外，没有按scale扩大文件|
|die20.9×12.9|真实输出20×12，原int转换截断小数|
|null文件路径|Bitmap分配前ArgumentNullException|
|独占锁已有PNG再写|实际写失败，原文件完整字节保持|
|die0×0|Bitmap构造ArgumentException，未生成zero.png|
|正die、小控件背景null|读取backgroundBitmap.Width发生NRE，未生成small.png|

SaveSnapshoot使用原PaintBackgroundImageAndCurves中心平移裁剪，没有走公开Paint事件或handler绘制。原DieSizeChanged回调抛同一fixture异常时，die40×24及背景重建已经提交。输入已Dispose的Bitmap时，原setter先提交共享Image引用和新Matrix dx7/dy9，再重建读取Image.Size失败；公开状态保留已提交引用和矩阵，随后用有效fixture恢复。

独占保存失败已实际执行，但没有持有方法内新Bitmap引用，因此不声称测到了它的实际泄漏。原IL显示Image.Save后才有Bitmap.Dispose，只有Graphics using的Finally；Save抛错会越过尾部Dispose，这是静态释放路径证据。背景绘制的临时Matrix没有显式Dispose调用也仅是IL证据，未量化长期handle增长。

## 原Dispose与所有权观察

原控件Dispose后IsDisposed=true，Designer components中的ContextMenuStrip.IsDisposed=true，无控件Handle创建。只读保存的内部背景Bitmap仍能GetPixel，Matrix仍能Elements；内部gridLinePen、current painting tool的Pen/Brush/DummiedPen仍实际可画。原Designer.Dispose只释放components并调用base，没有处理这些字段；PaintingToolSet类型元数据没有Dispose或IDisposable。旧Matrix替换和最终Dispose均没有主动销毁本轮持有的对应对象。

共享caller source Bitmap也仍可读取，这与调用方提供/持有图像的边界不同，不能单凭它仍可用判定控件应拥有或泄漏源图像。本轮证明选定内部对象没有在原Dispose时主动释放；持有引用本身延长可达性，未测GC终结、进程长期内存或GDI handle增长，也不代表所有资源所有权已验收。探针在观察后逐个Dispose只读收集的选定控件及handler GDI对象，随后内部Bitmap/Matrix访问失败，caller image由调用方using释放；没有通过生产私有字段修补代码。

## 保留的失败与验收范围

ac02b0编译失败是探针Action lambda直接写Matrix.Elements属性表达式，零字节emit未执行；改为局部读取。4次原生断言失败均保留原输入/compile/EXE/root/png：2b98e3在16项后要求纯蓝像素，实际抗锯齿混色；d43ef8在20项后误认为base绘制前后未触碰区域仍Magenta，实际240灰；8cbeb0在21项后误期望Smoothing getter HighQuality，实际AntiAlias；113559在21项后把PixelOffset误写Half，尽管已观察HighQuality，已纠正。红/蓝采用相对其他通道大30的颜色判定，绿色/白/Lime位置仍精确ARGB，完整PNG字节SHA两轮匹配。

接受版794e3b 42项，独立重编译cd6d45再42项；16原保真程序集实际bound/replay路径核对，runtime-map172项，162引用中10直接原源码程序集。45IL/6类型0da7ad，父原控件/保真资源98065/d5dc69通过，bc89d3预检/冻结/绑定通过；两轮14PNG完整SHA和实际解码尺寸核对，图像已查看。PNG签名均真实PNG，无图像替身或绘图算法副本。

无生产C#/项目修改、私有写、SDK/handler替换、真实窗口或鼠标键盘、轴/相机/点胶/SQL、原完整生产Task/MSBuild/部署。AKRS.Galaxy2.Dispense全部82源文件、可视编辑/鼠标键盘及管理/ZX2200参数桥仍未验收。旧主阅读器和47专题4997独立视图保持，16工程/29组/1436文件/13项目标整体未完成。

见[测试](native-dispense-rendering-test.json)、[审计](native-dispense-rendering-audit.json)、[进度](native-dispense-rendering-progress.json)。
