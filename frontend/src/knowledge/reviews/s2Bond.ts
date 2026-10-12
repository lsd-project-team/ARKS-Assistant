import { choices, flow, outcome, step } from './builders.ts';

// 动作重做与步骤提交分开说明；提交之后的异常没有在本方法内回滚。
export const s2BondFlows = [
  choices(
    's2-bond-modes',
    '固晶门控、离线与空跑',
    'Bond 在 try 之前调用 WorkStart 并置 Running；try 内先 PrepareBeforeBond，再判断 OffLine 和 DryCycle。开始回调本身抛异常不受这个 catch / finally 包围。',
    ['s2-bond-entry'],
    [
      step(
        'guard',
        '只处理 Process 焊点',
        'IsDoWork 先要求 EntityState.Process，再排除 Disable、EnableInSystem1，最后查当前 S2 步骤是否仍需执行；这与 Pick / AfterBond 仅查物料状态和步骤的门控不同。',
        ['s2-bond-guard', 's2-pick-guard', 's2-after-guard'],
      ),
      step(
        'offline',
        'OffLine 也先准备并提交',
        '准备会取当前芯片、吸嘴、焊点和 Z 轴初始速度。准备成功后，OffLine 调用 S2FinishedStep 并返回 Success，仍执行 Stop / WorkStop；准备过程实际异常则走 catch，不能把缺轴故障当作每次离线的必然结果。',
        ['s2-bond-prepare', 's2-bond-entry', 's2-bond-final'],
      ),
      step(
        'dry',
        'DryCycle 使用位置偏移并提交',
        '空跑根据焊点坐标、吸嘴高度、芯片厚度、位置补偿和 BondingDistance 算位置，再加代码中的 Z=5 偏移；旁边“3mm”注释与该常量不同。调用移动、PlacementDelay 和安全位后提交 S2 步骤，再刷新 UI 并 Success。刷新若异常，步骤可能已经提交。',
        ['s2-bond-dry', 's2-bond-final'],
      ),
    ],
  ),
  flow(
    's2-bond-placement',
    '固晶位置与贴片动作',
    '正常固晶先计算位置、移动到预固晶位并发胶盘信号，再进入 ReBond。重贴返回该标签，保留之前计算的位置和预移动结果。',
    ['s2-bond-entry', 's2-bond-pre-move', 's2-bond-contact'],
    [
      step(
        'move',
        '预固晶移动失败提前返回',
        '按慢行程配置形成预固晶 XYZT 并调用 MoveToPreBondPos，非 Success 原样返回；成功后才发胶盘信号并记录 RealBondPosition。AbsoluteMove 和 InterpolationMove 走不同移动入口，具体运动曲线仍需继续复核。',
        ['s2-bond-pre-move', 's2-bond-move-mode'],
      ),
      step(
        'type',
        'ReBond 重新设置力曲线',
        '标签之后先设置力实时曲线并调用 ZeroBondhead，再按 IsDipOnTU 和 WatchFluxCount % DipOnTUAfterBondingNum 选 DipFluxOnTU / BondOnTU。这里没有对除数为 0 单独保护；异常会进入外层 catch。',
        ['s2-bond-contact', 's2-bond-final'],
      ),
      step(
        'contact',
        '私有 Bond 的下降、延时与释放',
        '下降后等待 max(PlacementDelay - VacuumOffDelay, 0)。非 DipFluxOnTU 才关闭吸嘴真空、异步吹气并等 VacuumOffDelay；随后记录力、关主动读力并上抬。私有方法实际异常返回 Exception，外层收到非 Success 就提前返回。',
        ['s2-bond-inner', 's2-bond-inner-return', 's2-bond-contact'],
      ),
      step(
        'detect',
        '按配置进入贴后留晶检查',
        'Bond 成功后先导出力数据；仅非 DryCycle、非 DipFluxOnTU，且启用芯片检测与贴后慢行程时检测是否仍有料。先按状态关吹气，取 ComponentCheckAfterBonding 的反值，再后台 CloseToolVaccum；检测有料才显示重贴对话框。',
        ['s2-bond-contact', 's2-bond-check'],
        [
          outcome(
            '导出力数据的重试',
            '导出开关关闭或载具为空时跳过；保存 Excel 捕获异常后，操作员 Retry 递归调用 ExportForceData，其他选择返回继续。目录和路径准备在该局部 try 前，异常可直接传播给外层；这个重试不是重新贴片。',
            's2-bond-export-entry',
            's2-bond-export-return',
          ),
        ],
      ),
    ],
  ),
  choices(
    's2-bond-rework',
    '固晶留晶：重贴与重新取贴',
    '留晶对话框的 Retry 回到本方法 ReBond；Cancel 则重建消息并返回 ExcuteResult.Retry。两条路径的准备动作与队列处理不同。',
    ['s2-bond-check', 's2-bond-rework'],
    [
      step(
        'rebond',
        '重贴：回到 ReBond',
        'Retry 只重做力曲线、清零、类型选择与 Bond，不重跑 CalculateBondPos、MoveToPreBondPos、胶盘信号或 RealBondPosition 记录。',
        ['s2-bond-pre-move', 's2-bond-contact', 's2-bond-check'],
      ),
      step(
        'abort',
        '终止：失败计数后 Abort',
        'Abort 增加固晶失败数后直接返回，未提交此处的 S2 步骤；finally 仍执行。外层线程消费 Abort，再 Stop 和请求安全位置。',
        ['s2-bond-rework', 's2-bond-final', 's2-worker-results'],
      ),
      step(
        'ignore',
        '忽略：抛料后继续收尾',
        'Ignore 增加固晶失败数，调用 ThrowAction 后只跳出 switch，继续后面的 TU 蘸胶视觉与步骤提交。忽略并不把刚才的检测失败改为成功。',
        ['s2-bond-rework', 's2-bond-dip', 's2-bond-commit'],
      ),
      step(
        'repick',
        '重新取贴：重建消息后 Retry',
        'Cancel 增加失败与抛料计数，ThrowAction 后建立 Pick、条件成立的 UpLook、条件成立的基板相机校正、最后 Bond；置 IsRepickComponent 后返回 Retry。这个列表没有蘸胶节点，也未在这里重置 S2RemainingSteps；外层 continue 重新等待并选未完成消息。',
        ['s2-bond-rework', 's2-worker-results', 's2-rework-current'],
      ),
    ],
  ),
  flow(
    's2-bond-commit',
    'TU 蘸胶结果与固晶提交',
    '贴后检测通过或忽略后，仍有 TU 蘸胶视觉、步骤提交、统计和刷新。提交位置早于后续统计及 UI 成功返回。',
    ['s2-bond-dip', 's2-bond-commit', 's2-bond-final'],
    [
      step(
        'dip',
        'TU 蘸胶视觉有自己的结果分支',
        '当 IsDipOnTU 且计数余数为 0 时，先将 WatchFluxCount 清零，再做视觉。外层 switch 对 Success 继续，对 Fail 增加失败数后继续，对 Abort 直接返回，对 Exception 增加失败数并提示后返回。此 switch 未列 Retry；内层胶印 Fail 还可能先被转换成 Success，两个层级不能混用。',
        ['s2-bond-dip', 's2-bond-tu-return'],
      ),
      step(
        'before',
        '清有料标记，然后提交步骤',
        'TU 视觉分支没有提前返回时先增加 WatchFluxCount，再调用 VisionPreviousBondPosition。开启人工看贴片时移相机、展示视觉并等标记关闭；遇 Stop 只清标记、跳出等待，然后保存参数并返回。调用者仍继续清有料标记和提交步骤，没有据这个 Stop 另设返回。',
        ['s2-bond-dip', 's2-bond-commit', 's2-bond-visual-wait'],
      ),
      step(
        'after',
        '提交之后仍可能返回 Exception',
        '提交之后才统计贴片位置、增加吸嘴使用次数、检查固晶数量和刷新 UI。任一调用实际异常会进入外层 catch，准备返回 Exception；本方法没有恢复已经提交的步骤。',
        ['s2-bond-commit', 's2-bond-final'],
      ),
      step(
        'finally',
        '最后 Stop，再调用 WorkStop',
        'finally 先 State.Stop，再 WorkStop。回调异常可覆盖 Success / Exception 等准备返回值；外层 BondTask 没有统一 try 包围整段动作循环，因此不能把回调异常当作必然进入枚举 Exception 清理。',
        ['s2-bond-final', 's2-worker-select', 's2-worker-results'],
        [
          outcome(
            '软件状态的范围',
            'S2 步骤完成、后台吹气已发起或吸嘴计数增加，都是当前调用和状态变化；这里没有把它们统一变成实物贴片质量通过的确认。',
            's2-bond-inner',
            's2-bond-commit',
          ),
        ],
      ),
    ],
  ),
  choices(
    's2-bond-tu-vision',
    'TU 胶印检测与再次贴片',
    'DipFluxOnBondPositionVision 先查胶盘硬件和胶印位置，再相机视觉及胶印判定；内层 Fail 与最终返回给 BondTask 的结果并非同一枚举。',
    ['s2-bond-tu-input', 's2-bond-tu-return'],
    [
      step(
        'input',
        '按识别个数与偏移检查',
        '结果为 null 或个数不等于 DipOnTUFluxNum 时报警；否则逐项按 BlobResult 转换坐标，计算相对中心的 X / Y 偏移。Y 表达式保留源码的减负值，等效加 FluxDistanceY，不能按字段名称自行改成减值。',
        ['s2-bond-epoxy-data', 's2-bond-epoxy-limits'],
      ),
      step(
        'alarm',
        '人工 OK 用新结果重新判定',
        'X / Y 绝对偏移严格大于各阈值时报警。OK 取 PR 当前 AlgResults 回到 Recheck；Ignore 返回 Fail；Abort 返回 Abort；其他选择抛异常。此 OK 不是无条件接受胶印，也不直接重贴。',
        ['s2-bond-epoxy-limits'],
      ),
      step(
        'success',
        '检测 Success 后再次 Bond',
        '包装方法收到 Success，按慢行程配置调整 bondPos.Z，调用 MoveSafeBondXYZ，再执行 Bond(BondOnTU)，直接返回这次 Bond 结果；内层这次贴片非 Success 不会被自动改成成功。',
        ['s2-bond-tu-return'],
      ),
      step(
        'fail',
        '检测 Fail：禁用焊点后 Success',
        '包装方法收到 Fail 就 SetMatterDisable 并返回 Success，外层因此可能继续 WatchFluxCount、提交和统计；收到 Abort 则直接置机器状态 Stop 后 Abort。包装 try 内的未知结果或实际异常转 Exception；硬件与空位置检查却在这个局部 try 前，由更外层 catch 处理。',
        ['s2-bond-tu-input', 's2-bond-tu-return', 's2-bond-dip', 's2-bond-commit'],
      ),
    ],
  ),
];
