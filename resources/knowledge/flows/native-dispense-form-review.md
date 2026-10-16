# 原点胶窗体数据往返与ZX2200转换桥

两轮全新Framework CLR STA进程各40个不同检查通过，每轮实际构造两个原EpoxyPatternForm和一个原ZX2200 UcEpoxyApplication，执行原SetContent/GetContent、原Load/表格刷新方法及公开正反转换和纯预处理。34原IL方法、2源程序集、19份C#及1resx输入哈希、每轮16保真源程序集；父6380+新增64=6444冻结绑定。

窗体、控件及真实DevExpress/WinForms表格已构造，但没有显示窗口、ShowDialog、消息循环或OS输入，Form/Uc Handle均false。Load和刷新是两个封闭原方法delegate直接调用，未伪造源对象、替换控件或反射写字段；不等同完整弹窗/result/Retry生命周期。

## 尺寸与首次Load的区别

原构造字段micronPerPixel50、die350×300，6列表格由真实Designer建立。首次GetContent没有背景Bitmap，原EPEData构造器ArgumentNullException。

输入A为micron2、die200×160、两点曲线，SetContent先按旧字段设显示die7×6，再接收新单位/尺寸。GetContent返回物理die200×160、micron2，逻辑点1.25/−2.5及逐点HeightMeasurement=true保持；显示die却尚未按新字段计算。

随后直接调用原EpoxyPatternForm_Load，显示die变100×80（200/2、160/2），并原InitGvSegmentEndpoints创建表格数据。这是必须保留的修正边界：不能只据SetContent旧尺寸声称首次真实弹窗显示必然错误，因为原首次Load确实重算。完整ShowDialog顺序仍未执行。

再输入B为micron4、die320×240，SetContent仍先使用旧A，显示die100×80，物理字段/GetContent已是B；应得80×60尚未在此方法更新。再次null SetContent先按现有B设die80×60，随后读null.DefaultInfo NRE，曲线引用保留。重复SetContent旧字段行为已实际复现，实际Retry/重用时是否传入不同单位还需调用方生命周期证据。

## 默认参数、测高标志与表格

原SetContent导入DefaultInfo MaxSpeed77/HeightMeasurement=true，并控制第5列Visible。GetContent只构造新EPEData，不调用SetDefaultValues，返回DefaultInfo MaxSpeed/EndSpeed0、HeightMeasurement=false，而原控件默认参数仍77/true、逐点参数仍完整。把这份返回数据再SetContent，控件默认参数也变0，证明原窗体往返丢失默认参数，未与模板文件的HeightMeasurement丢失混为同一环节。

无bool参数的SetContent重载隐藏测高列，但不会清除逐点HeightMeasurement=true。图像保持caller Bitmap同一引用，点数组/结构复制，矩阵值复制。GetContent导出的物理尺寸和曲线值正确，不把默认参数损失扩展成所有参数丢失。

SetContent只ClearSelection，不刷新legacy曲线/段DataGridView。导入1曲线时两表Rows仍0；直接调用原RefreshDataGridVeiws后都为1。后续空内容清空原CurveList、启用Paint/禁用Move，但两表仍各1旧行。原界面调用方是否另调用刷新必须按路径判断；本轮保存了明确的直接方法差异。

## 实际失败的部分提交

|原SetContent输入/回调|原结果|
|---|---|
|公开DieSizeChanged回调抛fixture异常|显示die已经设置；默认点/曲线/背景和新物理字段未导入，异常同一实例|
|EpePointList=null|默认点参数已经换99，原曲线引用和旧单位4仍保留|
|BackgroundImageInfo=null|默认点换111、曲线引用已替换，旧单位4仍保留，ArgNull|
|背景info存在但Image=null|SetContent接受并更新单位8，GetContent因背景Bitmap为空ArgNull|
|公开把构造后的MicronPerPixel改0|Form导入0未验证；GetContent调用原EPEData时ArgumentOutOfRange|

0单位样本使用第二个原Form和公开Size10×10，避免在后续背景重建中绘制无穷die边界；只验证导入与GetContent验证边界，没有触发后续Load或设备动作。各原Form.Dispose达到嵌套控件，caller Bitmap仍有效；探针随后明确释放当时只读可达的选定GDI对象，未声称替换时丢弃的全部Matrix或所有资源均已释放。

## ZX2200正向转换

原Uc构造绑定真实EpoxyApplication公共模型，Load/Init/实际运动未调用。原ChangeListPosToPatternData把每点(double X/Y)先cast float，再×1000；样本1.23456789/−2.3456789因此按float精度进入编辑器，未宣称double精度全保真。

