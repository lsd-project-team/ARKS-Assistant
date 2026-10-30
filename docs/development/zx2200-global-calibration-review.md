# 全局标定与扫描采集：源码复核

覆盖清单 08.01–08.06。按实际菜单事件、两代全局标定窗体、区域插值、驱动工具、Bond 与 BC 关系读取。主程序相关文件在原编译清单中，业务原件只读；没有执行轴移动、回零、补偿下载或标定精度测试。本文供 Archify 引用已提交事实，逐行原件另由 source-evidence.json 绑定。

## 入口与新版数据主链

主页面分别打开 FrmGlobalCalibration、FrmGlobalCalibrationEx、FrmBondCompensateCalibration 与 BC 的 FrmCalibration，四个事件均在 Designer 绑定，不能合成一个必经入口。新版主链是预定义 World/Axis 对应点、拟合并生成预期轴点、真实扫描写 ScanAxis、粗略完成门控、建立区域、按优先级插值，再在带补偿扫描中把插值加到目标 XY。新版软件区域与旧版驱动映射是不同数据和应用链。

依据：UcMainSystem.cs 1411–1415、1706–1727、1768–1772；UcMainSystem.Designer.cs 1326、1552、1567、1609；FrmGlobalCalibrationEx.cs 417–556、659–854、882–1071、1098–1171；BilinearCompensator.cs 43–59、249–305。

## 新版扫描范围与点位

手动对应点要求 WorldX/WorldY 为配置列/行间距的整数倍，确认后取当前机械 XY（模拟时取起点值），同一 World 点可确认替换。自动预定义点是 4×4 循环并交替 rowDir；每行先移动 Y，但没有同步 currentPos，下一条 X 移动又使用旧 currentPos.Y，WorldX 仍按 j 正向递增，因此不把这段代码称为已验证的规则蛇形四乘四采样。

生成要求至少 3 对点；MathService 用伪逆拟合 3×3 仿射矩阵。自定义生成拟合 World→Axis，扫描后生成拟合 World→ScanAxis，两者都填充四象限，并用矩阵重算 Axis。代码中的 colSpace 与 rowSpace 都读取 SpRowSpacing，不替它改成理想的独立行列间距。四象限填充会拒绝任一行/列数为零；重复 World 点按容差跳过。矩阵还直接写固定 D 盘位置，FileStream 前没有在这里创建目录。

GlobalCalibrationData 区分 World、预期 Axis 和实测 ScanAxis，各值四舍五入 8 位。ScanCompletedFlag 只要求全部 ScanAxis 标量中零值少于 3 个，空列表也为 true，一点未测（两个零）也可能通过；不是逐点成功记录。建立区域还要求构造数据至少 4 点。模拟点列先生成 16 个 World/Axis 点，再调用同一个扩点方法。

依据：FrmGlobalCalibrationEx.cs 361–556、1178–1214、1288–1343、1512–1602；GlobalCalibrationData.cs 25–86；GlobalCalibrationDomainEx.cs 76–88；MathService.cs 275–322。

## 普通、温漂、带补偿与模拟扫描

启动先创建暂停事件和取消源，索引 0 为普通扫描，其他已选索引为带补偿扫描；finally 恢复控件。真实扫描先到起点 XYZ，每点先等暂停事件，再检查取消。可选首点/每 N 点/每段时间采温漂 Mark；该辅助把保存的机械拍照位转 G0 后调用默认 Bond 相机的共同视觉，不能因参数名含 UpLook 就画成上视相机。捕获后恢复标定 PR 硬件并安全 XYZ 返回，否则走 MoveXY。两代 MoveXY 的 ETEL 分支传 XY/1000 给 ipolLine 并等待，其他驱动走模块 XY。

普通真实扫描对 Axis 目标定位，结果经像素→G0→机械坐标写 ScanAxis，记录指令、编码器、像素、Mark、温漂等字段，每 10 点刷新日志；正常走出循环后 Save（包括按取消标志 break），finally 刷新日志。异常会跳过循环末的 Save。真实带补偿扫描对 Axis+区域插值定位，仍写 ScanAxis 并记录日志，finally 刷新，但没有普通扫描那条尾部域 Save。不是下载硬件补偿表后再扫描。

