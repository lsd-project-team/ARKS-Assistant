# 点胶原生报告接入源码交接视图

[打开点胶证据阅读器](module-source-explorer-native-dispense.html)。接入点胶几何、控件、绘制、输入、窗体五份已冻结报告，新增260段原始源码声明。独立视图共有29模块、552条既有代表关系、52专题/5257段快照；12个原生专题共500条运行边界提示。父6444+新增91=6535冻结绑定，绑定数不是测试数或覆盖率。

|原生报告|新增声明快照|具有声明候选的原IL/所选IL|阅读器入口|
|---|---:|---:|---|
|[native-dispense-geometry](native-dispense-geometry-review.md)|58|61/61|[源码入口](module-source-explorer-native-dispense.html#module=AKRS.Galaxy2.Dispense&evidence=topic%2Fruntime%2Fnative-dispense-geometry%2F53ff6934c1544d88)|
|[native-dispense-control](native-dispense-control-review.md)|43|43/43|[源码入口](module-source-explorer-native-dispense.html#module=AKRS.Galaxy2.Dispense&evidence=topic%2Fruntime%2Fnative-dispense-control%2Fb508275404ed4bdf)|
|[native-dispense-rendering](native-dispense-rendering-review.md)|42|45/45|[源码入口](module-source-explorer-native-dispense.html#module=AKRS.Galaxy2.Dispense&evidence=topic%2Fruntime%2Fnative-dispense-rendering%2Fff88a56663c117f6)|
|[native-dispense-input](native-dispense-input-review.md)|84|84/84|[源码入口](module-source-explorer-native-dispense.html#module=AKRS.Galaxy2.Dispense&evidence=topic%2Fruntime%2Fnative-dispense-input%2F73ccc09422165f49)|
|[native-dispense-form](native-dispense-form-review.md)|33|34/34|[源码入口](module-source-explorer-native-dispense.html#module=AKRS.Galaxy2.Dispense&evidence=topic%2Fruntime%2Fnative-dispense-form%2Ff50a4c334095bc1e)|

## 原文与运行边界

41个源文件依照既有审计清单逐一核对字节SHA、BOM、UTF8/CP936解码文本SHA；Roslyn解析567个方法、构造器、属性与运算符声明，0语法错误。六个Point2D显式转换和相等/不等运算符纳入本轮提取，未修改此前已冻结提取器。260段在专题之间可能重复，不等于260个独立方法或行为。

五份报告共267个所选IL成员在原文件中均有同类型/成员名候选，未匹配成员为0。这是声明定位结果，既不证明参数/泛型语义精确匹配，也不证明全部声明或分支运行。属性关联get/set候选，同名重载保留全部候选；泛型成员名归一化。实际ObjectHelper源码为Clone<T>，冻结Cecil签名为T AKRS.ZX2200.Infrastructure.Utils.ObjectHelper::Clone(T)，两者单独校验；不是SDK同名类型。

每个新片段显示其绑定报告、测试记录、IL候选和该轮运行范围。几何报告包含原XML/BMP文件往返；控件报告只执行隐藏控件方法和委托；绘制报告执行原OnPaint/快照PNG，但不认定全部GDI所有权或持续泄漏；输入报告使用构造的Mouse/Key事件参数执行原方法，不发送OS输入。输入报告的窗体声明仍明确为静态IL；窗体报告另有实际Set/Get、直接Load/网格刷新和ZX2200转换器证据，3个弹窗入口仍是静态IL，未执行ShowDialog、完整OK/Cancel/Retry或实际窗口交互。

窗体DefaultInfo丢失、单位与旧显示尺寸顺序、转换精度/字段丢失、异常时部分提交都保留原报告边界；本轮只把这些证据接入阅读器，未修正生产行为或重新运行CLR生产动作。

原主阅读器40专题3817快照、保真阅读器40专题4757快照、上一独立原生视图47专题4997快照及其全部JSON证据/哈希/专题值均保留。552条代表关系未增加推断边，29模块仍是部分复核。页面底部校验命令已指向本派生视图，生成一致性使用--check，避免误操作旧生成器。

## 浏览器与冻结验证

Edge headless实际执行8次模块/专题检索与源码选择，包括两份报告中同一GetContent的不同运行边界、原Point2D运算符、RemoveAllCurves、SaveSnapshoot、OnMouseDown、ZX2200 InitPatternData与仓库ObjectHelper.Clone。泛型方法深链接重新加载、旧力控专题搜索、弹窗入口搜索和空结果提示通过。5257段文本和500条原生边界提示逐一渲染精确核对，4种宽度1600/1440/850/390无页面横向溢出、0浏览器错误。截图已观察，限定范围提示、源码与既有关系面板可读。

初版提取保留561声明/254快照，补运算符后6bf3b0形成567/260。首次浏览器b496ad因验证脚本写成不存在的ClearCurves失败，原候选与日志保留；对照原IL声明改为RemoveAllCurves后d267d8通过，页面底部命令修正后be9219重跑全部浏览器检查通过。首次预检7c71d2错误假定Cecil签名含Clone<T>；冻结原IL实际为Clone(T)，原失败脚本/日志保留，核对原源码泛型语法及实际签名后1698b2通过。上述两处均为验证脚本断言修正，未修改生产实现。

bf558a校验五份原生报告及上一阅读器六个父绑定通过；23f70b完成冻结和最终绑定检查。新增91项包含生成输入、原文/编码元数据、接受结果、失败候选、脚本、截图和派生文件；未重复执行原生生产任务。

![实际阅读器截图](/C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-dispense-reader/reader-browser.png)

正式1328回归维持原冻结范围。本轮没有完成全部29组语义/动态调用、真实设备运动/视觉/UI/SQL、完整MSBuild与织入、部署或工程师交接验收。16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-dispense-reader-test.json)、[审计](native-dispense-reader-audit.json)、[进度](native-dispense-reader-progress.json)、[源码快照与IL候选](native-dispense-reader-evidence.json)。