Speed12.75→MaxSpeed12，EndSpeed6.75→6，AltitudeCompensation−3.75→−3，均int向零截断；Acc2.5仍double保留。OpenGlueFlag反转为Dummied，HeightMeasurement强制false，DripTime/AdvanceClose/LagOpen对应Time/PreDelay/PostDelay。改返回的EPEPointData值不会改原EpoxyApplicationLocation引用对象。

## 反向转换、遗漏字段与预处理返回值

原InitPatternData先Clear同一个公共DispensePatternParas列表，再每曲线构造新location并Add。X/Y除1000，与EPEData.MicronPerPixel7无关；Speed来自int MaxSpeed，Acc保留2.5，Dec也被写Acc2.5（原8.5丢失）。OpenGlueFlag/Dummied反转、Altitude和时间延迟保持。

EndSpeed没有赋回，原6.75/编辑值6最终变0；Z9.5、Name original-point、Index42和Type Paint也没有映射回来，变默认Z0/Name null/Index0/Type Dispense。这是此UI转换接口的往返损失，不证明原底层模型存储/运动接口均不支持这些字段。

随后InitPatternData实际调用原DispenserMoveHelper.EpoxyPretreatment，但丢弃返回值。原预处理通过仓库内AKRS.ZX2200.Infrastructure.Utils.ObjectHelper.Clone的BinaryFormatter Serialize/Deserialize生成深复制，再归一化、spindle比例和旋转/偏移处理。公开源模型的restored坐标/Speed12仍保留，不因这个调用变成归一化或Speed6。

单独调用同一原EpoxyPretreatment，样本默认策略SingleDotOnly，对两点首点取归一化后的中点，再加偏移10/20/30，得到10/20/30、Speed6；返回clone及点对象与源不相同，源Speed12/Z0保持。本轮实际验证默认策略和clone独立性，未覆盖Drawing/Printting等全策略或所有退化几何。

原ChangeListPosToPatternData(null) NRE，null公共pattern list返回空、null曲线数组NRE。原InitPatternData(null)先Clear旧列表再NRE；两曲线的新data第二项null时，首曲线两点已Add，再NRE，真实部分提交且未执行后面的预处理/Refresh。

## 管理按钮调用方范围

原Uc.BtEditPattern_Click和Form模板新增/读取三个body只读IL，含真实ShowDialog。Uc编辑点击把转换点封装为micron1/die3500×4200/新500×500 Bitmap，再SetContent→ShowDialog；OK后先Clear旧pattern，再GetContent→InitPatternData，EpoxyIsReasonable失败goto Retry，最后Dispose窗体/置null。Form模板读取点击在SetContent后显式刷新各表，所以不能把直接SetContent旧表行当成模板读取完成后必然旧行。

上述modal入口没有执行，且原规则检查可能弹消息框；没有用DialogResult替身或截短ShowDialog来宣称完整管理流程通过。本轮仅实际构造Form/Uc并验证其可独立调用的数据桥，完整编辑/Cancel/OK/Retry/模板管理与路径/保存生命周期仍需验收。

## 保留诊断与验证

26cb49首次native在32项后失败，探针假定纯预处理首点归一化应9/18，没有计入原默认SingleDotOnly两点平均。原失败Cases/Host/compile/EXE/root完整保留；公开源枚举确认SingleDotOnly=0，接受版按原结果10/20/30及Speed6核对。没有把探针错误当产品失败。

39f565接受版40项，1be1e4独立重编译/replay再40，Probe/标签/结果/诊断相同，实际保真bound/replay16程序集位置核对。初次IL bbed6b误查SDK ObjectHelper未匹配，初输出保留；原调用签名定位到仓库ObjectHelper源码，最终6f03a9为34方法/2程序集，未伪造SDK clone绑定。父原输入/保真资源61371/478239通过，3de5e6预检/冻结/绑定通过，无独立session；162引用含10直接源引用、runtime-map172项。

无生产C#/工程/私有写、SDK/算法/handler替身，真实窗口/输入、轴/相机/点胶/SQL、原整生产Task/MSBuild/部署。19源码/1resx补证不是原点胶全部82文件或ZX2200全业务完成；旧主阅读器及47专题4997独立源码视图保持，16工程/29组/1436文件/13项目标整体未完成。

见[测试](native-dispense-form-test.json)、[审计](native-dispense-form-audit.json)、[进度](native-dispense-form-progress.json)。