普通模拟扫描只加每轴约 ±0.002 的随机偏差并写 ScanAxis，正常结束 Save；带补偿模拟只记录期望目标/补偿与已有或估算 Mark，不同样写回和保存。模拟分支没有真实分支同样的尾部 finally 刷新。预测值只在普通扫描日志中记录；模型创建代码已注释，Predict 在 predictor 为空时给零，取消勾选仍直接 Dispose，不把勾选描述为已经加载模型并作用到运动。

暂停只 Reset/Set 事件，停止先 Set 释放暂停再 Cancel；没有逐轴 Stop 或统一撤销当前运动/视觉。检查发生在下一点前，延时未传取消令牌。循环勾选订阅完成事件，正常返回后经 500ms 再启动；停止按钮没有取消该订阅，完成事件前也没有按取消状态分支。关闭在运行时拒绝，编辑态关闭可选择 Save。

依据：FrmGlobalCalibrationEx.cs 227–249、309–354、574–623、659–1091、1392–1396、1484–1509、1609–1695；System2Domain.cs 184–236。

## 区域、点序与文件

区域以 WorldY 四舍五入 6 位分行、WorldX 排列，键为预期 Axis，值为 ScanAxis−Axis。寻找相邻两行与两列四角；按当前数组顺序进入公式，退化分母抛异常，没有找到单元则不命中。区域按 Priority 降序，取首个包含目标的区域，未命中返回零；不是多个区域叠加。新增区域先过粗略扫描标志、名称唯一确认和至少 4 点构造；添加/删除/排序主要更新内存列表，域保存仍在相应 Save 入口。

扫描点排序按 WorldY、WorldX 先排，再反转奇数行得到蛇形。添加、替换、删除、清空和单独排序不在同一处理体立即 Save。导入 JSON 检查非空列表后先 Save 旧域，再清空/装入新列表，未在此立即保存导入后状态；导出用 JsonFormatHelper 保存当前列表，另有格式化日志路径和输出，不能当作只执行一种导出。

依据：BilinearCompensator.cs 43–185、191–305；FrmNewCompensationRegion.cs 51–75；GlobalCalibrationData.cs 93–122；FrmGlobalCalibrationEx.cs 558–564、1098–1171、1288–1477。

## 旧版单轴、二维平台与模式

旧窗体有 8 个索引模式，单独采集/二维/单轴 X/单轴 Y/测试精度/Bond 标定/二维与 Bond 交替标定/交替验证。列表第 4 个文字仍写“单轴补偿X”，索引 3 实际执行 ScaleY；按调用分派说明。启动先 Save，任务未完成不再启动；停止置 isStop，部分入口另保存 AxisCompensateProgram，未等同轴停止。

ScaleX/ScaleY 各关闭本轴线性补偿并回零，按列或行采集；相机模式用像素偏差乘 SpinX/SpinY，轴模式对中后用目标减指令位置。首轮收集、后续累加，不是平均；每轮写单轴 ETEL 文件并下载，首轮后激活。定位失败或 isStop 直接返回，没有统一恢复入口前的开关状态。单轴文件步长固定 3.0e-3，不自动使用界面采集间距。

二维 InitData 关闭补偿并使 XY 回零，到起点并对中，更新起点和保存，两映射列表以每格 0.0001 初始化。初步 X 做两轮首行并复制到各行，初步 Y 做两轮首列并复制到各列；随后逐格循环累加像素误差，每轮 SaveData。ETEL 方向系数为 -1，其他默认 1。二维定位失败记录 999 并加零继续；RecordData 记录失败哨兵，StageCalibrationTest 另按 ColumnCount−30、Y+5、X+50 的特定位置验证，不能称为全平面精度认证。

FrmAssistant2DStage 当前直接引用检索只找到声明。其列表有 3 项，第二项回调和外层都递增步索引；行数表达式用末行 Y 减起点 X，Save 又把行列数都赋成 rows。保留为未确认主入口的旧辅助实现，不替它拼成正常示教链。

依据：FrmGlobalCalibration.cs 85–98、154–238、245–304、310–382、508–818、863–1209、1404–1604；FrmAssistant2DStage.cs 93–243、280–300。

## ETEL 与固高文件、下载及启用

