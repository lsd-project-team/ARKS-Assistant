import { flow, outcome, step } from './builders.ts';

export const transportInputFlows = [
  flow(
    'transport-entry',
    '输送入口与配置',
    'StartTask 先检查输送配置并初始化模块，再分 DryCycle 与普通模式。普通模式经过载具检查和映射后，按配置调用料仓任务与输送任务。',
    ['tr-entry'],
    [
      step(
        'mode',
        '检查配置与工作模式',
        '未配置输送时返回；否则调用 TransportModule.Init。DryCycle 直接进入 StartDryRun，跳过下述普通模式检查、映射和料仓启动。',
        ['tr-entry'],
        [
          outcome(
            '入口异常',
            'catch 记录并显示异常，没有在该 catch 中调用 Stop，也没有给调用方返回布尔成功值。',
            'tr-entry',
          ),
        ],
      ),
      step(
        'carrier',
        '检查上下料口载具',
        '出料口检查限制 LoaderBin、OnlineWithAutoUnloader；入料口检查限制 LoaderBin、OnlineWithAutoLoader。对应口有料时，重试回到出料口检测起点，终止返回 false。',
        ['tr-carrier-out', 'tr-carrier-in'],
        [outcome('检查失败', 'StartTask 收到 false 后调用 Stop 并退出本方法。', 'tr-entry')],
      ),
      step(
        'map',
        '按配置刷新与映射',
        '仅 Online 先关要料信号；IsReverseSearch 为 true 时刷新 TransportUnit，随后调用 MapMaterial。映射总是调用 Bond.MapBelt，配置 S1 才调用 Dispense.MapBelt；Online 或 OnlineWithAutoLoader 还按前端检测更新入料段状态。',
        ['tr-entry', 'tr-map'],
      ),
      step(
        'tasks',
        '分别启动任务',
        'LoaderBin 先调用 LoaderTask.Start、UnloaderTask.Start，随后调用 TransportTask.Start。各段使用 Task.Run，不在这里等待全部任务结束。',
        ['tr-entry', 'tr-loader', 'tr-unloader', 'tr-task-online', 'tr-split-task'],
        [
          outcome(
            'None',
            '不创建自动入料任务。有 S1 物料时询问是否继续：Yes 发 S1 完成信号，No 调用 Stop。No 分支的 break 只退出 switch，后面三个工位传输 Task 的创建判断仍会执行；到出料部分才 return。',
            'tr-feed-none',
            'tr-split-task',
            'tr-bond-first',
            'tr-wait-task',
            'tr-output-task',
          ),
          outcome(
            '外部设备配置不对称',
            '送板任务用于 Online 或 OnlineWithAutoLoader，收板任务用于 Online 或 OnlineWithAutoUnloader；不能把两种单侧配置都描述成双侧联机。',
            'tr-task-online',
            'tr-output-online',
          ),
          outcome(
            '创建判断',
            '所列任务为空或 Status 不等于 Running 时创建。这里没有统一等待旧任务退出，也没有按配置先清空其他分支已有的任务对象。',
            'tr-belt-create',
            'tr-bin-create',
            'tr-split-task',
            'tr-output-task',
          ),
        ],
      ),
    ],
  ),
  flow(
    'transport-online-feed',
    '送板机进料',
    '送板线程由 PrepareFeeding 门控，控制器在入料段记忆为 NoMaterial 时发出要料请求并检测前端物料。',
    ['tr-task-online', 'tr-online-feed'],
    [
      step(
        'permit',
        '等待上料准备',
        '每轮先调用 WaitStart；PrepareFeeding 为 false 时等待 1000 毫秒再进入下一轮，不调用送板控制器。',
        ['tr-task-online'],
      ),
      step(
        'request',
        '要料与前端检测',
        '入料段为 NoMaterial 时打开要料输出并计时。前端检测到物料后启动入料皮带，延时后关要料输出，再停止皮带。已有物料时直接关要料输出并返回 NoStart。',
        ['tr-online-feed'],
        [
          outcome(
            '超过 5000 毫秒',
            '先置 Alarm 并关要料输出；重试重新要料并计时，终止返回 Abort，不再上料设置 ContinuousFeeding=false 并返回 NoStart。',
            'tr-online-feed',
          ),
        ],
      ),
      step(
        'finish',
        '提交入料状态',
        '控制器尾部写 HasMaterial、创建 System2 类型的 TransportUnit 并保存，然后返回 Success。线程在 Success 时清 PrepareFeeding；Abort 调用 Stop；该 switch 没有 Exception 分支。',
        ['tr-online-feed', 'tr-task-online'],
      ),
    ],
  ),
  flow(
    'transport-belt-feed',
    '皮带进入 S1',
    '非 None 且非 LoaderBin 创建皮带进入 S1 的任务；先处理首次启动的已有物料，再按 ContinuousFeeding 调用传输控制器。',
    ['tr-belt-create', 'tr-belt-first', 'tr-belt-run'],
    [
      step(
        'first',
        '处理已有物料',
        '不启用重启提示时，首次发现 S1 有料便发完成信号，仍继续本轮后续判断；启用提示时首次处理后一定 continue，有料且选 Yes 发信号，选 No 调用 Stop。',
        ['tr-belt-first'],
      ),
      step(
        'gates',
        '检查上料与占用',
        'ContinuousFeeding=false 时等待下一轮。控制器发现 S1 已有料便返回 NoStart；仅 Online 额外检查入料段记忆，无料时返回 NoStart。缺少皮带数据时，重试回方法的 retry，终止返回 Abort，忽略继续后续代码。',
        ['tr-belt-run', 'tr-belt-gate'],
      ),
      step(
        'sense',
        '检测入料与 S1 传输',
        '先并行调用挡料与 UnClamp，等待后启动入料皮带；运动中检测入料段物料并在需要时创建载具对象，随后启动 S1 皮带检测 S1 物料。',
        ['tr-belt-in', 'tr-belt-dispense'],
        [
          outcome(
            '入料未检测到',
            '自动路径可重新上料、关闭 ContinuousFeeding 后返回 NoStart，或终止返回 Abort；手动路径直接返回 None。',
            'tr-belt-in',
          ),
          outcome(
            'S1 卡料',
            '重试回 retry，终止返回 Abort，忽略只退出报警 switch。S1 未检测到的 Ignore 路径不会进入 else 中的物料提交，但仍可到方法尾部返回 Success。',
            'tr-belt-dispense',
            'tr-belt-commit',
          ),
        ],
      ),
      step(
        'commit',
        '提交与发布信号',
        '进入 S1 检测到物料的 else 后，停止入料皮带，按 S1 配置 Clamp，移交 TransportUnit，更新两段物料和 Ready 状态，置 IsTuInDispense1=true。线程在 Success 发 S1 完成信号并清 PrepareFeeding。',
        ['tr-belt-commit', 'tr-belt-run'],
        [
          outcome(
            '未配置 S1 的放行位置',
            'AllowDispenseTransferToBondSignal.Set 位于结果 switch 之后，因此未配置 S1 时，NoStart、Abort 或未处理的返回码也可能走到这个放行语句。',
            'tr-belt-run',
          ),
          outcome(
            '异常',
            '控制器捕获异常返回 Exception；线程结果 switch 没有 Exception 分支，线程自己的 catch 仅显示异常。',
            'tr-belt-commit',
            'tr-belt-run',
          ),
        ],
      ),
    ],
  ),
  flow(
    'transport-bin-feed',
    '料仓推入 S1',
    'LoaderBin 任务在首次已有物料处理和 ContinuousFeeding 判断后，等待 LoaderAllowPushSignal，再调用推料控制器。',
    ['tr-bin-create', 'tr-bin-first', 'tr-bin-run'],
    [
      step(
        'permit',
        '等待料仓允许推料',
        '首次物料提示与皮带任务相同：关闭重启提示时直接发已有物料信号；启用提示时首轮处理后 continue。持续上料关闭时等待；推料信号 Wait=false 则退出任务。',
        ['tr-bin-first', 'tr-bin-run'],
      ),
      step(
        'push',
        '推杆回位与推料',
        'S1 有料返回 NoStart。否则调用挡料与 UnClamp；RePush 先 MovePushRodHome 再 PushTabletToDispenseNoWait，res 被后一次调用覆盖，随后按推料结果分支。',
        ['tr-bin-push'],
        [
          outcome(
            '推料结果非 Success',
            '重试清推杆错误、上使能后回 RePush；忽略继续；下一片返回 None；终止返回 Abort；不再上料关闭 ContinuousFeeding 并返回 NoStart。',
            'tr-bin-push',
          ),
          outcome(
            '推到位却未检测到入口物料',
            '循环内发现推杆到位时先回位，再提供同组处理选项。此处 Ignore 只退出 switch，仍留在检测循环；不是直接宣布入料完成。',
            'tr-bin-detect',
          ),
        ],
      ),
      step(
        'belt',
        'S1 皮带传输与入口复查',
        '入口检测通过后另起推杆回位任务，最多循环检测 10000 毫秒；S1 皮带 MoveBeltWaitArrive 返回后复查入口。有料则置 NoMaterial/Alarm，重试回 RePush、终止返回 Abort、不再上料返回 NoStart。',
        ['tr-bin-belt'],
        [
          outcome(
            '卡料后忽略',
            'Ignore 跳过无卡料 else 中的载具创建和状态提交，仍可到尾部返回 Success；不要把返回码解释成此处完成了全部提交。',
            'tr-bin-belt',
            'tr-bin-commit',
          ),
        ],
      ),
      step(
        'handshake',
        '提交与请求下一层',
        '无卡料 else 中 Clamp，创建或刷新 System1 载具，写 HasMaterial、Ready 和第一段位置，并等待回位 Task。线程收到 Success 发 S1 完成信号并清 PrepareFeeding；Success 或 None 后复位允许推料，发 AllowLoaderMoveSignal。',
        ['tr-bin-commit', 'tr-bin-run'],
        [
          outcome(
            'NoStart',
            '等待 500 毫秒后 continue，保留允许推料信号，不请求料仓换层。',
            'tr-bin-run',
          ),
          outcome(
            'Abort / Exception',
            '调用 Stop 并 return，不执行后面的信号复位与允许移动。',
            'tr-bin-run',
          ),
        ],
      ),
    ],
  ),
];
