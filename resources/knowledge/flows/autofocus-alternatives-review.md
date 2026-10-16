# 可选自动对焦算法：步骤、实例状态与生产接入边界

本报告补充[生产对焦主链](autofocus-module-review.md)，不替代其 `AutoFocus` 结论。范围限于 `trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs` 中另三种实现。生产主链调用的是 `AutoFocus`；不能因为存在以下方法，就把它们串进生产工作步骤。

## 调用证据与简明流程

[机器证据与测试回执](autofocus-alternatives-test.json)保存原文、文件 SHA256、片段 SHA256 和全 trunk C# 具名引用。排除 bin/obj/.git 的词法扫描得到五处：三个方法声明、AdjustThreshold 声明以及 New 内对 AdjustThreshold 的调用。未找到三种算法的具名调用点；不覆盖反射、外部程序集或其他表达方式，不声明这些方法绝不使用。

| 方法 | 输入与工作步骤 | 输出与局部退出 |
| --- | --- | --- |
| DoFocusing | 相机名、Z轴、两端范围；查相机→检查轴/软限位启用→三段采样→二次多项式拟合→移动到顶点 | 返回拟合位置；轴缺失/软限位关闭/二次项为零时提示并返回0 |
| DoFocusingNew | 查相机→先移动到Plimit→采图评分→空阈值方法→根据历史最高分选方向移动→检测下降与下限 | void；连续两次低于历史最高分或移动后位置≤Nlimit时设置实例停止标志 |
| DoFocusingNew2 | 查相机→先移动到Plimit→采图评分→低于历史最高分时缩步反向→按分差判断恢复移动或继续移动 | void；分差<1时先恢复移动并直接break；否则移动后检查下限 |

以上方法没有持久化、数据库或任务队列操作；主要输出是轴移动副作用。相机仓库查询、轴命令与评分 SDK 是外部依赖边界。

## DoFocusing 的三段采样

见[原文:30–147](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L30)。相机查询发生在 AxisZ 空检查之前；软限位接口取回 IsEnable/N/P，但本方法只使用 IsEnable 作门控，没有用返回 N/P 将目标位置截断。

1. [第一段:40–74](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L40)：步长=(Plimit−Nlimit)/5，最多六次从下界向上取点；评分低于前一次即退出。FirStation 使用末尾两/三项的条件选择，不是全列表最大值搜索。
2. [第二段:77–111](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L77)：步长=范围/25，从 FirStation 反向最多六次；同样遇下降退出。随后直接访问 `SecFocusRes[Count−3]`，没有第一段的 Count<3 保护。若第二个样本即低于第一个，Count=2，将产生负索引；这是源码分支分析，未执行此方法。
3. [第三段及输出:95–132](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L95)：九项数组保留一个第二段样本，补采八点，步长=范围/125；`Fit.Polynomial(...,2)` 后只检查二次项非零，就移动至 `-b/(2a)` 并返回。没有在此验证曲线向下开口、顶点处于采样范围或评分达标。实际拟合数值和轴保护由外部库/驱动决定。

本方法未见 catch/finally；失败提示和返回0不可等同于安全回位，也不能将0一概解释为成功的焦点位置。

## 两种 New 方法的状态和停止次序

[共享字段:149–153](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L149)包括 stopAdjusting=false、maxSharpnessScore=0、stepSize1=1；[New2字段:316–319](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L316)另含 stepSize=4、direction=1。它们是实例字段，两种方法进入时都没有重置停止标志和历史分值。

- [New:155–206](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L155)：先 AbsoluteMove(Plimit)，再判断 while。AdjustThreshold(0) 的目标方法为空。每轮先移动再判断下降；第一次下降将步长减半，第二次连续低于历史最高分则停止；遇不低于历史最高分的样本重置下降计数、更新最高分并恢复步长1。没有显式上限位置比较，也没有总采样上限或本地停止/急停查询。
- [New2:322–366](../../trunk/AKRS.Galaxy2.AutoFocusing/Model/AutoFocusing.cs#L322)：评分下降先将 stepSize 除3并反转 direction，然后判断 `score−max<1`。此条件不是绝对差条件；所有下降都满足。该分支执行 `RelativeMove(-direction*stepSize*3)` 并break，跳过下面的Nlimit检查。不能仅凭注释把该移动称为回到最佳焦点。
- 当共享 stopAdjusting 已为true，再调任一方法仍执行最初的 AbsoluteMove，却不进入采样循环。实例是否在生产中复用尚未证实；不能把受控复用情景当作现场故障。

## 已执行的八项受控检查

[脚本](../../scripts/test-autofocus-alternatives.cjs)原样提取 New、New2、AdjustThreshold 及实例字段；相机、位图、评分、轴与仓库使用替身，轴立即记录位移。没有调用真实运动或 SDK。

| 场景 | 已验证结果 |
| --- | --- |
| New依次评分10、9、8，起点10 | 相对移动+1、−1、−0.5后停止，末位置9.5 |
| New停止后复用同实例 | 移动到新起点，零次采样 |
| New停止后改调同实例New2 | 共享停止标志，仍零次采样 |
| New依次评分1、2、3 | 从输入Plimit=10移动到13，测试相机样本耗尽后主动抛异常结束；这不是生产超时 |
| New2首评分0，起点10 | 满足分差<1，移动−12到−2后结束 |
| New2停止后复用同实例 | 移动到新起点，零次采样 |
| New2评分10、9，起点10 | 先+4，再在反向缩步后执行+4，到18结束 |
| New2首评分0，Nlimit=5 | 到−2并直接break，未执行末尾下限检查 |

## 尚未完成

DoFocusing 的真实 MathNet 拟合和三阶段运行未测试；三种方法均未证明生产可达。真实配方、轴同步/软限位契约、相机 SDK、资源释放、最终焦点质量及停止/急停仍需验证。新增证据只缩小“其他算法未展开”的缺口，不能将整个自动对焦模块升级为完整验收，也不改写现有生产主链图。