SaveData 按 X 轴驱动类型分支。ETEL 先写 StageXY 文本、首次下载，再 OpenStage：关闭补偿、回零 XY、再下载并激活。文本用域中的起点/间距/网格，偏差格式四位小数，按列数换行；保存文件、下载和激活是不同步骤。下载方法捕获 DsaException 仅弹框，不向上层返回失败；因此后续激活调用并非以该次下载成功 bool 门控。

固高先把累计偏差 ×10000 转 int[,] 并保存域，OpenStage 只在 X 轴为 GTAxis 时进入关闭/回零后下发表；其他非 ETEL 类型虽会生成整数表，没有同样的开启分支。参数默认脉冲比 10000，步长是先把间距转 int 再乘比例；芯片 core=2，默认轴 1/2，两张表启用。AutoScale 将行列数量各加 20，以原表边缘值向外复制；不是重新测得扩展区域。GuGaoDrive 开启接口返回 bool，但 OpenStage 调用处没有接收；关闭接口累加返回码非零会抛异常。

旧域的 GetAxisCompensate 取四角并将整数除 10000，有范围及绝对补偿不超过 1 的判断；外边界检查后仍访问 index+1，不能推定所有边界均有合法邻格。GetBondHandCompensate 是相机/焊头两位置补偿的差，未在此将它当作新版区域插值。SDK 命令的真实单位和设备精度没有运行验证。

依据：FrmGlobalCalibration.cs 415–575、1234–1286；ETelDrive.cs 27–70、78–194、204–330；GuGaoDrive.cs 839–1086；GlobalCalibrationDomain.cs 94–169。

## Bond 偏移的两种实现

旧窗体 Bond 标定更新两张数组并逐轮导出/保存；但 BondCompensate.GetBondCompensate 开头直接返回零，后续插值不可达。能采集不表示旧模型当前已给目标加补偿。独立 FrmBondCompensateCalibration 则反复 Bond→视觉→Pick 对中到每轴 0.002 范围，再初始化 PlanePoint2Ds；逐格带已有偏移放置、测量、取回并减去本次偏差，整轮导出 Excel 后继续，无固定完成轮数。初始收敛圈没有 stop 检查，主循环逐点检查；该循环没有直接调用域 Save，参数保存按钮另做保存。

独立验证用已有表移动并记录，不在该方法更新表；VisionResult 实际使用硬编码“测试”视觉，未使用该配置 PrName。GetBondOffset 未建表给零，建表后调用 PlaneInterpolate；后者当前只取所属单元 q1，超出边界反而返回输入 XY，不称为已验证的双线性补偿。Pick/Bond 调用力控与真空吹气，不仅是相机采样，均未在此运行。

依据：FrmGlobalCalibration.cs 1293–1300、1404–1604；BondCompensate.cs 74–80；FrmBondCompensateCalibration.cs 90–132、172–471；BondCompensateCalibration.cs 73–87；MathAdvanceHelper.cs 27–47。

## BC 偏移关系

BC 窗口用 GlobalCalibrationRing 定位并对中，按行退 markDistance、每点前移 56，取 Bond 相机一层转换的像素偏差写 ΔX/ΔY，随后退 54 再对中。内层异常只 break 当前行，外层仍可能装入部分行并 Save、提示完成，不把弹窗视作全部点采齐。

实际 GetΔXY 属于 BCOffsetRelationCalibration。先取相邻 Y 行中较近的一行，不在 Y 方向插值；只有前后行都存在才进入 X 处理，否则零。X 在相邻点间线性插值，低于首点时用前两点外推，高于最后点则零。代码用 Capacity<=1 而非 Count 门控，且只检查 ΔX>1 或 ΔY>1，不能写成双侧绝对值保护。GenLineEqu 没有相同 X 的单独保护。

另一个视觉验证任务内层 for 的递增是 i++ 而非 j++，并且结果表 X/Y 位置写到同一列，不描述为已经可正常结束的规则验证；当前主工程 GetΔXY 的直接调用只在这个窗口的查询/验证，不推定生产动作已普遍接入。

依据：FrmCalibration.cs 52–60、199–216、246–356、364–503；BCOffsetRelationModel.cs 36–188。
