# 原九宫格几何与目标点限位集成验证

2026-09-29。180项断言通过，整链35个原方法、3个属性、3个原信号绑定。来源与执行结果见wafer-geometry-test.json；审计见wafer-geometry-audit.json。

## 本轮新增
完整CalculateDiesPosition、ResetNineDiesData、Distance、DetectInkDot、MatchResultToWorld数组重载、IsInSearchRange、IsInCircleRange、IsInRectRange和台面目标点IsInCollisionCircle，共9个原方法，接入已有消费者、搜晶、Stop、顶针和台面链。生产代码未修改。

## 已验证行为
- 四种方向逐一验证9个理论位置及对应匹配结果归属。重置清除Exist，中心保持台面Z，周边理论位置Z为0。
- 相同槽位重复结果由后者覆盖；等距按if分支顺序优先左上。先前分配会替换槽位参考位置，进而影响后续最近点归属。没有额外最大匹配距离过滤，仍受搜索范围过滤。
- 匹配失败或空结果会保留已重置的无芯片状态；null数组/null元素产生异常。离线或空跑时坐标包装固定返回一个零偏移，若匹配返回两项，则先填中心后发生IndexOutOfRangeException。匹配返回数量由SDK替身提供，尚未证明生产视觉会产生这一组合。
- 圆形范围接受边界；矩形严格排除边界，组合范围取交集。目标点限位半径转long；半径2.9按2检查。控制器越界时先关真空再拒绝轴命令，显式关闭限位检查则传递目标。
- 墨点成功且算法结果IsSuccess为true，或DoWork返回非Success，会把该芯片Exist设false；检测成功但未检出墨点保留芯片。空/null算法结果抛异常且已有几何分配仍保留。
- 缺失模板、光源、采图、修正、执行和释放异常均按顺序传播。采图后的墨点异常路径没有finally保证Dispose；图像寿命测试使用可观测Bitmap替身，并非真实System.Drawing图像释放验收。
- 空匹配但成功标志为true时仍会为墨点流程采图并释放；匹配失败则跳过墨点。不存在的芯片不访问墨点依赖。
- 四种模式消费者成功路径通过；Nine会执行两次原九宫格计算。首次vision.match或pixel.world中注入原Stop后，Nine仍调用两次XY并发出许可。该初次计算路径不再次进入停止检查，受控结果不等于实机行为。

## 边界与后续
运行器在.NET 10.0.11编译原成员及Signal，不是完整产品Framework构建。九宫格方向和载具形状枚举、行列间距、范围配置是明确夹具输入；MatchResult、GetOffsetWorld、相机/算法SDK、Bitmap、轴驱动、坐标标定、I/O、日志和存储仍为替身。原AnalyseDie重试/跳过/报警逻辑未接入；真实视觉质量、原生UI、生产并发、实际配置/DLL及设备验收仍待完成。29组保持partial。

运行node scripts/test-wafer-geometry.cjs及node scripts/build-wafer-geometry-audit.cjs --check；统一回归和阅读器结果以独立integration-verification回执为准。
