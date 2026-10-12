import { choices, flow, outcome, step } from './builders.ts';

export const waferFlipFlows = [
  flow(
    'wafer-flip-task',
    '翻转线程与焊头交接',
    'FlipTask 等供晶许可，执行翻转动作，再发布焊头可取料并等取料完成。动作返回与线程回零并非统一收尾。',
    ['w-flip-worker-entry', 'w-flip-worker-results'],
    [
      step(
        'start',
        '线程创建与本轮芯片',
        'Start 在任务为空或非 Running 时设 Working 并创建无取消令牌的 LongRunning 任务，最后返回 true；不是等待该任务成功。DoWork 先 FlipTableGoHome，再 WaitStart；没有所需芯片时延时 100ms 并下一轮。',
        ['w-flip-start', 'w-flip-worker-entry'],
      ),
      step(
        'wait',
        '需要翻转且工具未持晶才等供晶',
        'UseFlipTable 且软件标记 IsComponentOnFlipTool 为 false 才进入 NextDie 标签、Wait IsWaferAllowPickSignal，false 直接 return。已有持晶标记会跳过供晶等待和本次翻转动作。',
        ['w-flip-worker-entry'],
      ),
      step(
        'results',
        'Success、NoStart 与退出结果',
        'DryCycle 调空跑翻转，其他调用普通入口。Success 置持晶标记；NoStart 回 NextDie，不重新获取本轮芯片。Exception、Abort 对 Wafer 请求 ReturnEjection 后 return；其他未列结果没有置持晶标记，但仍可落到发布许可。',
        ['w-flip-worker-results'],
      ),
      step(
        'handoff',
        '发布后等待 BondPickSucceed',
        'Set IsFlipAllowPickSignal 后 Wait IsBondPickSucceedSignal，false 直接 return。末尾 FlipTableGoHome 只在外层循环正常退出后执行，提前 return 和未捕获异常不保证经过它；DoWork 没有 finally。',
        ['w-flip-worker-end'],
      ),
    ],
  ),
  choices(
    'wafer-flip-notify',
    '翻转避让后的后台供晶请求',
    'notifyWafer 回调通过 Task.Run 启动另一段轮询；翻转动作调用回调不等于后台请求已经发出。',
    ['w-flip-notify-entry', 'w-flip-notify-exit', 'w-flip-controller-transfer'],
    [
      step(
        'avoid',
        '先等翻转轴越过搜索避让位',
        '后台任务读取翻转 T，只有严格大于 SearchComponentAvoidancePos 才进入下一芯片判断。不存在下一芯片时直接结束该轮询，不刷新地图也不 Set 需求。',
        ['w-flip-notify-entry'],
      ),
      step(
        'request',
        '存在下一芯片才更新与请求',
        '下一芯片名非 null 时，当前 component 为 Wafer 配置先请求顶针准备位，再 RefreshMap，随后 SetCurrentNeedChipName(component.Name) 并 Set 需求。赋值用的是当前字段 component.Name，不是查询到的 nextComponentName。',
        ['w-flip-notify-entry'],
      ),
      step(
        'timeout',
        '十秒提示、停止与调度边界',
        '超过 10000ms 提示继续或退出；Ignore 重启计时，Abort 调 Stop 后 return。每轮另检查 IsStop 并延时 10ms。调用者不 Wait 这个 Task，且回调捕获的是 component 字段，不能保证名称快照或在翻转 Success 前完成。',
        ['w-flip-notify-exit', 'w-flip-worker-results'],
      ),
    ],
  ),
  choices(
    'wafer-flip-actions',
    '普通与空跑翻转动作的差别',
    '普通与空跑均调用真空准备和运动控制；空跑不是不触发硬件的纯界面模拟。',
    ['w-flip-controller-entry', 'w-flip-dry-entry', 'w-flip-dry-return'],
    [
      step(
        'prepare',
        '载具真空准备与取片高度',
        '两个入口都取当前 FlipTool，用工具晶圆高度加芯片过行程计算取片位，再 PrepareBeforePick。准备方法按 Wafer / Waffle 开关对应真空，开启分支还延时；其他类型没有有效 case。',
        ['w-flip-controller-entry', 'w-flip-prepare', 'w-flip-dry-entry'],
      ),
      step(
        'pick',
        '普通下降、真空与顶针',
        '普通路径按开关选择一次下降或高速预取、低速取片。拾取延时为 max(FlipToolPickupDelay−VacuumOffDelay,0)，然后开翻转真空；只有 CarrierWithWaferConfig 请求顶针抬起，之后执行真空延时。',
        ['w-flip-controller-entry', 'w-flip-controller-pick'],
      ),
      step(
        'transfer',
        '普通上抬决定检测和通知时机',
        '启用取后慢速时先低速上抬，只有这一分支内且启用检测才检查漏晶；处理完成再调用 notifyWafer，并移到交接位。未启用取后慢速则直接通知和移动，未执行这里的漏晶检查。',
        ['w-flip-controller-pick', 'w-flip-leak-entry', 'w-flip-controller-transfer'],
      ),
      step(
        'dry',
        '空跑仍开真空、抬顶针并交接',
        '空跑移动到取片位加 3mm，延时并开翻转真空；晶圆配置仍请求抬顶针，之后真空延时、通知并移动交接位。没有普通路径的低速漏晶分支。两个入口正常返回 Success，catch 仅记录后返回 Exception，没有统一 finally 回零。',
        ['w-flip-dry-entry', 'w-flip-dry-return', 'w-flip-controller-transfer'],
      ),
    ],
  ),
  choices(
    'wafer-flip-leak',
    '翻转漏晶的五种选择',
    '检查只在普通动作的取后慢速分支内启用。每次漏晶增加真空报警计数；重测、重取与下一颗的返回点不同。',
    ['w-flip-leak-entry', 'w-flip-leak-repick', 'w-flip-controller-transfer'],
    [
      step(
        'recheck',
        '重新检测',
        'Yes 回 ReCheckVacuum，只重复 IsComponentOnFlipTool 判断；未再次执行下压和开真空的重取动作。重复失败会再次增加报警计数。',
        ['w-flip-leak-entry'],
      ),
      step(
        'abort',
        '终止',
        'Abort 先 Machine.Stop，再返回 ExcuteResult.Abort。若 Stop 本身抛异常，会被控制器 catch 转成 Exception，不能保证最终枚举仍为 Abort。',
        ['w-flip-leak-entry', 'w-flip-controller-transfer'],
      ),
      step(
        'ignore',
        '忽略',
        'Ignore 离开结果 switch，继续后面的通知及移交，正常返回 Success；这不能证明工具上实际有芯片。线程 Success 之后才置软件持晶标记。',
        ['w-flip-leak-entry', 'w-flip-controller-transfer', 'w-flip-worker-results'],
      ),
      step(
        'repick',
        '重取当前芯片',
        'Retry 关真空、低速下压、拾取延时、开真空、真空延时、低速上抬，再回 ReCheckVacuum。此处没有重做完整 PrepareBeforePick 或重新请求顶针抬起。',
        ['w-flip-leak-repick'],
      ),
      step(
        'next',
        '请求下一颗',
        'No 先调用 notifyWafer，再 FlipTableGoHome，返回 NoStart；FlipTask 消费 NoStart 回 NextDie 再等供晶许可，不发布本轮翻转可取料信号。后台通知可能尚未完成。',
        ['w-flip-controller-transfer', 'w-flip-worker-results'],
        [
          outcome(
            '通知完成不是同步前提',
            '回调内部 Task.Run 没有在调用点等待完成；若通知条件不满足，它还可能不发下一次需求。',
            'w-flip-notify-entry',
            'w-flip-notify-exit',
          ),
        ],
      ),
    ],
  ),
];
