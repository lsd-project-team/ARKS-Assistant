import { choices, flow, outcome, step } from './builders.ts';

export const waferWorkerFlows = [
  choices(
    'wafer-task-start',
    '供晶线程的创建与退出',
    'Start 是 void 入口；设置 Working 和创建任务不证明这一轮搜晶已经完成。Dowork 捕获异常后先提示，再请求 Stop。',
    ['w-start', 'w-worker-catch'],
    [
      step(
        'create',
        '初始化后创建长运行任务',
        '任务为空或 Status 不是 Running 时，先 Block.StartInit、清 PreviousNeedChipName，再设 Working，以 CancellationToken.None 创建 LongRunning 任务。这里没有取消令牌与完成等待。',
        ['w-start', 'w-block-init'],
      ),
      step(
        'running',
        '已有 Running 任务只更新机器状态',
        '已有 Running 任务不再创建，只 SetStateWorking。Start 自身异常仅弹提示，不向调用者返回成功标志，也没有在 catch 中 Stop。',
        ['w-start'],
      ),
      step(
        'wait',
        '每轮先 WaitStart，再等芯片需求',
        'IsAloneDryCycle 下先延时并自行 Set 需求信号；需求 Wait 返回 false 时回到 WaitBondNeed，重新进入 WaitStart。该返回不是此线程的直接 return。',
        ['w-demand'],
      ),
      step(
        'exit',
        '异常提示与中止方法的边界',
        'Dowork catch 先弹“晶圆线程即将停止”，之后调用 Stop，没有 finally。AbortWaferSubThread 内的 Abort 和置空均被注释，不具备取消当前任务的实现。',
        ['w-worker-catch', 'w-abort'],
      ),
    ],
  ),
  flow(
    'wafer-demand',
    '芯片需求、换料判断与选晶',
    '供晶任务读取当前需求名称，检查载具配置，再按换料标记调用 ChangeTabletAuto 和 NextDie。',
    ['w-carrier', 'w-fail-entry'],
    [
      step(
        'name',
        '校验所需芯片配置',
        'GetCarriers().Exists 判断名称存在后从仓库 Find 并转换配置；不存在直接抛异常。CurrentNeedChipName 的 setter 只是字段赋值，没有在这里建立请求队列或不可变快照。',
        ['w-carrier', 'w-abort'],
      ),
      step(
        'mark',
        '无料片或名称变化时请求换料',
        '当前料片为 NullTablet，或需求名不同于 PreviousNeedChipName，就 SetChangeCarrierSignal。随后 NeedChange 通过 IsNeedChangeCarrier 读取有效换料条件。',
        ['w-carrier', 'w-need-change', 'w-change-flags'],
      ),
      step(
        'change',
        '换料 false 报警后抛异常',
        '需要换料时建立并记录报警；ChangeTabletAuto 返回 false 就记录处理状态再抛异常，true 则记录结束后继续。数据插入和初始化异常也可能进入外层 catch。',
        ['w-carrier'],
      ),
      step(
        'search',
        'NextDie 与上一芯片名的更新',
        'NextDie 为 false 转入专门恢复分支；正常返回 true 后才将当前名称写入 PreviousNeedChipName，这发生在真空准备和可取晶信号之前。',
        ['w-fail-entry', 'w-select-retry', 'w-before-pick'],
      ),
    ],
  ),
  choices(
    'wafer-search-recovery',
    '搜晶失败后回到哪里',
    'NextDie=false 不统一等于换片。首先检查 IsNeedChange，再区分地图、普通料片、空跑及操作员结果。',
    ['w-fail-entry', 'w-select', 'w-select-retry'],
    [
      step(
        'map',
        '地图、空跑及非晶圆料片',
        '需要换料且当前是 WaferTablet 时，WaferMap 直接回 NeedChange；其他搜晶模式在 DryCycle 下也回 NeedChange。需要换料且当前不是 WaferTablet 时同样回 NeedChange。',
        ['w-fail-entry', 'w-select', 'w-select-retry'],
      ),
      step(
        'ok',
        '普通选点提示的 OK',
        '普通料片、非空跑时，通过 VisionAlarmFunc 提示；Single 还显示当前搜索方向。返回 OK 就回 NeedChange，不是在本处直接发送取晶许可。',
        ['w-select'],
      ),
      step(
        'retry',
        'Retry 先核对选点范围',
        '非 Box 且选点在范围外时提示并回 RetrySelectPoint；表达式使用 &，两侧都会求值。通过后清换料标记、将 SlotState 设 Good、经 UI 委托调用设备参数保存，再回 NeedChange。',
        ['w-select-retry', 'ws-box-save', 'w-form-ui'],
      ),
      step(
        'other',
        '不能恢复的结果抛搜晶失败',
        '不需要换料，或操作员结果没有进入 OK / Retry 恢复分支，最终抛“搜晶失败”。后续由 Dowork catch 提示再 Stop，不能把所有报警选择都画成重试。',
        ['w-fail-entry', 'w-select-retry', 'w-worker-catch'],
      ),
    ],
  ),
  flow(
    'wafer-publish',
    '真空准备、发布许可与单独搜晶',
    '搜晶正常返回后准备真空，再复位需料并 Set 可取料。后面的单独空跑刷新、记录与停止均发生在许可发出之后。',
    ['w-before-pick', 'w-publish', 'w-record'],
    [
      step(
        'vacuum',
        '按载具类型准备真空',
        '配置打开真空时，Wafer 开顶针台真空，Waffle 开晶圆台 Waffle 真空，然后执行开真空延时；配置关闭则分别关真空。此 switch 没有 StaticWaffle 的有效 case。',
        ['w-before-pick'],
      ),
      step(
        'permit',
        '先 ReSet 需求，再 Set 可取料',
        '非 Wafer 配置、IsAloneDryCycle 且 StaticWaffle、非 Offline 的分支还会先调用焊头 MoveZ、再 MoveBondXY。之后 ReSet IsBondNeedChipSignal，再 Set IsWaferAllowPickSignal。此处不等待消费者完成取晶。',
        ['w-dry-position', 'w-publish'],
      ),
      step(
        'after',
        '单独搜晶的后续动作',
        'IsAloneDryCycle 下调用 RefreshMap(true) 并增加次数；同时开启记录才匹配固定 PR 并写实验表。成功结果直接读 matchResults[0]，没有此处的空数组保护。IsSearchOne 在这些动作后 Stop。',
        ['w-publish', 'w-record'],
        [
          outcome(
            'true 参数的限制',
            'RefreshMap 的 isDebugMode 参数在该方法体内没有被使用，传 true 不会自行跳过高度等待、顶针准备或地图更新。',
            'w-refresh-height',
            'w-refresh-mode',
          ),
        ],
      ),
    ],
  ),
];
