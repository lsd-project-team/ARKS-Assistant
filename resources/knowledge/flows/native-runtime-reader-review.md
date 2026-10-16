# 原生报告接入可检索源码阅读器

[打开独立阅读器](module-source-explorer-native-runtime.html)。本轮把7个已冻结原生报告接入源码交接视图，新增240段原始声明。原保真阅读器29模块、552代表关系、40专题/4757快照的JSON值全部保留；新视图47专题/4997快照，未增加模块完成数或推断调用关系。父5961+新增82=6043冻结绑定。

|绑定原生报告|新增声明快照|匹配原IL/原IL总数|阅读器入口|
|---|---:|---:|---|
|[native-s1-rework-context](native-s1-rework-context-review.md)|16|17/18|[源码入口](module-source-explorer-native-runtime.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=topic%2Fruntime%2Fnative-s1-rework-context%2F42cef0148da0f077)|
|[native-predispense-prerequisites](native-predispense-prerequisites-review.md)|60|60/61|[源码入口](module-source-explorer-native-runtime.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=topic%2Fruntime%2Fnative-predispense-prerequisites%2F5bf29dbc3307fa6e)|
|[native-s2-shelf-gates](native-s2-shelf-gates-review.md)|30|30/31|[源码入口](module-source-explorer-native-runtime.html#module=AKRS.ZX2200%2FInfrastructure&evidence=topic%2Fruntime%2Fnative-s2-shelf-gates%2F6807f282bf637148)|
|[native-s2-compensation-prerequisites](native-s2-compensation-prerequisites-review.md)|30|30/31|[源码入口](module-source-explorer-native-runtime.html#module=AKRS.ZX2200%2FInfrastructure&evidence=topic%2Fruntime%2Fnative-s2-compensation-prerequisites%2F6807f282bf637148)|
|[native-s2-reset-propagation](native-s2-reset-propagation-review.md)|17|17/18|[源码入口](module-source-explorer-native-runtime.html#module=AKRS.ZX2200%2FInfrastructure&evidence=topic%2Fruntime%2Fnative-s2-reset-propagation%2F6807f282bf637148)|
|[native-s2-action-boundaries](native-s2-action-boundaries-review.md)|28|28/29|[源码入口](module-source-explorer-native-runtime.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=topic%2Fruntime%2Fnative-s2-action-boundaries%2F248763d85eebfd74)|
|[native-force-calibration](native-force-calibration-review.md)|59|59/64|[源码入口](module-source-explorer-native-runtime.html#module=AKRS.ZX2200%2FInfrastructure&evidence=topic%2Fruntime%2Fnative-force-calibration%2Fb09a750d0aca55d7)|

## 快照与运行证据的区别

63个原文件字节/已审计编码哈希核对，Roslyn解析1456个方法、构造器与属性声明、0语法错误；这不是完整语义分析。根据各报告已冻结IL的qualified type与member name选择240个声明位置，同名重载都保留为候选，没有按参数语义/动态分派断言精确绑定或执行。

原SDK Singleton/JSON等IL没有仓库源声明的成员明确登记在unmatchedIlMethods；不生成伪源码或用相似类型填补。本轮7专题仅依据来源文件归属挂到既有模块，不增改552条代表关系。源码按原审计UTF8/CP936严格解码与归一化行尾，匹配原文件SHA和解码文本SHA；旧保真快照/哈希值全部保留，旧两个阅读器未修改。

新片段顶部直接显示绑定原生报告、原生测试记录及“同名重载均为候选，不证明该声明已执行”的边界；可展开匹配原IL签名。执行的配置、公开fixture、原Task或直接调用、未执行UI/SQL/设备，以各绑定报告为准。尤其S2点胶离线predicate=false的直接绕过调用、原清零Task公开UI异常、力控公开数值样本，都没有变成成功生产验收。

新增源码候选在不同专题可能重叠，240不等于240个独立行为或测试。各报告原生断言数不相加认定覆盖；阅读器阶段只执行浏览器，没有重新执行生产Task/动作，也没有改变原生报告、源码、测试、SDK或工程。

## 实际浏览器验证

Edge headless真实加载、29模块导航、Bond模块的ActualForceToInputForce专题检索/源码选择、原生边界提示、深链接reload、S2 AfterBond检索、空结果边界提示通过。全部4997快照逐一渲染精确文本、240边界提示全部显示，browserErrors=0。1600/1440/850/390四宽度document.scrollWidth均不超过viewport，截图已人工观察，新增提示、原代码与原关系面板可见。

首次解析器PowerShell无参数GetText过载失败afd6f3，原候选保留；显式CancellationToken后ea4171解析通过。809579生成，d14896最终浏览器验证，12590/76dd70父力控/源码编码流水线通过，b172db生成一致性/预检/冻结/绑定通过，无新增独立CLR生产执行。此前7d9de7浏览器检查已通过，最终d14896仅调整截图定位，并重跑同一交互与显示检查。

正式冻结1328、主阅读器40专题3817快照及源码模块原台账不改。本独立视图继续保持29模块部分复核；未完成所有业务语义/动态调用、实际硬件/厂商依赖、完整MSBuild/织入、部署/UI/SQL、整Retry/输送握手和工程交接验收。16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-runtime-reader-test.json)、[审计](native-runtime-reader-audit.json)、[进度](native-runtime-reader-progress.json)、[原文快照与未匹配IL](native-runtime-reader-evidence.json)。
