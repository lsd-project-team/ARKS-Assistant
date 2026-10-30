import { choices, flow, outcome, step } from './builders.ts';

// goto 的落点分别保留；重测、重取和下一颗不是同一个重试循环。
export const s2PickFlows = [
  choices(
    's2-pick-modes',
    '取晶入口与运行模式',
    'Pick 的 OffLine 在 try 之前返回；其余模式先准备、换嘴和清嘴，之后才判断 DryCycle。模式名称不能作为所有动作都不发生的依据。',
    ['s2-pick-mode'],
    [
      step(
        'guard',
        '焊点与步骤门控',
        'IsDoWork 排除 Disable、EnableInSystem1 和已经不需要的 S2 步骤；这里没有 Bond 节点的 EntityState.Process 判断。是否执行动作与外层是否标记消息 Finished 是两层判断。',
        ['s2-pick-guard', 's2-worker-commit'],
      ),
      step(
        'offline',
        'OffLine 提前返回',
        '记录开始日志后直接返回 Success，没有进入 Prepare 或 finally；本方法未调用 WorkStart，也未置 Running。外层线程仍按返回结果处理当前消息，因此不能写成“离线取晶消息始终未完成”。',
        ['s2-pick-mode', 's2-pick-success', 's2-worker-commit'],
      ),
      step(
        'prepare',
        '先准备，再检查空跑',
        '准备焊点、下一芯片名、吸嘴与初始速度；首启先发要料并清首启/新产品标记。非首启、使用翻转台且为新产品时，可能先退顶针，再刷新 Map、发要料；DipMode 非 Off 会置 IsNeedDip。之后调用换嘴和清嘴，换嘴非 Success 原样返回。',
        ['s2-pick-prepare', 's2-pick-product', 's2-pick-mode'],
      ),
      step(
        'dry',
        'DryCycle 仍调用移动与信号',
        '空跑辅助方法先等待允许取料，再按载具类型调用实际移动，抬到安全位并 WaitStart；成功路径用后台任务请求下一颗或通知翻转台，再返回 Success。这里没有正常 Pick 调用，也没有 S2FinishedStep。',
        ['s2-pick-dry', 's2-pick-dry-move', 's2-pick-dry-flip', 's2-pick-dry-return'],
      ),
    ],
  ),
  flow(
    's2-pick-sequence',
    '取晶位置、动作与计数',
    '普通路径先做取片补偿视觉并计算补偿量，再进入 NextDie。下一颗会回到该标签，保留标签之前已经取得的补偿量和准备状态。',
    ['s2-pick-mode', 's2-pick-next'],
    [
      step(
        'wait',
        '按载具等待允许取料',
        '非补偿模式调用 WaitAllowBondPickSignal，非 Success 转为 Abort。非翻转、静态华夫盒且开启避让时轮询许可，换盒请求可调用避让与 Pause，循环检查 Stop；其他分支按相机和载具选择晶圆或翻转许可，最后 WaitStart。',
        ['s2-pick-next', 's2-wait-pick-avoid', 's2-wait-pick-signals'],
      ),
      step(
        'position',
        '计数、视觉与预取位',
        '每次进入 NextDie 都增加 Total。静态华夫视觉 Retry 回到 NextDie，其他非成功结果按 switch 返回；其他载具用 Bond 相机时先移动搜晶并等信号。随后计算位置、准备取晶参数、调用预取位移动与 CheckBeforePick，失败提前返回。',
        ['s2-pick-next', 's2-pick-position', 's2-pick-before-check'],
      ),
      step(
        'pick',
        '选择取料类型，再进入 Repick',
        '翻转台优先，否则按晶圆/华夫载具选类型。Repick 调用 Pick：Success 清翻转工具有料标记，Abort 返回，返回 Exception 时先请求顶针缩回再返回。实际抛出的异常则进入外层 catch，不能保证执行这个枚举分支。',
        ['s2-pick-action', 's2-pick-throw', 's2-pick-success'],
        [
          outcome(
            '补偿模式的局部跳过',
            '私有 Pick 在补偿模式直接 Success；普通分支取得参数后下降、开真空、按类型顶起、延时和上抬。这个局部返回没有跳过外层 DoWork 的所有位置、计数和漏晶判断。',
            's2-pick-inner',
            's2-pick-lift',
            's2-pick-leak',
          ),
        ],
      ),
      step(
        'count',
        'Usable 在漏晶检测之前增加',
        'Pick 返回通过当前 switch 后，芯片和顶针的 Usable 计数各加一次，再进入漏晶判断。重取回到 Repick 会再次经过这些计数；计数增加不能写成真空检测已通过或芯片实物合格。',
        ['s2-pick-action', 's2-pick-leak'],
      ),
    ],
  ),
  choices(
    's2-pick-leak-options',
    '取晶漏晶：五种选择',
    '启用芯片检测且取晶后检查失败时，先增加真空报警计数，再显示五个选择。每次重新检测失败也会再次增加报警计数。',
    ['s2-pick-leak'],
    [
      step(
        'retry',
        '重新检测：回到 ReCheckVacuum',
        '只回到漏晶检查标签，不重新取晶，也不重跑 NextDie 的 Total 计数；检查再次失败会再次显示对话框。',
        ['s2-pick-leak'],
      ),
      step(
        'abort',
        '退出：返回 Abort',
        '本节点在对话框分支直接返回 Abort，仍执行 try 的 finally；外层 BondTask 对 Abort 另行 Stop、请求安全高度和可选胶盘归位。',
        ['s2-pick-leak', 's2-pick-success', 's2-worker-results'],
      ),
      step(
        'ignore',
        '忽略：继续记录有料',
        'Ignore 只跳出对话框 switch，继续将 IsMaterialOnBondhead 置 true、发起灯光任务和等待开始。该标记不能证明刚才失败的漏晶检查已转为通过。',
        ['s2-pick-leak', 's2-pick-success'],
      ),
      step(
        'repick',
        '重取：回到 Repick',
        'Cancel 回到 Pick 调用前的 Repick，不重新搜晶、算位置或增加 Total；再次取晶后会重新增加 Usable，并再次进入漏晶检测。',
        ['s2-pick-action', 's2-pick-leak'],
      ),
      step(
        'next',
        '下一颗：抛料后回到 NextDie',
        'Yes 先 ThrowAction。使用翻转台时仅在下一芯片名为空的分支刷新 Map/发要料，但随后都会发取料成功信号；不用翻转台则刷新 Map 并用当前芯片名发要料。置 IsRepickComponent 后回到 NextDie，重新等待、增加 Total 并计算位置。',
        ['s2-pick-next-die', 's2-pick-next'],
      ),
    ],
  ),
  choices(
    's2-pick-signals',
    '取晶收尾与后台信号',
    '取晶最后的灯光和供晶通知通过 Task.Run 发起，DoWork 不等待这些任务完成。主方法 Success 不能证明后台信号已经发出。',
    ['s2-pick-success'],
    [
      step(
        'light',
        '先有料标记，再等开始',
        '漏晶分支通过或选择忽略后，先置有料并启动精度相机灯光任务，再 WaitStart；等待失败返回 Abort 时，这些先发生的操作并未在本层回滚。灯光方法查 PR 后调用 SetLight，后台任务没有由此处 await。',
        ['s2-pick-success', 's2-pick-wafer'],
      ),
      step(
        'wafer',
        '晶圆通知按下一芯片分支',
        '不用翻转台时仅非补偿模式在后台调用 SendSignalToWaferTable；下一芯片等于当前且非空时用当前芯片名，否则仅 AccuracyMode.Off 分支用下一芯片名刷新 Map 并发要料。后者没有排除下一芯片名为空。',
        ['s2-pick-success', 's2-pick-wafer'],
      ),
      step(
        'flip',
        '翻转通知等待离开区域',
        '使用翻转台时在后台循环判断 XY 区域；在区域内 Yield 后继续，离开才发取料成功。Pause 重置计时；超 10 秒提示，忽略重置计时，退出 Stop 并结束任务。此循环未单独检查普通 Stop，不能写成随主方法退出而同步取消。',
        ['s2-pick-success', 's2-pick-flip'],
        [
          outcome(
            'finally 的顺序',
            '进入 try 的分支最终先置 State.Stop，再调用 WorkStop；回调若抛出异常，可覆盖原本准备返回的枚举。OffLine 的提前返回不执行这个 finally。',
            's2-pick-mode',
            's2-pick-success',
          ),
        ],
      ),
    ],
  ),
];
