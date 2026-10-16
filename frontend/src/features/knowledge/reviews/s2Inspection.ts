import { choices, outcome, step } from './builders.ts';

// 只描述当前可达分支，不把参考点 region 或报警确认补写成已完成的检测功能。
export const s2InspectionFlows = [
  choices(
    's2-after-modes',
    '焊后检测入口与频率',
    'AfterBond 先 WorkStart、Running 并初始化 defectResult=Success，再进入 try。非编辑测试时才取得当前上下文并检查频率，之后才判断离线、空跑和检测用途。',
    ['s2-after-entry'],
    [
      step(
        'guard',
        '物料与步骤门控',
        'IsDoWork 排除 Disable、EnableInSystem1 与不需要的 S2 步骤，没有 EntityState.Process 门控。非编辑测试路径取得基板、基岛、焊点、检测配置和芯片；编辑测试沿用已经设置的上下文。',
        ['s2-after-guard', 's2-after-entry'],
      ),
      step(
        'frequency',
        '频率跳过也提交步骤',
        '频率功能关闭或 CurrentDefectNumber 达到 DefectFrequency 时需检测；未达到时先把计数加一并返回 false。节点收到 false 就提交当前 S2 步骤并 Success；该跳过路径的 FinishedDefect 调用已注释，因此不清频率计数。',
        ['s2-inspection-frequency', 's2-after-entry'],
      ),
      step(
        'offline',
        'OffLine 提交，但不做视觉',
        '通过前面的频率门控后，OffLine 直接 S2FinishedStep 并 Success，没有调用本方法后续检测用途入口，也未在这个分支调用 FinishedDefect。',
        ['s2-after-entry'],
      ),
      step(
        'dry',
        'DryCycle 移动、延时并提交',
        '空跑把 P1 检测位置变换到 G0 并减焊头相机偏移，调用移动和 DownLookSearchDelay，再提交步骤并 Success；这里没有执行普通胶量 / 焊后 / BLT 检测。',
        ['s2-after-entry', 's2-after-dry'],
      ),
      step(
        'finish',
        'finally 清测试标记，不统一提交',
        'finally 依次清 IsEditTest、置 Stop、WorkStop、刷新 S2 UI，并未统一 S2FinishedStep。回调或刷新抛出异常可能覆盖返回值，WorkStop 异常还会阻断后续刷新；不能写成每个退出路径都已经提交。',
        ['s2-after-final'],
      ),
    ],
  ),
  choices(
    's2-after-vision',
    '焊后定位模式与背崩',
    'AfterBondCheck 用途的 switch 当前只有 WithoutReferenceSearch case。保持配置为 WithReferenceSearch 时没有独立入口，会落到末尾 Success；该路径没有显式步骤提交。参考点 region 存在不等于此模式已接通。',
    ['s2-after-vision-entry', 's2-after-reference', 's2-after-final'],
    [
      step(
        'one',
        '无参考点：一点定位',
        '先对 P1 调用 DefectVision。一点且不检测背崩时直接 WithoutReferResultDeal；该方法点为 null 返回 Fail，否则叠加焊点角度、记录结果，再调用 PostBondDefect。',
        ['s2-after-one', 's2-after-without'],
      ),
      step(
        'two',
        '无参考点：两点定位',
        '两点配置才调用 P2；P2 为 null 返回 defectResult，没有在这里补一次检测。无参考点两点分支使用 (P1 + P2) / 2 交给结果处理，不能把这写成额外的参考点校正。',
        ['s2-after-two'],
      ),
      step(
        'reference',
        '参考点代码的可达限制',
        'P1 / P2 参考点处理仍嵌套在 WithoutReferenceSearch 的 case 内，其中一点参考结果又要求 WithReferenceSearch。当前 switch 没有与之对应的独立 case；配置在此过程中保持不变时，不能按代码区域标题画出一条正常参考点流程。',
        ['s2-after-vision-entry', 's2-after-two', 's2-after-reference'],
      ),
      step(
        'crack',
        '一点背崩：先处理定位结果',
        '开启背崩时先调用 WithoutReferResultDeal；返回非 Success 会再调用一次并返回第二次结果，并非复用第一次返回。Success 后才取匹配结果做背崩检测，Retry 只回到背崩检测标签。',
        ['s2-after-crack'],
        [
          outcome(
            '背崩选择的结果',
            '发现背崩：Abort 增失败数并 Stop；Ignore 增失败数、禁用焊点但 Success；OK 返回 Retry。该方法未追加步骤提交，之前的 PostBondDefect 却可能已经提交，后续背崩失败没有在此回滚。',
            's2-after-crack-result',
            's2-after-post-result',
          ),
        ],
      ),
    ],
  ),
  choices(
    's2-after-results',
    '胶检与焊后检测返回',
    'EpoxyCheck 调相机视觉后进入胶量结果处理；AfterBond 的定位结果进入 PostBondDefect。两者对 Success / Fail / Abort 的外层处理相似，只有胶量 Retry 另有重新点胶路径。',
    ['s2-after-epoxy-entry', 's2-after-epoxy-result', 's2-after-post-result'],
    [
      step(
        'success',
        'Success：非编辑测试才提交',
        '共享检测返回 Success 后，仅 !IsEditTest 时提交当前 S2 步骤并调用 FinishedDefect 清频率计数，再 Success。PostBondDefect 在补偿模式先调用 PickUpDie，再判断结果；拾回内部动作仍需另外复核。',
        ['s2-after-epoxy-result', 's2-after-post-result', 's2-inspection-frequency'],
      ),
      step(
        'fail',
        'Fail：禁用焊点后 Success',
        '共享检测返回 Fail 时，调用 SetMatterDisable 并返回 Success，没有在这两个分支中提交步骤或清频率计数。外层可以标记消息 Finished，但不能解释为该焊点检测通过。',
        ['s2-after-epoxy-result', 's2-after-post-result', 's2-worker-commit'],
      ),
      step(
        'abort',
        'Abort 与未列出的返回',
        'Abort 分支先 Machine.Stop 再 Abort；胶量未列出枚举与焊后非 Success / Fail / Abort 枚举会抛出“未知错误”，由节点 catch 准备返回 Exception。PostBondDefect 没有对应的 Retry 分支。',
        ['s2-after-epoxy-result', 's2-after-post-result', 's2-after-final'],
      ),
      step(
        'retry',
        '胶量 Retry：按步骤重建点胶与检测',
        'ReDispense 遍历 S2RemainingSteps 的所有键，查对应步骤；EpoxyNameApplicationName != "Null" 就添加 S2 点胶，DefectName 等于当前检测名就添加 AfterBond。将匹配键赋 false 后按指定步骤重建消息，再 Retry；不只重置当前步骤，步骤查找没有空项保护。',
        ['s2-after-epoxy-result', 's2-after-redispend', 's2-rework-named'],
      ),
    ],
  ),
  choices(
    's2-after-blt',
    'BLT 测量与人工选择',
    'BLT 用途先测芯片周围和表面高度，再逐项计算差值、平均值与极差；判断严格使用 >，达到阈值相等不在这两个比较中报警。',
    ['s2-after-blt-entry', 's2-after-blt-calc'],
    [
      step(
        'measure',
        '成对高度与列表边界',
        '按 height2.Count 读取两组高度并将差值四舍五入到 3 位，再 Average、Max、Min。这里没有保护空列表或长度不一致；倾斜报警文案还直接读取 0–3 四项，不能假定异常数据会自动补齐。',
        ['s2-after-blt-calc'],
      ),
      step(
        'pass',
        '无报警：提交并清频率',
        '平均差值偏离 BLTStandard 超过 MaxBLTOffset，或极差超过 MaxSurfaceSlope 时累计报警文案；文案为空则提交步骤、FinishedDefect，再 Success。',
        ['s2-after-blt-calc', 's2-after-blt-options'],
      ),
      step(
        'operator',
        '报警后的确认不重新测量',
        '先设置 BLT 视觉硬件、关闭测高气缸并移动相机，再显示报警。Abort 及其他未列选择增失败数、Stop、Abort；Ignore 增失败数并禁用焊点后 Success，不在该分支提交；OK 直接提交、清频率并 Success，没有重新测高度的回环。',
        ['s2-after-blt-options', 's2-after-blt-return'],
      ),
    ],
  ),
];
