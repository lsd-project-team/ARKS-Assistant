import { flow, outcome, step } from './builders.ts';

export const s1ActionFlows = [
  flow(
    's1-dispense-commit',
    '点胶与步骤提交',
    '点胶节点先经过单步、预点胶及 WaitStart，再计算位置并调用插补。焊点步骤在返回 Success 和线程完成消息之前提交。',
    ['s1-point-before', 's1-point-work', 's1-worker-results'],
    [
      step(
        'single',
        '单步与离线标记',
        'OffLineWork 先调用 S1FinishedStep，把当前焊点步骤写 true，之后才等待单步。非单步模式直接通过；单步等待返回 false 时点胶节点返回 Abort。',
        ['s1-point-before', 's1-single-gate', 's1-point-finished'],
        [
          outcome(
            '等待期间关闭单步模式',
            'Signal.WaitSingleStep 循环发现 IsSingleStepWork=false 返回 false；它没有调用 WaitStart，也没有在该循环检查机器 Stop/Pause。不能把它解释成统一的暂停停止门控。',
            's1-single-signal',
          ),
        ],
      ),
      step(
        'pre',
        '预点胶与停止检查',
        '调用 PreDispenseAction.DoWork，非 Success 返回 Alarm；随后 Signal.WaitStart=false 返回 Fail。这两处都早于本次插补，但离线分支可能已提交过焊点步骤。',
        ['s1-point-before', 'tr-signal-start'],
      ),
      step(
        'dispense',
        '胶型、坐标与插补',
        '按当前步骤查询胶型。胶型偏移经焊点坐标变换后，加点胶位置补偿和设备偏移；角度由坐标系角度加旋转补偿。DryCycle 将 isDrip 设为 false，仍调用 InterpolationApplication；返回非 Success 则返回 Alarm。',
        ['s1-current-context', 's1-point-work'],
      ),
      step(
        'commit',
        '先提交焊点，再完成收尾',
        '插补返回 Success 后先 S1FinishedStep，再刷新统计。观看点位的等待、预点胶时机标记及 finally 回调都发生在焊点提交之后；直到动作返回，线程才有机会标记消息 Finished。',
        ['s1-point-work', 's1-point-after', 's1-worker-results', 's1-reset-messages'],
        [
          outcome(
            '观看期间停止',
            '观看循环检查 IsStop，停止时清观看开关并 break，随后仍可走后续标记和 Success 返回；不会在该 break 处回滚已提交的焊点步骤。',
            's1-point-after',
          ),
          outcome(
            '回调异常',
            'WorkStart 位于 try 前；finally 先置动作 State=Stop，再调用 WorkStop 和刷新载具。回调或刷新抛出的异常可能向线程传播，不能保证由 catch 转成 Exception 返回码并进入线程 Stop 分支。',
            's1-point-before',
            's1-point-after',
            's1-worker-results',
          ),
        ],
      ),
    ],
  ),
  flow(
    's1-segment-handshake',
    '分段排序与等待',
    'Divide 在消息队列中插入交互动作。交互通过两个信号请求 S1 段间输送；它调用 Wait，却没有使用 Wait 的布尔结果。',
    ['s1-divide-messages', 's1-segment-action'],
    [
      step(
        'partition',
        '按索引拆分消息',
        'GetFirstMatrixIndex 对异形配置取坐标 X<0 的基板索引；普通配置取矩阵前 ColumnCount/2 列。排序方法把消息分成索引在集合中和不在集合中两组；不是简单按基板编号一半切分。',
        ['s1-segment-index', 's1-divide-messages'],
      ),
      step(
        'insert',
        '实际执行顺序',
        '重组时先加入不在集合中的 lastActionNodeMessages，再加入 InteractiveAction，最后加入在集合中的 firstActionNodeMessages。两组各自保持原消息相对顺序；基板索引 0 的消息也参与该分组。',
        ['s1-divide-messages'],
      ),
      step(
        'request',
        '按位置标记发段间许可',
        'InteractiveAction 仅在 Divide 且 IsTuInDispense1=true 时调用 MoveZToSafePos，发 AllowDispense1TransferToDispense2Signal，再等 TransferToDispense2FinishedSignal。非 Divide 或已不在第一段直接走 Success。',
        ['s1-segment-action'],
        [
          outcome(
            '等待返回 false',
            'Wait 初始或循环检查到 Stop 可返回 false，但交互动作未检查返回值，仍置 IsFirstDispense=true 并走 Success。调用本身没有整体超时参数。',
            's1-segment-action',
            'tr-signal-wait',
          ),
        ],
      ),
      step(
        'pause',
        '等待期间的状态检查',
        'Signal.Wait 进入事件等待前调用一次 WaitStart；事件轮询循环检查 Stop，没有重新检查 Pause。因此进入等待之后的暂停，不等于该循环必然阻塞信号消费。',
        ['tr-signal-wait', 'tr-signal-start'],
        [
          outcome(
            '交互收尾异常',
            '正常 try 异常被转为 Exception，但 WorkStart 在 try 前，WorkStop 在 finally。回调异常仍可能覆盖预定返回结果并向线程传播。',
            's1-segment-action',
          ),
        ],
      ),
    ],
  ),
  flow(
    's1-defect-result',
    '检测结果如何回到线程',
    '检测节点按模式调用视觉与 PostBondEpoxyCheck，再将结果转换成焊点提交、禁用、停止或返工。动作返回 Success 不一定表示执行过视觉检测或判定合格。',
    ['s1-defect-run', 's1-defect-results'],
    [
      step(
        'gate',
        '确认当前焊点需要检测',
        '与点胶节点一样，禁用、仅 S2 启用、当前步骤不再需要执行时跳过；焊点为空抛异常。OffLineWork 在 DoWork 中先提交焊点步骤，之后仍进入检测模式 switch。',
        ['s1-defect-gate', 's1-defect-run'],
      ),
      step(
        'mode',
        '当前实现只处理一种模式',
        'WithoutReferenceSearch 计算检测位置，调用 DispenseVisionDefect，再进入结果处理。这个 switch 没有其他 case；其他模式直接走尾部 Success，不在这里拍照，也没有在该尾部补写 S1FinishedStep。',
        ['s1-defect-run'],
      ),
      step(
        'result',
        '区分提交、禁用与重做',
        'PostBondEpoxyCheck 返回 Success 时提交当前步骤；Fail 时禁用焊点却返回 Success；Abort 时调用 Stop 并返回 Abort；Retry 调用 ReDispense 后返回 Retry；其他值抛异常。此处只解释返回码消费，不推断检查内部的判定标准。',
        ['s1-defect-results'],
        [
          outcome(
            'Fail 的线程行为',
            '线程看到的是 Success，因而标当前动作消息完成；不是在这里因 Fail 退出。后续节点仍按焊点禁用状态进行 IsDoWork 判断。',
            's1-defect-results',
            's1-worker-results',
            's1-point-gate',
            's1-defect-gate',
          ),
          outcome(
            '异常与收尾',
            'try 内的异常返回 Exception；finally 置 State=Stop，调用停止回调及载具刷新。开始回调和 finally 回调的异常不保证被该 catch 包含。',
            's1-defect-run',
          ),
        ],
      ),
    ],
  ),
  flow(
    's1-rework-state',
    '返工与两套完成状态',
    '返工先清焊点步骤，再尝试清指定动作消息。常规 Finish 只清消息标记；重新排序或再次 InjectSteps 也不等于清空已有焊点步骤。',
    ['s1-defect-rework', 's1-rework-messages', 's1-reset-messages', 's1-inject'],
    [
      step(
        'point',
        '先重置当前焊点全部步骤',
        'ReDispense 遍历当前焊点 S1RemainingSteps 的键，把值写 false；准备重置的动作列表包含点胶节点和检测节点。焊点字典重置发生在调用 SetActionNodeReWork 之前。',
        ['s1-defect-rework'],
      ),
      step(
        'message',
        '必须精确匹配动作上下文',
        'WorkMessages 非空时，SetActionNodeReWork 为每个指定动作 Find 同动作名、同基板、同基岛、同 ProcessStepName 的消息，将找到的 Finished 置 false；找不到就抛 ActionNode Sort Error。其 for 虽多次迭代，Find 条件不含循环索引，未逐条重置同名消息。空消息列表会跳过内层循环，不在这里抛缺配对异常，也不重置消息。',
        ['s1-rework-messages'],
        [
          outcome(
            '点胶与检测步骤名不同',
            '两种消息按配方的 if / else if 生成；重置却要求都与当前检测步骤同名。缺少相应消息时抛异常，已有焊点字典修改没有在该方法内回滚，不能宣称返工请求总能成功建立。',
            's1-step-action',
            's1-defect-rework',
            's1-rework-messages',
          ),
        ],
      ),
      step(
        'retry',
        'Retry 从队首重新选择',
        '返工顺利返回 Retry 时，线程不标当前消息完成，下轮 GetNextActionNode 从队首找未完成项。若 ReDispense 抛异常，则在检测动作的 try/catch 内返回 Exception；finally 回调仍可能再次抛异常。',
        ['s1-defect-results', 's1-defect-run', 's1-worker-results', 's1-next-message'],
      ),
      step(
        'restart',
        '消息清空不等于业务步骤清空',
        'Finish 把消息 Finished 全部置 false；Init 清空并重建消息；InjectSteps 只补缺失键。若再次生产复用原载具且没有其他路径重置已完成步骤，IsS1NeedStep 仍为 false，动作可被跳过并由线程标消息完成。',
        [
          's1-reset-messages',
          's1-init',
          's1-inject',
          's1-point-needs',
          's1-point-gate',
          's1-worker-select',
        ],
      ),
    ],
  ),
];
