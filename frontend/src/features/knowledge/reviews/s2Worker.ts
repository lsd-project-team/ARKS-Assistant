import { choices, flow, outcome, step } from './builders.ts';

// 返回枚举、操作员选择和实际抛出异常分别描述，避免合并成统一失败出口。
export const s2WorkerFlows = [
  flow(
    's2-task-entry',
    'S2 线程入口与准备门控',
    'Machine.Start 先调用 S2 消息初始化，再调用 BondTask.Start；Start 返回 true 表示调用返回，未等待线程完成或汇总线程内结果。',
    ['working-state', 's2-worker-start'],
    [
      step(
        'start',
        '按任务状态创建线程',
        'BondWorkTask 为空或 Status 不等于 Running 时用 LongRunning、CancellationToken.None 启动 DoWork。条件没有分别排除其他尚未结束的状态；AbortThread 当前为空，没有在这里实现取消或唤醒。',
        ['s2-worker-start', 'abort-s2'],
      ),
      step(
        'reset',
        '重置运行字段，等待开始',
        'DoWork 先 ResetInformation，再进入外层 WaitStart。重置包括首启、重取、蘸胶、跳过次数和接触力等运行字段，未重建 WorkMessages，也未清空焊点步骤字典。',
        ['s2-worker-entry', 's2-runtime-reset'],
      ),
      step(
        'prepare',
        '先调用安全位和焊头清零',
        '每次外层 WaitStart 通过后依次 MoveShelfToHome、MoveToSafePos、ResetBondhead，随后查首个芯片。三个调用在本层 Enable 判断之前，调用返回值未被消费；具体子方法的模式门控需另行阅读。',
        ['s2-worker-entry', 's2-first-component'],
      ),
      step(
        'nozzle',
        '条件满足才提前换吸嘴',
        'Enable、IsChangeNozzleAdvance 和 component 非空同时满足才检查是否需要换吸嘴。ChangeNozzle 返回 false 时 Stop 并退出线程；旁边提前向供晶发要料信号的旧代码已注释。',
        ['s2-worker-nozzle'],
        [
          outcome(
            '实际异常',
            'DoWork 没有包围整段的 try / catch / finally；未被内部方法处理的异常可使 Task 故障，不会自动沿返回枚举的清理路径执行。',
            's2-worker-entry',
            's2-worker-results',
            's2-worker-finish',
          ),
        ],
      ),
    ],
  ),
  choices(
    's2-incoming',
    '来料、补偿与步骤注入',
    '来料检查、界面刷新、三个补偿调用和步骤注入都在 Enable 生产动作判断之前；Enable 为 false 不等于这些入口全部跳过。',
    ['s2-worker-incoming', 's2-worker-inject'],
    [
      step(
        'online',
        '补偿模式或流道来料',
        'GetIncomingSignal 在补偿模式直接返回 true；配置流道时等待 TransferToBondFinishedSignal，返回值直接交给外层判断。外层收到 false 直接退出，没有在这个判断处再调用 Stop。',
        ['s2-incoming-online', 's2-worker-incoming'],
      ),
      step(
        'manual',
        '无流道的人工来料',
        '当前载具非空则继续；为空时提示放入产品。确认后调用 MapBelt(true)，不消费其返回值，改查载具是否已生成；仍为空或选择停止会调用 Stop 并返回 false。',
        ['s2-incoming-manual'],
      ),
      step(
        'compensate',
        '刷新后依次执行补偿入口',
        '先调用 ReFreshSystem2TuAction，再依次取片温漂视觉补偿、System2TemperatureCompensation、ScanReferencePoints，任一返回 false 就直接退出。这里未统一追加 Stop，也没有把子方法 true 写成现场校正已验收。',
        ['s2-worker-incoming'],
      ),
      step(
        'inject',
        '注入步骤，必要时替换载具',
        '补偿模式先创建“测试”载具，然后 InjectSteps 并置 IsFirstDispense=true。Enable 为 true、配置流道且载具不是产品时，替换为 System2 新载具并置 IsProduct=true；新载具构造的 Init 自身也注入 S2 和 S1 步骤。',
        ['s2-worker-inject', 's2-tu-construct', 's2-tu-init'],
        [
          outcome(
            '步骤保留',
            'InjectSteps 只给匹配焊点添加不存在的步骤键，并赋 false；已有键和值保留，重复注入不是清空完成状态。',
            's2-inject-steps',
          ),
        ],
      ),
    ],
  ),
  choices(
    's2-results',
    '动作结果与两种重试入口',
    '内层循环先 WaitStart，再 GetNextActionNode；Alarm 对话框重试的标签却在这两步之后。两条重试路径不能画成同一个回环。',
    ['s2-worker-select', 's2-worker-results', 's2-worker-alarm'],
    [
      step(
        'execute',
        '判断是否工作，再调用动作',
        '非空动作先 IsDoWork。为 true 时调用 CloseDispenseCylinder 再 DoWork；该方法只有在 !IsCloseCylinder 时关闭测高气缸。IsDoWork 为 false 会越过结果判断，直接标记当前消息 Finished。',
        ['s2-worker-select', 's2-worker-cylinder', 's2-worker-commit'],
      ),
      step(
        'retry',
        '动作返回 Retry：重新选消息',
        'ExcuteResult.Retry 执行 continue，不完成当前消息，重新经过内层 WaitStart 和 GetNextActionNode。后者从队首找未完成消息，并有连续同名校正动作的异常检查。',
        ['s2-worker-results', 's2-worker-select', 's2-next-message'],
        [
          outcome(
            '并非保证无限重复同一动作',
            '上一动作与下一条未完成消息同名，且名称为 UpLookCorrectionActionNode 或 SubstrateCameraCorrectionActionNode 时，控制器提示排序出错并抛异常。',
            's2-next-message',
          ),
        ],
      ),
      step(
        'alarm',
        'Alarm：终止、重试或忽略',
        '终止先 Stop，再调用焊头安全高度及可选胶盘归位，然后 return。重试 goto RetryCommand，在同一 actionNode 上重新执行 IsDoWork，不再经过本层 WaitStart 或重新选消息；忽略则走消息完成。',
        ['s2-worker-alarm', 's2-worker-select', 's2-worker-commit'],
      ),
      step(
        'finish',
        '哪些结果会标记消息完成',
        'Abort 和 Exception 枚举分支先 Stop，再焊头去安全高度、按配置胶盘归位并退出。Success、Fail 及其他未列入 switch 的返回值会走 FinishCurrentActionNode；没有“所有非 Success 都停止”的统一规则。',
        ['s2-worker-results', 's2-worker-alarm', 's2-worker-commit', 's2-finish-message'],
      ),
    ],
  ),
  choices(
    's2-release',
    '消息复位与载具放行',
    '消息选择返回 null、Enable 为 false，或内层 WaitStart 退出，都可能进入尾部收尾。收尾日志、消息标记与流道移走载具是不同层面的结果。',
    ['s2-worker-select', 's2-worker-inject', 's2-worker-finish'],
    [
      step(
        'finish',
        '安全位后复位消息',
        '尾部先 MoveToSafePos，再 Finish。Finish 将所有消息 Finished 改回 false，并把当前消息指向第 0 项；它没有清除焊点 S2RemainingSteps，也没有重新生成配方消息。空列表没有索引保护。',
        ['s2-worker-finish', 's2-controller-finish'],
      ),
      step(
        'post',
        '归一化补偿与可选保存',
        'Finish 之后记录“整个产品做完”，调用 NormalizationOffset，按配置 SaveEjectionTime，再 SendAway，最后刷新 UI。此处日志不能证明每个业务步骤都执行过；某个调用抛异常可阻断后续放行。',
        ['s2-worker-finish'],
      ),
      step(
        'online',
        '有流道：只发传输许可',
        'SendAway 在配置流道且 IsStop 为 false 时 Set AllowBondTransferToWaitingUnloadSignal。该方法不等待移走确认，也不在这里清空流道载具；已经停止则只记录不发许可。',
        ['s2-send-online'],
        [
          outcome(
            '完成日志的范围',
            '外层 SendAway 返回后仍记录“送走载具完成”，包括其因停止而不发许可的分支，不能据此认定实际送板完成。',
            's2-worker-finish',
            's2-send-online',
          ),
        ],
      ),
      step(
        'manual',
        '无流道：先清软件状态，再提示',
        '未停止时按 AutoSaveMapping 调用保存，随后先将载具置 null、分段状态置 NoMaterial，再提示人工拿走，最后 Stop。解除夹紧调用已注释；这里的状态清除在人工确认前发生。已停止则跳过这段。',
        ['s2-send-manual'],
      ),
    ],
  ),
];
