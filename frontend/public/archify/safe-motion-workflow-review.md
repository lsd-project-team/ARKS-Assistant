# 安全移动：门控、返回值与完成边界

更新：2026-09-28。范围：MoveSafeBondXY、MoveSafeBondXYZ、MoveSafeBondXYZT、MoveZAxis、System2Domain.WaitSingleStep及4D软限位。

[项目入口](index.html) · [可搜索原文](safe-motion-source.html) · [交互流程图](safe-motion.html) · [详细高度/信号审查](bond-motion-single-step-source-review.md) · [测试回执](safe-motion-test.json)

## 源码执行摘要

先读取当前Z，计算安全高度，检查目标软限位，再等待外层单步。拒绝时void返回。高度关系决定XY/Z调用次序；每次Z移动又有独立单步门控。Z包装拒绝返回Abort，驱动返回码原样向上返回，但高层安全移动不检查返回码。异常则直接传播，中断余下语句。

| 当前Z / 目标Z与安全高度关系 | 原方法调用次序 | 测试结果 |
|---|---|---|
| 高 / 高 | XY→目标Z | 通过 |
| 高 / 低 | XY→目标Z | 通过 |
| 低 / 高 | 目标Z→XY | 通过 |
| 低 / 低 | 安全Z→XY→目标Z | 通过 |
| 等于安全高度 | 归入高侧 | 通过 |

证据：[完整原方法49–180行](safe-motion-source.html#safe-xyz)。这里的高低仅指源码数值比较，不据此推断物理轴方向。

## 已执行的关键失败场景

- 外层单步false：不下发XY/Z，但安全高度计算与目标软限位检查已经发生。
- 低→低时外层true、第一次Z单步false、第二次Z单步true：实际调用序列为XY→目标Z；安全Z没有调用驱动。
- 低→高时目标Z单步false：仍调用XY。
- Z驱动返回Fail：高层仍调用后续XY及目标Z。
- Z驱动抛异常：后续XY不执行；XY抛异常：后续目标Z不执行。
- 目标软限位检查抛异常：不进入运动；当前高度NaN在宽松软限位替身下到达最后错误分支并抛异常。
- Z速度按配置倍率相乘；Z包装保留驱动Abort返回值。

[Z包装](safe-motion-source.html#z-wrapper)和[单步包装](safe-motion-source.html#domain-step)均提取真实源码执行。测试并未把高层返回值消费逻辑重写为期望行为。

## 发出、返回、完成不是同一件事

[XY模块](safe-motion-source.html#xy-module)在OffLineWork或轴引用未就绪时直接return；正常路径分别下发X/Y，再调用MotionService.WaitAxesArrival。现在已有[随仓库二进制等待契约审查](motion-arrival-contract-review.md)：可以核查当前DLL的逐轴调用、结果聚合、单轴精度分支与四类驱动调用，但缺原始依赖源码、厂商SDK、现场配置与真机回执，不能声称超时、停轴、精度与取消的整机契约已经验收。Z驱动返回码也不能被改述为物理到位证明。

[信号循环](safe-motion-source.html#signal-step)每轮先检查单步标志，再等待事件；事件到达后没有再次检查该标志。[UI开关](safe-motion-source.html#ui-step)与[Stop](safe-motion-source.html#stop)对信号/标志的变更可能交错。本轮使用确定性信号替身，未验证线程竞争或内存可见性，不能推导关闭单步一定Abort。

## 验证范围和后续验收

34项测试覆盖3种完整编排原方法，编译C#5时仅把插值诊断文本替换为常量。编排测试中高度计算、软限位、信号等待、XY/XYT动作和Z驱动为替身；另5项直接提取4D限位原方法，轴参数为替身；不测试真实安全高度计算、驱动、机械状态或硬件停轴。16段源码索引包括真实高度算法和信号循环，但静态可读不等于运行验收。生产源码未修改。

复现：
- node scripts/test-safe-motion.cjs
- node scripts/build-safe-motion-review.cjs --check
- node scripts/verify-safe-motion-browser.cjs

下一验收条件：取得匹配版本的Axis/MotionService契约与依赖，继续复核其他运动入口及真实配置组合，补真实配置下高度和软限位组合，再验证受控设备中的到位/取消/停止行为。当前仍为局部源码与隔离验证，不提高全局完整验收组数。

首轮验证：15项隔离检查通过；8段原文、文件链接、筛选及1440/850/390宽度检查通过；恢复既有审查文档原哈希后，verify-all: PASS。

## 二维与四维增量复核

[二维MoveSafeBondXY](safe-motion-source.html#safe-xy)只在当前Z低于安全高度时执行“安全Z→XY→原Z”，并不是移动后留在安全高度。当前Z等于或高于安全值时只移动XY。首次Z的Abort仍不会阻止XY和恢复原Z；Z异常则阻止后续语句。

[四维MoveSafeBondXYZT](safe-motion-source.html#safe-xyzt)有与3D相同的四种高度分支，但水平动作替换为XYT，把目标T传给下层；Z返回仍未判定。[下层XYT](safe-motion-source.html#xyt-module)先检查IsReady，再用(X,Y,0,T)检查软限位，然后才判断OffLineWork，最后依次下发X、Y、T并调用外部WaitAxesArrival。不能把这三次下发称为已验证的同步插补。

[4D限位原方法](safe-motion-source.html#limit-4d)只比较X/Y/Z，没有T比较或显式有限数检查。5项新增原方法测试确认：XYZ范围正常时极大T通过；越界X/Z抛异常；NaN比较可通过；Z负限位为1时合成Z=0被拒绝。这里只证明本地方法，不推断驱动最终是否接受非法数值或角度。


## 安全高度与实际调用者

[二维高度](safe-motion-source.html#height-2d)在TU换算、非工作状态覆盖及静态华夫盒避让之后，对最终safeHeight作Z限位检查。[四维高度](safe-motion-source.html#height-4d)只在有TU的分支、后续状态覆盖及避让之前检查一次计算值；在本方法末尾没有再次检查最终safeHeight。若编排实际调用MoveZAxis，它另有Z软限位检查；不能把高度重载的前置检查差异说成驱动一定越界。

[重取片](safe-motion-source.html#repick-call)调用四维安全移动后立即清IsRepickComponent标志，void返回没有直接告知该调用者是否已下发动作。[标定遍历](safe-motion-source.html#calib-call)调用二维安全移动后直接调用MoveAxisZ；若二维外层单步false而静默返回，这个调用点本身未按返回值阻止后续Z语句。这里仅追踪局部调用，不代表这些条件在现场必然发生。

[Archify交互图](safe-motion.html)以10节点/11关系概括2D/3D/4D门控；[图→源码绑定](safe-motion.graph-evidence.json)覆盖每个节点和关系。为保持可读性，图把按入口执行的可选Z收尾合并到XY/XYT动作节点，精确分支仍以本页和原文为准。图形交付9项校验零错误零警告；四种桌面尺寸的浏览器检查通过，明/暗两主题截图已人工查看。全量verify-all: PASS。测试/图均不代表真机安全验收。
