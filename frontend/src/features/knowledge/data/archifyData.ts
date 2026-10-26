import type { ArchifyData } from '../types';

export const archifyData: ArchifyData = {
  graphs: [
    {
      slug: 'startup-workflow',
      title: '01 · 启动、回零与生产放行',
      nodes: [
        {
          id: 'entry',
          label: '程序入口',
          detail:
            'Mutex 单实例；磁盘不足返回；迁移提示、日志与后台辅助线程；按配置检查授权，失败返回。范围仅主入口外层。',
          signals: [],
        },
        {
          id: 'init',
          label: '非离线初始化',
          detail:
            '仅非离线进入 PR/硬件初始化块；含轴卡与轴设置。catch 记录并弹窗，未直接退出；后续另有 Harmony/视觉事件设置。',
          signals: [],
        },
        {
          id: 'home',
          label: '可选开机回零',
          detail:
            '按 IsAxisResetBeforeWork 调用 AllAxisGoHome；人员取消、回零 false 或捕获异常返回 false。只有成功末段开补偿并置 AllAxisReset；Main 未检查该返回值。',
          signals: [],
        },
        {
          id: 'form',
          label: '主窗体加载',
          detail:
            'Load 事件：非离线且未回零则禁用主区域并立即返回；只有通过且中途无异常才加载数据、初始化界面参数、连接仪器、选灯并启动后台。',
          signals: [],
        },
        {
          id: 'operator',
          label: '点击生产启动',
          detail:
            'ItemClick 事件按配置确认配方；Cancel 返回。关闭手动面板、退出单步后调用 Start；catch 调用 Stop，finally 恢复控件。',
          signals: [],
        },
        {
          id: 'checks',
          label: '启动检查通过？',
          detail:
            'Prepare 先清理文件并复位信号，再检查回零、任务状态、初始化、门与 Working；请求安全位后依次调用各域、产品、焊点和制程检查。false 不代表无副作用；子检查内部不纳入本节点验收。',
          signals: [],
        },
        {
          id: 'working',
          label: '置 Working',
          detail:
            '仅 Prepare 返回 true 后 SetState(Working)；是状态赋值与记录，不是所有任务启动成功的确认。',
          signals: [],
        },
        {
          id: 'dispatch',
          label: '启动并发任务',
          detail:
            '按源码顺序发起输送→供晶→可选 S1→动作初始化→固晶→可选胶盘→可选翻转→两类真空检查；补偿模式跳过部分任务。调用顺序不等于并发任务完成顺序。',
          signals: [],
        },
        {
          id: 'reject',
          label: '取消或检查失败返回',
          detail:
            '配方确认 Cancel 在按钮内返回，或 Prepare false 使 Start 返回；前者不调用 Start，后者可能已发生清理、信号复位及移动请求。',
          signals: [],
        },
        {
          id: 'monitor',
          label: '后台监控与存储',
          detail:
            '仅主窗体加载通过门控后调用；线程不存在或不存活时新建后台线程。ThreadFlag 为真时依次调用门、激光、登出、温度、耗材、扫描与存储入口，再 Sleep(100)，不是固定 100ms 周期。',
          signals: [],
        },
        {
          id: 'stop',
          label: 'Stop 软件停止',
          detail:
            '普通 Stop 改状态、清窗报警、清单步与需晶、按 Online 条件关要料、关顶针吹气真空并清缺陷计数；无统一任务退出等待。详见停机复核。',
          signals: ['IsBondNeedChipSignal'],
        },
        {
          id: 'restart',
          label: '再次点击启动',
          detail:
            '表示操作员再次触发同一个启动按钮事件，不是 Stop 自动调用 Start，也不是 Continue；仍需重新通过启动检查。',
          signals: ['IsBondNeedChipSignal'],
        },
      ],
      validated: true,
      diagnostic: '',
      edges: [
        {
          id: 'entry-init',
          from: 'entry',
          to: 'init',
          label: '非离线才执行',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'init-home',
          from: 'init',
          to: 'home',
          label: '初始化块结束',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'home-form',
          from: 'home',
          to: 'form',
          label: '未检查回零返回值',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'form-operator',
          from: 'form',
          to: 'operator',
          label: '加载放行后人工点击',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'operator-checks',
          from: 'operator',
          to: 'checks',
          label: '确认通过调用 Start',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'checks-working',
          from: 'checks',
          to: 'working',
          label: '通过',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'working-dispatch',
          from: 'working',
          to: 'dispatch',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'checks-reject',
          from: 'checks',
          to: 'reject',
          label: '未通过',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'form-monitor',
          from: 'form',
          to: 'monitor',
          label: '加载未提前返回',
          role: 'async',
          variant: 'dashed',
        },
        {
          id: 'stop-restart',
          from: 'stop',
          to: 'restart',
          label: '操作员再次启动',
          role: 'return',
          variant: 'dashed',
        },
      ],
      cards: [
        {
          dot: 'cyan',
          title: '控制顺序与调用边界',
          items: [
            'Main 创建窗口，Load 由事件触发；生产启动来自按钮 ItemClick。',
            '初始化与开机回零均有配置条件；无条件箭头不代表底层成功。',
          ],
        },
        {
          dot: 'amber',
          title: '就绪检查有副作用',
          items: [
            '清理文件与信号复位发生在检查前；还会请求安全位置。',
            'Prepare false 只使 Start 返回，不能推断之前没有动作。',
          ],
        },
        {
          dot: 'amber',
          title: '完成与未完成范围',
          items: [
            '本章复核外层控制流，非驱动、所有自检或设备运行验收。',
            '100ms 是每轮调用之后休眠；Stop 返回不代表任务均退出。',
          ],
        },
      ],
      reviewDocument: 'startup-semantic-revalidation.md',
    },
    {
      slug: 'transport-workflow',
      title: '02 · 载具输送与上下料',
      nodes: [
        {
          id: 'start',
          label: '输送启动与映射',
          detail:
            '未配置输送返回；Init 后 DryCycle 转模拟入口。普通路径先检查，失败 Stop/return；按配置复位要料/反向刷新，再 MapMaterial。仅 LoadConfiguration==LoaderBin 在这里同时启动两个料仓任务；随后 TransportTask.Start。',
          signals: [
            'AllowDispenseTransferToBondSignal',
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToBondFinishedSignal',
          ],
        },
        {
          id: 'mode',
          label: '上料配置？',
          detail:
            '按同一个 LoadConfiguration 选择：None 只处理 S1 已有料确认；非 LoaderBin 建皮带任务；LoaderBin 建推料任务。在线模式额外建立前端进料任务；各段任务并发，不是一次串行调用。',
          signals: [
            'AllowLoaderMoveSignal',
            'LoaderAllowPushSignal',
            'AllowDispenseTransferToBondSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToDispense2FinishedSignal',
            'TransferToBondFinishedSignal',
            'AllowUnloaderMoveSignal',
            'UnloaderAllowPushSignal',
          ],
        },
        {
          id: 'belt',
          label: '皮带或在线进料',
          detail:
            'Online/OnlineWithAutoLoader 先有独立进料任务：PrepareFeeding 门控，等前端到料；超 5000ms 可重试、终止或不再上料。后续皮带任务调用 TransferLoadBeltToDispense；软件 Success 发 S1 来料，已有料也可直接发。',
          signals: [
            'AllowLoaderMoveSignal',
            'LoaderAllowPushSignal',
            'AllowDispenseTransferToBondSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToDispense2FinishedSignal',
            'TransferToBondFinishedSignal',
            'AllowUnloaderMoveSignal',
            'UnloaderAllowPushSignal',
          ],
        },
        {
          id: 'bin',
          label: '料仓定位与传送',
          detail:
            'LoaderTask 先 MoveToCurrentPlaceLayer、发允许推料；传输任务 Wait LoaderAllowPush 后调用料仓传输，按结果发布来料、复位推料许可、发 AllowLoaderMove；定位任务再 MoveToNextPlaceLayer。未列出的结果与 Ignore 不能解释为物理确认。',
          signals: [
            'AllowLoaderMoveSignal',
            'LoaderAllowPushSignal',
            'AllowDispenseTransferToBondSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToDispense2FinishedSignal',
            'TransferToBondFinishedSignal',
            'AllowUnloaderMoveSignal',
            'UnloaderAllowPushSignal',
          ],
        },
        {
          id: 's1',
          label: 'S1 来料与加工',
          detail:
            '非离线 GetInputSignal 轮询来料 State 并直接赋 ReSet；按 Enable 和动作结果推进，正常结束且未停止才放行。未配置 S1 的皮带旁路在结果 switch 后发放行，并非仅 Success；料仓分支没有对应语句。',
          signals: [
            'AllowLoaderMoveSignal',
            'LoaderAllowPushSignal',
            'AllowDispenseTransferToBondSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToDispense2FinishedSignal',
            'TransferToBondFinishedSignal',
            'AllowUnloaderMoveSignal',
            'UnloaderAllowPushSignal',
          ],
        },
        {
          id: 's2',
          label: '放行并传入 S2',
          detail:
            'S1 有料且 S2 无料才继续，自动模式 Wait S1 放行；成功路径迁移载具、清 S1 并 Save，任务收到 Success 才发 S2 来料。局部 Ignore 也可到 Success；该任务未单列控制器返回 Exception。',
          signals: [
            'AllowLoaderMoveSignal',
            'LoaderAllowPushSignal',
            'AllowDispenseTransferToBondSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToDispense2FinishedSignal',
            'TransferToBondFinishedSignal',
            'AllowUnloaderMoveSignal',
            'UnloaderAllowPushSignal',
          ],
        },
        {
          id: 'wait',
          label: '传入等待下料区',
          detail:
            'Bond SendAway 在已配置输送且未停止时放行；Bond 有料且等待区空，控制器自动 Wait 放行。传输后迁移载具、清 Bond 并 Save；两处 Retry 回不同标签，Ignore 可推进状态；该任务对 Exception 调 Stop。',
          signals: [
            'AllowLoaderMoveSignal',
            'LoaderAllowPushSignal',
            'AllowDispenseTransferToBondSignal',
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToDispense2FinishedSignal',
            'TransferToBondFinishedSignal',
            'AllowUnloaderMoveSignal',
            'UnloaderAllowPushSignal',
          ],
        },
        {
          id: 'out',
          label: '按配置选下料',
          detail:
            '这里仍按 LoadConfiguration 选下料：None 返回；非 LoaderBin 建等待区到出口皮带任务，LoaderBin 建入仓任务。占用/传感器门控因配置不同而异，不可概括成全模式统一互锁。',
          signals: ['AllowUnloaderMoveSignal', 'UnloaderAllowPushSignal'],
        },
        {
          id: 'online',
          label: '联机出口交接',
          detail:
            '仅 Online/OnlineWithAutoUnloader 另启出口交接；等下游要料与出口感应出现/消失，Retry 不重新检查下游要料，Ignore 仍可清对象并 Save。普通 Belt 无此独立下游任务；出口任务未单列 Exception。',
          signals: ['AllowUnloaderMoveSignal', 'UnloaderAllowPushSignal'],
        },
        {
          id: 'unloader',
          label: '下料仓交接',
          detail:
            'Wait UnloaderAllowPush 后传入料仓；控制器清等待区、更新状态、AddCurPlaceLayer 再 Save。任务复位推料许可并发 AllowUnloaderMove；料仓任务再次 MoveToCurrentPlaceLayer。移动/推杆/Save 内部未全部验收。',
          signals: ['AllowUnloaderMoveSignal', 'UnloaderAllowPushSignal'],
        },
        {
          id: 'alarm',
          label: '局部报警处理',
          detail:
            '代表性进料报警：5000ms 超时可 Retry、Abort 或 Ignore；Ignore 实为关闭 ContinuousFeeding 并 NoStart。其他卡料 Ignore 可能继续软件迁移；局部 Retry 标签和 Exception 处理不同，详见复核文档。',
          signals: [
            'AllowLoaderMoveSignal',
            'LoaderAllowPushSignal',
            'AllowDispenseTransferToBondSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToDispense2FinishedSignal',
            'TransferToBondFinishedSignal',
            'AllowUnloaderMoveSignal',
            'UnloaderAllowPushSignal',
          ],
        },
      ],
      validated: true,
      diagnostic: '',
      edges: [
        {
          id: 'start-mode',
          from: 'start',
          to: 'mode',
          label: '普通模式',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'mode-belt',
          from: 'mode',
          to: 'belt',
          label: '非 None / 料仓',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'mode-bin',
          from: 'mode',
          to: 'bin',
          label: '料仓',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'belt-s1',
          from: 'belt',
          to: 's1',
          label: '来料信号',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'bin-s1',
          from: 'bin',
          to: 's1',
          label: '来料信号',
          role: 'main',
          variant: 'default',
        },
        {
          id: 's1-s2',
          from: 's1',
          to: 's2',
          label: '物料与放行条件',
          role: 'main',
          variant: 'default',
        },
        {
          id: 's2-wait',
          from: 's2',
          to: 'wait',
          label: 'S2 放行与空闲',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'wait-out',
          from: 'wait',
          to: 'out',
          label: '等待区有料',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'out-online',
          from: 'out',
          to: 'online',
          label: '联机收板配置',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'out-unloader',
          from: 'out',
          to: 'unloader',
          label: 'LoaderBin',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'belt-alarm',
          from: 'belt',
          to: 'alarm',
          label: '送板超 5 秒',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'alarm-belt',
          from: 'alarm',
          to: 'belt',
          label: '该处选择 Retry',
          role: 'return',
          variant: 'dashed',
        },
      ],
      cards: [
        {
          dot: 'cyan',
          title: '并发与配置边界',
          items: [
            '图线是物料/信号主链，不是一个串行任务。',
            '上下料选择共用 LoadConfiguration；Belt 不等于联机收板。',
            'None、DryCycle 和已有物料复用按源码分支处理。',
          ],
        },
        {
          dot: 'amber',
          title: '软件成功不等于机械确认',
          items: [
            'Ignore 可能仍迁移状态、清对象或递增层号。',
            '各处 Retry 位置与 Exception 处理不同，不能合并成统一恢复。',
            '本图末端是局部交接，任务通常继续等待下一片。',
          ],
        },
      ],
      reviewDocument: 'transport-semantic-revalidation.md',
    },
    {
      slug: 'dispense-workflow',
      title: '03 · S1 配方、点胶与分段交接',
      nodes: [
        {
          id: 'sort',
          label: '生成配方动作',
          detail:
            'Init 清空消息，以启用的 ProcessSteps 和两类排序配置生成；Divide 按 last→Interactive→first 重组，再按异形配置剔除。注册集合与消息顺序不同，八种策略见复核表。',
          signals: [],
        },
        {
          id: 'wait',
          label: '等来料并预点胶',
          detail:
            '非离线才轮询来料：Sleep10，暂停先跳过，再调用预点胶。非 Success 或 Stop 返回 false，调用者安全位后退出且无显式 Stop。Set 直接赋 State=ReSet；未知状态抛异常。离线绕过此等待。',
          signals: ['AllowDispenseTransferToBondSignal', 'TransferToDispense1FinishedSignal'],
        },
        {
          id: 'inject',
          label: '注入焊点步骤',
          detail:
            'Enable=true 才检查 IsProduct、必要时重建载具并 InjectSteps；只对匹配焊点名且缺失的步骤键加入 false，已有值保留。Enable=false 绕过动作进入普通收尾。',
          signals: ['AllowDispenseTransferToBondSignal', 'TransferToDispense1FinishedSignal'],
        },
        {
          id: 'next',
          label: '查未完成动作',
          detail:
            '按顺序找首条未 Finished 消息，以名称在注册 ActionNodes 中 Find。消息耗尽或名称未匹配均可能返回 null，外层均 break；不能把空结果等同产品所有工艺完成。',
          signals: ['AllowDispenseTransferToBondSignal', 'TransferToDispense1FinishedSignal'],
        },
        {
          id: 'gate',
          label: '需要执行？',
          detail:
            '执行 IsDoWork：各动作检查配置、物料状态、已定位/已测高/已识别或剩余步骤，具体条件不相同。false 直接标消息完成；门控异常不在动作 DoWork 的 catch 内。',
          signals: ['AllowDispenseTransferToBondSignal', 'TransferToDispense1FinishedSignal'],
        },
        {
          id: 'work',
          label: '执行当前动作',
          detail:
            '非四类测高且非离线时先收回测高气缸，再 DoWork。定位 bool、分段 Wait 结果被忽略；身份识别离线真正返回，定位/测高/点胶离线不都立即返回。Success 可是跳过或物料禁用。详细动作表及下层边界见复核文档。',
          signals: [
            'AllowDispense1TransferToDispense2Signal',
            'AllowDispenseTransferToBondSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToDispense2FinishedSignal',
          ],
        },
        {
          id: 'result',
          label: '返回结果？',
          detail:
            '仅处理正常返回的 ExcuteResult：Retry continue 重新取首条未完成消息；其他非 Success 走安全位与 Stop 后返回；Success 标当前消息完成。DoWork 外层没有统一 catch，未捕获异常不保证 Stop。',
          signals: ['AllowDispenseTransferToBondSignal', 'TransferToDispense1FinishedSignal'],
        },
        {
          id: 'finish',
          label: '标当前消息完成',
          detail:
            'IsDoWork=false 或返回 Success 调 FinishCurrentActionNode，将当前消息 Finished=true；下一轮仍受 Signal.WaitStart 控制。检测重做可先重置较早消息，物料状态与消息状态不是同一层。',
          signals: ['AllowDispenseTransferToBondSignal', 'TransferToDispense1FinishedSignal'],
        },
        {
          id: 'stop',
          label: '安全位并 Stop',
          detail:
            '动作返回非 Success 且非 Retry，依次请求安全位、调用 Machine.Stop、记录并 return。等料失败只有安全位后 return；抛异常与返回值失败不同，不保证执行此清理链。',
          signals: ['AllowDispenseTransferToBondSignal', 'TransferToDispense1FinishedSignal'],
        },
        {
          id: 'release',
          label: '条件放行与重置',
          detail:
            '退出内循环或 Enable=false 后请求安全位；仅 IsStop=false 发 AllowDispenseTransferToBondSignal。Finish 把所有消息 Finished=false 并清当前指针，随后外层循环；不清空产品全部状态，不代表物料已传走。',
          signals: ['AllowDispenseTransferToBondSignal', 'TransferToDispense1FinishedSignal'],
        },
      ],
      validated: true,
      diagnostic: '',
      edges: [
        {
          id: 'sort-wait',
          from: 'sort',
          to: 'wait',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'wait-inject',
          from: 'wait',
          to: 'inject',
          label: '来料',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'inject-next',
          from: 'inject',
          to: 'next',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'next-gate',
          from: 'next',
          to: 'gate',
          label: '有动作',
          role: 'main',
          variant: 'default',
          fromSide: 'bottom',
        },
        {
          id: 'next-release',
          from: 'next',
          to: 'release',
          label: '空结果',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'gate-work',
          from: 'gate',
          to: 'work',
          label: '是',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'gate-finish',
          from: 'gate',
          to: 'finish',
          label: '否',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'work-result',
          from: 'work',
          to: 'result',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'result-finish',
          from: 'result',
          to: 'finish',
          label: '成功',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'finish-next',
          from: 'finish',
          to: 'next',
          label: '下一步',
          role: 'return',
          variant: 'dashed',
          toSide: 'top',
        },
        {
          id: 'result-next',
          from: 'result',
          to: 'next',
          label: 'Retry',
          role: 'return',
          variant: 'dashed',
        },
        {
          id: 'result-stop',
          from: 'result',
          to: 'stop',
          label: '其他失败',
          role: 'error',
          variant: 'security',
        },
      ],
      cards: [
        {
          dot: 'cyan',
          title: '选择与重做',
          items: [
            '按配置排序；点胶 / 检测映射为 if / else if。',
            '空结果也可能是动作名未匹配；Retry 重取未完成项。',
            '检测可重置早期消息；Fail 也可禁用焊点后返回 Success。',
          ],
        },
        {
          dot: 'amber',
          title: '不可省略的边界',
          items: [
            '等料预点胶失败直接退出；禁用 S1 则绕过动作。',
            '分段 Wait、定位 bool 未检查；异常不保证 Stop。',
            '仅未 Stop 才放行；底层动作与现场结果未全部验收。',
          ],
        },
      ],
      reviewDocument: 'dispense-semantic-revalidation.md',
    },
    {
      slug: 'wafer-supply-workflow',
      title: '04 · 晶圆供料、换料与翻转',
      nodes: [
        {
          id: 'need',
          label: '等待芯片需求',
          detail:
            'StartInit 后启动长期任务；等待共享需求事件。调用方先写芯片名再 Set；单独 DryCycle 可自发需求。',
          signals: ['IsWaferAllowPickSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'valid',
          label: '校验芯片料片',
          detail: '未知名称抛异常；空片或名称变化置换片标志。',
          signals: ['IsWaferAllowPickSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'change',
          label: '需换料？',
          detail: '检查 IsNeedChangeCarrier；为真才调用换片。',
          signals: ['IsWaferAllowPickSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'search',
          label: '按模式搜晶',
          detail: 'Single / Nine / WaferMap / Box。各模式 false 与异常不同，见搜索分支审查。',
          signals: [],
        },
        {
          id: 'found',
          label: '搜晶成功？',
          detail: 'NextDie 的 bool 决定后续；false 仅在特定需换片条件下进入恢复，否则最终抛异常。',
          signals: ['IsWaferAllowPickSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'replace',
          label: '换料与初始化',
          detail:
            'ChangeTabletAuto 的 false 不继续搜索；内部初始化 false 按配置回 Operation 或重开向导，空跑忽略该 bool。外层换片没有直接 Stop 门控。手动窗口先改共享内存再保存/请求运动，取消或失败不作本地回滚；无效名称保留旧 tempTablet。实际控件事件与设备行为未验收。',
          signals: [],
        },
        {
          id: 'retry',
          label: '换片或选点',
          detail:
            '需换片时，Map/DryCycle/非晶圆回检查；普通晶圆人工 OK 回检查，Retry 验范围并复位标志，其他返回抛异常。',
          signals: ['IsWaferAllowPickSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'stop',
          label: '提示后请求停止',
          detail:
            'Dowork catch 先弹窗再调用 Stop；弹窗异常会跳过 Stop。Stop 内先设置状态并写日志队列，入队阻塞/异常可发生在状态变 Stop 之后、其余清理之前。同样接收换片/搜索/准备异常；不是 FlipTask 的统一兜底，也不证明所有线程或输出安全退出。',
          signals: ['IsWaferAllowPickSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'ready',
          label: '发布晶圆就绪',
          detail:
            '搜索 true 后更新名称并准备真空；清需求再 Set 晶圆可取。单次搜索随后 Stop；就绪不是已取走。',
          signals: ['IsWaferAllowPickSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'route',
          label: '翻转取料？',
          detail: '逻辑分支跨任务：直取是否等待仍依相机/StaticWaffle；补偿工作不调用此等待包装。',
          signals: [
            'IsBondPickSucceedSignal',
            'IsWaferAllowPickSignal',
            'IsBondNeedChipSignal',
            'IsFlipTableAllowPickSignal',
          ],
        },
        {
          id: 'flip',
          label: '翻转并发布',
          detail:
            '独立 FlipTask 等晶圆；已有料跳过新取料。Success 置有料；Exception/Abort return，NoStart 重等；发布后等 S2 完成。',
          signals: [
            'IsBondPickSucceedSignal',
            'IsWaferAllowPickSignal',
            'IsBondNeedChipSignal',
            'IsFlipTableAllowPickSignal',
          ],
        },
        {
          id: 'pick',
          label: 'S2 接续',
          detail:
            '等待成功再继续取晶；Pick 成功清翻转有料。后续 Task.Run 分发直取预取或翻转通知；不代表整个生产完成。',
          signals: ['IsWaferAllowPickSignal', 'IsBondNeedChipSignal', 'IsFlipTableAllowPickSignal'],
        },
      ],
      validated: true,
      diagnostic: '',
      edges: [
        {
          id: 'need-valid',
          from: 'need',
          to: 'valid',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'valid-change',
          from: 'valid',
          to: 'change',
          label: '有效',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'change-search',
          from: 'change',
          to: 'search',
          label: '否',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'change-replace',
          from: 'change',
          to: 'replace',
          label: '是',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'replace-search',
          from: 'replace',
          to: 'search',
          label: '返回 true',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'search-found',
          from: 'search',
          to: 'found',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'found-ready',
          from: 'found',
          to: 'ready',
          label: 'true',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'found-retry',
          from: 'found',
          to: 'retry',
          label: 'false 且需换片',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'retry-change',
          from: 'retry',
          to: 'change',
          label: '满足恢复条件',
          role: 'return',
          variant: 'dashed',
        },
        {
          id: 'found-stop',
          from: 'found',
          to: 'stop',
          label: '失败未恢复',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'valid-stop',
          from: 'valid',
          to: 'stop',
          label: '未知芯片',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'ready-route',
          from: 'ready',
          to: 'route',
          label: '信号交接',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'route-pick',
          from: 'route',
          to: 'pick',
          label: '直取条件',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'route-flip',
          from: 'route',
          to: 'flip',
          label: '翻转',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'flip-pick',
          from: 'flip',
          to: 'pick',
          label: '翻转就绪',
          role: 'main',
          variant: 'default',
        },
      ],
      cards: [
        {
          dot: 'cyan',
          title: '跨任务信号交接',
          items: [
            '晶圆就绪由直取等待者或 FlipTask 消费；不是同步函数调用。',
            'S2 接续不等于整机完成；连续生产由下一需求再次触发。',
          ],
        },
        {
          dot: 'amber',
          title: '恢复和退出边界',
          items: [
            '换片 false 按分支重试；空跑忽略初始化结果，Stop 不保证中断。',
            '异常先提示再 Stop；日志入队阻塞或失败可截断停止清理。',
            '窗口先改内存后保存；取消或提交失败没有本地回滚。',
          ],
        },
      ],
      reviewDocument: 'wafer-supply-semantic-revalidation.md',
    },
    {
      slug: 'bonding-workflow',
      title: '05 · S2 配方调度与载具完成',
      nodes: [
        {
          id: 'wait',
          label: '等待 S2 来料',
          detail:
            '先回安全位并可提前换嘴。补偿模式直接通过；有流道等入料信号，无流道检查载具并可能人工放料。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'prepare',
          label: '补偿并注入步骤',
          detail:
            '三项补偿检查 false 直接 return；InjectSteps 只补焊点步骤键。Enable=false 跳过动作循环，仍走收尾。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'next',
          label: '选未完成消息',
          detail:
            '查首个 Finished=false；动作名未匹配也可返回 null。连续同名两类校正消息会抛异常。',
          signals: [],
        },
        {
          id: 'type',
          label: '当前动作类别',
          detail:
            '启动 Init 已编排消息；此处只是当前对象的阅读分组，不是循环内重新生成配方。每个动作先检查 IsDoWork。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'component',
          label: '组件动作序列',
          detail:
            '编排 Pick、UpLook、SubstrateCamera、Bond；翻转时按 DipMode 插入 DipFlux。实际执行可由动作自身条件跳过，内部另章复核。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'inspect',
          label: '检测或点胶消息',
          detail:
            '字段优先级 Component→Defect→Epoxy，后两者生成 AfterBondCheck 或 S2Dispense。不是每次贴片必有检测。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'outcome',
          label: '处理动作返回',
          detail:
            'Retry 重新选未完成；Alarm 人工处理；Abort/Exception 返回值 Stop并局部回退。IsDoWork=false及未单列返回值也会标完成；抛异常无统一catch。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'operator',
          label: '人工处理 Alarm',
          detail:
            'Retry goto 当前动作检查，不经顶部 WaitStart；Ignore标消息完成；Abort Stop和局部回退。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'stop',
          label: 'Stop 后局部回退',
          detail:
            '显式 Abort/Exception 或 Alarm选Abort：Stop→抬Z→按配置收胶盘→return；不是全部异常的finally保证。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'complete',
          label: '收尾并重置消息',
          detail:
            '回安全位、Finish全消息置false、补偿归一化、可选保存顶针时间。Enable=false或内层WaitStart=false也可到此；空消息列表无索引保护。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'release',
          label: '条件放行或取走',
          detail:
            '仅非Stop时：自动Set下料许可；人工可保存Mapping、清载具、提示取走后Stop。许可不是物理传输完成。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'flux',
          label: '胶盘并发任务',
          detail:
            '独立任务等焊头离区后伸出、发允许蘸胶、等蘸胶完成、缩回、等再次允许伸出。超时可人工续等；不是同步配方子调用。',
          signals: ['IsAllowDipFluxSignal', 'BondDipFluxFinishSignal', 'AllowSlideOutSignal'],
        },
      ],
      validated: true,
      diagnostic: '',
      edges: [
        {
          id: 'wait-prepare',
          from: 'wait',
          to: 'prepare',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'prepare-next',
          from: 'prepare',
          to: 'next',
          label: '启用且可运行',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'next-type',
          from: 'next',
          to: 'type',
          label: '非 null',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'type-component',
          from: 'type',
          to: 'component',
          label: '组件',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'type-inspect',
          from: 'type',
          to: 'inspect',
          label: '检测 / 胶',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'component-outcome',
          from: 'component',
          to: 'outcome',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'inspect-outcome',
          from: 'inspect',
          to: 'outcome',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'outcome-next',
          from: 'outcome',
          to: 'next',
          label: '标完成 / Retry',
          role: 'return',
          variant: 'dashed',
        },
        {
          id: 'outcome-operator',
          from: 'outcome',
          to: 'operator',
          label: 'Alarm',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'operator-next',
          from: 'operator',
          to: 'next',
          label: 'Ignore',
          role: 'return',
          variant: 'dashed',
        },
        {
          id: 'operator-stop',
          from: 'operator',
          to: 'stop',
          label: 'Abort',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'outcome-stop',
          from: 'outcome',
          to: 'stop',
          label: 'Abort / Exception',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'next-complete',
          from: 'next',
          to: 'complete',
          label: '返回 null',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'complete-release',
          from: 'complete',
          to: 'release',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'operator-type',
          from: 'operator',
          to: 'type',
          label: 'Retry 同一对象',
          role: 'return',
          variant: 'dashed',
        },
      ],
      cards: [
        {
          dot: 'cyan',
          title: '编排和执行分开理解',
          items: [
            'Init 先按配置编排；图中类别只是已选动作的分组。',
            '每条消息单独执行或跳过；蘸胶插入顺序由翻转与 DipMode 决定。',
          ],
        },
        {
          dot: 'amber',
          title: '收尾不等于全部成功',
          items: [
            'Enable=false、内层 WaitStart=false 也可进入收尾。',
            'Finish 重置消息；无匹配动作也可返回 null；物理下料另由流道执行。',
          ],
        },
        {
          dot: 'amber',
          title: '胶盘独立并发',
          items: [
            '伸出→允许蘸胶→等蘸胶完成→缩回→等再次允许。',
            '区域等待超时可续等；部分 return 没有统一 finally。',
          ],
        },
      ],
      reviewDocument: 'bonding-semantic-revalidation.md',
    },
    {
      slug: 'pickup-workflow',
      title: '06 · 取晶动作与漏晶恢复',
      nodes: [
        {
          id: 'prepare',
          label: '准备芯片吸嘴',
          detail:
            'IsDoWork可跳过；OffLine在try前Success；准备后换嘴/清嘴，DryCycle走独立模拟流程。普通路径取得补偿，再到NextDie。',
          signals: ['IsBondPickSucceedSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'ready',
          label: '条件等待供料',
          detail:
            '非补偿工作调用等待包装；直取仍依相机/载具条件，翻转等翻转就绪。BondCamera移动搜索位后另等晶圆。',
          signals: [
            'IsBondPickSucceedSignal',
            'IsWaferAllowPickSignal',
            'IsBondNeedChipSignal',
            'IsFlipTableAllowPickSignal',
          ],
        },
        {
          id: 'position',
          label: '定位与取前检查',
          detail:
            'StaticWaffle定位可自动跳过或人工Retry；计算补偿位置、移动、启动采集，再查翻转交接位/芯片名。异常与非Success提前返回。',
          signals: ['IsBondPickSucceedSignal', 'IsWaferAllowPickSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'pick',
          label: '执行 Pick',
          detail:
            '补偿工作直接Success；普通路径慢下、吸嘴真空、关平台真空、可选吹气、压力记录、Wafer顶针、延时及条件慢升。异常重抛至主catch。',
          signals: ['IsBondPickSucceedSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'check',
          label: '配置的漏晶检测',
          detail:
            'Usable计数先增加，再按配置检查真空。重检不重取；未启用可直接继续，不能将计数视为已检测合格数。',
          signals: ['IsBondPickSucceedSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'handoff',
          label: '持料标记与通知',
          detail:
            '标记持料并提交预开灯；WaitStart失败返回Abort。通过后异步直取预取或翻转通知，不await，不保证发信号完成。',
          signals: ['IsBondPickSucceedSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'result',
          label: '返回调度结果',
          detail:
            '普通路径Success只代表本次同步流程返回；同步异常转Exception，finally只设动作Stop并WorkStop。异步任务不受这个catch统一处理。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondPickSucceedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'operator',
          label: '人工漏晶处理',
          detail:
            '重检回检测；重取只回Pick；下一颗抛料并走条件通知；Ignore继续；Abort返回。未见统一次数上限。',
          signals: ['IsBondPickSucceedSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'nextdie',
          label: '抛料并请求下一颗',
          detail:
            '直取刷新Map并发当前需求；翻转仅下一名null时补发晶圆需求，但均通知翻转取走。置IsRepickComponent，再回NextDie重新等待定位。',
          signals: ['IsBondPickSucceedSignal', 'IsBondNeedChipSignal'],
        },
        {
          id: 'abort',
          label: '返回 Abort',
          detail:
            '该人工出口只返回Abort，由BondTask Stop和局部回退。其他准备/等待早退也可能Abort，图未逐一重复绘制。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondPickSucceedSignal',
            'IsBondNeedChipSignal',
          ],
        },
      ],
      validated: true,
      diagnostic: '',
      edges: [
        {
          id: 'prepare-ready',
          from: 'prepare',
          to: 'ready',
          label: '普通在线路径',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'ready-position',
          from: 'ready',
          to: 'position',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'position-pick',
          from: 'position',
          to: 'pick',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'pick-check',
          from: 'pick',
          to: 'check',
          label: '正常返回',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'check-handoff',
          from: 'check',
          to: 'handoff',
          label: '通过 / 未启用',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'handoff-result',
          from: 'handoff',
          to: 'result',
          label: '提交后返回',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'check-operator',
          from: 'check',
          to: 'operator',
          label: '漏晶',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'operator-check',
          from: 'operator',
          to: 'check',
          label: '重检',
          role: 'return',
          variant: 'dashed',
        },
        {
          id: 'operator-pick',
          from: 'operator',
          to: 'pick',
          label: '重取原位置',
          role: 'return',
          variant: 'dashed',
        },
        {
          id: 'operator-nextdie',
          from: 'operator',
          to: 'nextdie',
          label: '下一颗',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'nextdie-ready',
          from: 'nextdie',
          to: 'ready',
          label: '回 NextDie',
          role: 'return',
          variant: 'dashed',
        },
        {
          id: 'operator-handoff',
          from: 'operator',
          to: 'handoff',
          label: '忽略',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'operator-abort',
          from: 'operator',
          to: 'abort',
          label: '退出',
          role: 'error',
          variant: 'security',
        },
      ],
      cards: [
        {
          dot: 'cyan',
          title: '重检、重取、下一颗不同',
          items: [
            '重检只测真空；重取跳过定位和取前检查；下一颗重新等待定位。',
            'Ignore继续不能证明实际有料；Usable计数在检测前增加。',
          ],
        },
        {
          dot: 'amber',
          title: '返回不等于通知完成',
          items: [
            '灯光和供料通知均为未await任务，Success不保证通知已完成。',
            'OffLine直接返回；DryCycle独立模拟；同步异常与异步异常分开理解。',
          ],
        },
        {
          dot: 'amber',
          title: '采集生命周期待验证',
          items: [
            '正常停止采集调用被注释；循环共用标志且无直接Stop检查。',
            '已登记静态风险，未运行复现；不将疑点写成已证实故障。',
          ],
        },
      ],
      reviewDocument: 'pickup-semantic-revalidation.md',
    },
    {
      slug: 'bond-action-workflow',
      title: '07 · 固晶动作与回带恢复',
      nodes: [
        {
          id: 'prepare',
          label: '准备并计算固晶位',
          detail:
            'IsDoWork检查焊点和S2步骤。WorkStart在try之前；OffLine标步骤后Success；DryCycle独立模拟。普通路径组合位置/角度/高度补偿。',
          signals: [],
        },
        {
          id: 'move',
          label: '移动到预固晶位',
          detail:
            '普通路径按AbsoluteMove或InterpolationMove选择预固晶移动；非Success直接返回。成功后通知胶盘、记录RealBondPos，再到ReBond。底层轨迹未纳入此次复核。',
          signals: ['BondDipFluxFinishSignal', 'AllowSlideOutSignal'],
        },
        {
          id: 'bond',
          label: '力曲线与 Bond',
          detail:
            'ReBond从力曲线/清零开始；按TU胶印周期选择动作。距离模式条件慢下，力模式进入力控；普通贴片关真空并异步弱吹，再记录压力、条件慢升/退力控。Bond非Success提前返回；正常后尝试导出xlsx，保存异常可递归Retry或放弃。',
          signals: [],
        },
        {
          id: 'check',
          label: '回带检测需处理？',
          detail:
            '普通贴片且开启芯片检测和慢速离开才检查回带；hasMaterial取检测反值。异步关真空不被主同步catch等待。条件不满足不等于检测合格。',
          signals: [],
        },
        {
          id: 'finish',
          label: '胶印检查与步骤收尾',
          detail:
            '可选TU胶印视觉：Ignore→Fail→禁用焊点→包装Success；成功则再次Bond。随后计胶印次数、可选人工视觉等待、清持料、S2步骤字典置true、统计/耗材/上限。人工视觉遇Stop只退出等待，调用者仍继续收尾；步骤完成不是质量通过。',
          signals: ['BondDipFluxFinishSignal', 'AllowSlideOutSignal'],
        },
        {
          id: 'return',
          label: '收尾返回 Success',
          detail:
            '普通收尾返回Success；预移动/Bond/胶印可提前返回；同步try异常返回Exception。finally只置State=Stop并发WorkStop；异步任务和入口事件不在同一异常保障内。外层BondTask解释结果，本节点不表示设备已安全复位。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'choice',
          label: '回带报警选择',
          detail:
            '回带报警四选项：Retry局部重贴；Abort计失败并返回；Ignore抛料后继续；Cancel抛料并重置相关消息、返回Retry。没有在这里设置人工重试次数上限。',
          signals: [],
        },
        {
          id: 'repick',
          label: '重置动作返回 Retry',
          detail:
            'Cancel计失败与Reject、抛料；重置Pick、配置对应校正和Bond消息，置IsRepickComponent并返回Retry；不是整个动作表重置。',
          signals: [],
        },
        {
          id: 'throw',
          label: '抛料并计失败',
          detail: 'Ignore计失败、抛料后仍进入后续胶印/收尾。控制流Success不证明此次贴装成功。',
          signals: [],
        },
        {
          id: 'stop',
          label: '返回 Abort',
          detail:
            'Abort计失败后返回Abort，由外层BondTask处理停机；不能把这个动作返回等同所有硬件都已安全停止。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
      ],
      validated: true,
      diagnostic:
        '本轮Archify九项检查通过；Edge桌面自动检查通过；已目视1440×900浅色截图。仅限展示验收。',
      edges: [
        {
          id: 'prepare-move',
          from: 'prepare',
          to: 'move',
          label: '普通路径',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'move-bond',
          from: 'move',
          to: 'bond',
          label: '移动成功',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'bond-check',
          from: 'bond',
          to: 'check',
          label: 'Bond成功',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'check-finish',
          from: 'check',
          to: 'finish',
          label: '无需处理',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'finish-return',
          from: 'finish',
          to: 'return',
          label: '收尾完成',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'check-choice',
          from: 'check',
          to: 'choice',
          label: '芯片回带',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'choice-bond',
          from: 'choice',
          to: 'bond',
          label: '重贴',
          role: 'return',
          variant: 'dashed',
        },
        {
          id: 'choice-repick',
          from: 'choice',
          to: 'repick',
          label: '重新取贴',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'choice-throw',
          from: 'choice',
          to: 'throw',
          label: '忽略',
          role: 'branch',
          variant: 'default',
        },
        {
          id: 'throw-finish',
          from: 'throw',
          to: 'finish',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'choice-stop',
          from: 'choice',
          to: 'stop',
          label: '终止',
          role: 'error',
          variant: 'security',
        },
      ],
      cards: [
        {
          dot: 'cyan',
          title: '重贴与重新取贴',
          items: ['Retry回ReBond，不重算位置或通知胶盘。', 'Cancel重置指定消息，返回Retry交调度。'],
        },
        {
          dot: 'amber',
          title: 'Success不是质量判定',
          items: ['胶印忽略可禁用焊点后仍返回Success。', '离线/空跑、提前返回及异常见源码复核。'],
        },
      ],
      reviewDocument: 'bond-action-semantic-revalidation.md',
    },
    {
      slug: 'failure-recovery-workflow',
      title: '08 · 暂停、重试、停止与线程边界',
      nodes: [
        {
          id: 'ret',
          label: '动作执行与结果分类',
          detail:
            '分别执行S1/S2动作并处理返回。S1除Retry/Success外尝试安全位再Stop；S2仅Abort/Exception/Alarm有特定分支，未列返回值可落到FinishCurrentActionNode。抛出的异常不等于返回Exception枚举；这些DoWork没有统一顶层catch。',
          signals: [
            'AllowDispenseTransferToBondSignal',
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'retry',
          label: 'Retry保留未完成',
          detail:
            '动作返回Retry执行continue，保留当前消息未完成并在循环顶部重新WaitStart、选消息；具体动作可将较早指定消息置false，不能泛化为固定回退。',
          signals: [
            'AllowDispenseTransferToBondSignal',
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'alarm',
          label: 'S2 Alarm人工选择',
          detail:
            'Alarm弹框：Retry直接goto RetryCommand，同一个actionNode重新IsDoWork，不回到循环顶部WaitStart或重新选择；Ignore落到标当前消息完成；Abort执行Stop、抬Z、条件收胶盘后返回。',
          signals: [
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'next',
          label: '继续消息选择',
          detail:
            '动作Retry通过循环顶部再选未完成消息；S2 Alarm Ignore先标当前消息完成，再选下一条。动作不需要执行时也可标消息完成；这是调度完成，不能当质量通过。',
          signals: [
            'AllowDispenseTransferToBondSignal',
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'door',
          label: '门监控或人工暂停',
          detail:
            '后台按ThreadFlag循环调用门监控。配置安全门且Working且门未关才Pause；自动关门恢复分支为注释。人工Pause直接改状态。监控线程其他任务或弹窗可能影响下一次检查时机。',
          signals: ['IsBondNeedChipSignal'],
        },
        {
          id: 'pause',
          label: '状态改为Pause',
          detail:
            'Pause仅SetState(Pause)，并通过SetState登记变更队列。协作检查点WaitStart等待；已经进入Wait事件循环时不每轮查Pause，不能声称轴立即停或全任务挂起。',
          signals: ['IsBondNeedChipSignal'],
        },
        {
          id: 'continue',
          label: '人工Continue',
          detail:
            '不配置门则直接Working；配置门且未关只提示；门关时先设两套IsFirstDispense=true再Working。方法未检查必须从Pause调用，也不重新创建任务；UI门控另行验证。',
          signals: ['IsBondNeedChipSignal'],
        },
        {
          id: 'running',
          label: '存活任务可继续',
          detail:
            '仅在仍存活、正在等待的任务进入对应检查点时可恢复。Loader/Unloader外层while(IsWorking)，若Pause时重新判断可能退出；Continue不会重建。料仓catch只弹窗，不能作为统一停机策略。',
          signals: [
            'AllowLoaderMoveSignal',
            'LoaderAllowPushSignal',
            'AllowUnloaderMoveSignal',
            'UnloaderAllowPushSignal',
            'IsBondNeedChipSignal',
          ],
        },
        {
          id: 'fault',
          label: 'Stop或指定故障',
          detail:
            '直接Stop或已追踪晶圆catch、编码器false返回可进入停止。环境/算法/捕获通讯异常返回false；光强不佳提示不直接返回false，不能泛称所有编码器报警都会Stop。',
          signals: ['IsBondNeedChipSignal'],
        },
        {
          id: 'emergency',
          label: '急停请求轴停止',
          detail:
            'Parallel.ForEach请求axis.StopMove(false,true)完成调用后执行Stop，再依次调用S1/Bond/晶圆Abort。Bond和晶圆Abort无实际终止；S1仅Dispose。前序抛异常可能阻断后序；无设备退出确认。',
          signals: ['IsBondNeedChipSignal'],
        },
        {
          id: 'stop',
          label: 'Stop与指定清理',
          detail:
            '置Stop、异步清登记弹窗、停止报警、关单步、复位需晶信号、仅Online关要料、关顶针吹气/真空、清焊后缺陷计数；没有统一try/finally或Join。不等于所有输出/轴停止。',
          signals: ['IsBondNeedChipSignal'],
        },
        {
          id: 'exit',
          label: '检查点退出待确认',
          detail:
            'Stop只能让相应协作检查返回false；调用方需检查返回且实际走到检查点。普通Stop没有统一Join/取消确认；S1/S2可在循环退出后继续局部收尾。底层运动、阻塞、异步线程是否结束未运行验收。',
          signals: [
            'AllowDispenseTransferToBondSignal',
            'AllowBondTransferToWaitingUnloadSignal',
            'TransferToDispense1FinishedSignal',
            'TransferToBondFinishedSignal',
            'IsBondNeedChipSignal',
          ],
        },
      ],
      validated: true,
      diagnostic:
        '九项Archify检查与Edge桌面检查通过，已目视1440×900浅色截图并修复重试与终止路线重叠；非设备安全验收。',
      edges: [
        {
          id: 'ret-retry',
          from: 'ret',
          to: 'retry',
          label: 'Retry',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'retry-next',
          from: 'retry',
          to: 'next',
          label: '重新取未完成',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'ret-alarm',
          from: 'ret',
          to: 'alarm',
          label: 'S2 Alarm',
          role: 'branch',
          variant: 'default',
          fromSide: 'top',
          toSide: 'top',
        },
        {
          id: 'alarm-next',
          from: 'alarm',
          to: 'next',
          label: 'Ignore标完成',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'alarm-stop',
          from: 'alarm',
          to: 'stop',
          label: 'Abort',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'ret-stop',
          from: 'ret',
          to: 'stop',
          label: '任务定义的终止',
          role: 'error',
          variant: 'security',
        },
        {
          id: 'door-pause',
          from: 'door',
          to: 'pause',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'pause-continue',
          from: 'pause',
          to: 'continue',
          label: '请求继续',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'continue-running',
          from: 'continue',
          to: 'running',
          label: '门条件通过',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'fault-stop',
          from: 'fault',
          to: 'stop',
          label: '',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'emergency-stop',
          from: 'emergency',
          to: 'stop',
          label: '轴停止请求后',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'stop-exit',
          from: 'stop',
          to: 'exit',
          label: '仅对应检查点',
          role: 'main',
          variant: 'default',
        },
        {
          id: 'alarm-ret',
          from: 'alarm',
          to: 'ret',
          label: 'Retry同动作',
          role: 'return',
          variant: 'dashed',
          fromSide: 'bottom',
          toSide: 'bottom',
          channelY: 172,
        },
      ],
      cards: [
        {
          dot: 'cyan',
          title: '两种Retry不可混同',
          items: [
            '动作Retry重选消息；Alarm Retry直接重做当前动作。',
            'Ignore标调度完成，不代表动作质量合格。',
          ],
        },
        {
          dot: 'amber',
          title: '状态不是退出确认',
          items: [
            'Pause/Continue不统一挂起或重建任务。',
            '普通Stop和Abort方法都不能证明所有线程退出。',
          ],
        },
      ],
      reviewDocument: 'failure-recovery-semantic-revalidation.md',
    },
  ],
  signals: {
    System2SingleStepSignal: {
      name: 'System2SingleStepSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'WaitSingleStep',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'WaitSingleStep',
        },
      ],
    },
    System1SingleStepSignal: {
      name: 'System1SingleStepSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'WaitSingleStep',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
      ],
    },
    AllowLoaderMoveSignal: {
      name: 'AllowLoaderMoveSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'ReSet',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Set',
        },
      ],
    },
    LoaderAllowPushSignal: {
      name: 'LoaderAllowPushSignal',
      resetMode: 'ManualReset',
      references: [
        {
          operation: 'ReSet',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'ReSet',
        },
      ],
    },
    AllowDispense1TransferToDispense2Signal: {
      name: 'AllowDispense1TransferToDispense2Signal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Set',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Wait',
        },
      ],
    },
    AllowDispenseTransferToBondSignal: {
      name: 'AllowDispenseTransferToBondSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Set',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Wait',
        },
      ],
    },
    AllowBondTransferToWaitingUnloadSignal: {
      name: 'AllowBondTransferToWaitingUnloadSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Set',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Wait',
        },
      ],
    },
    AllowWaitingUnloadTransferToOutloadSignal: {
      name: 'AllowWaitingUnloadTransferToOutloadSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'ReSet',
        },
      ],
    },
    TransferToDispense1FinishedSignal: {
      name: 'TransferToDispense1FinishedSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'State / 属性',
        },
        {
          operation: 'State / 属性',
        },
        {
          operation: 'State / 属性',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
      ],
    },
    TransferToDispense2FinishedSignal: {
      name: 'TransferToDispense2FinishedSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Wait',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Set',
        },
      ],
    },
    TransferToBondFinishedSignal: {
      name: 'TransferToBondFinishedSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Wait',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
      ],
    },
    AllowUnloaderMoveSignal: {
      name: 'AllowUnloaderMoveSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'ReSet',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Wait',
        },
      ],
    },
    UnloaderAllowPushSignal: {
      name: 'UnloaderAllowPushSignal',
      resetMode: 'ManualReset',
      references: [
        {
          operation: 'ReSet',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
      ],
    },
    IsBondPickSucceedSignal: {
      name: 'IsBondPickSucceedSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Wait',
        },
      ],
    },
    IsWaferAllowPickSignal: {
      name: 'IsWaferAllowPickSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Wait',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Set',
        },
      ],
    },
    IsBondNeedChipSignal: {
      name: 'IsBondNeedChipSignal',
      resetMode: 'ManualReset',
      references: [
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'ReSet',
        },
      ],
    },
    IsBondNeedEjectionSignal: {
      name: 'IsBondNeedEjectionSignal',
      resetMode: 'AutoReset',
      references: [],
    },
    IsEjectionComplete: {
      name: 'IsEjectionComplete',
      resetMode: 'AutoReset',
      references: [],
    },
    IsLoadWaferMap: {
      name: 'IsLoadWaferMap',
      resetMode: 'AutoReset',
      references: [],
    },
    IsFlipTableAllowPickSignal: {
      name: 'IsFlipTableAllowPickSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Wait',
        },
        {
          operation: 'ReSet',
        },
        {
          operation: 'Set',
        },
      ],
    },
    IsAllowDipFluxSignal: {
      name: 'IsAllowDipFluxSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Wait',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'ReSet',
        },
      ],
    },
    BondDipFluxFinishSignal: {
      name: 'BondDipFluxFinishSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'ReSet',
        },
      ],
    },
    AllowSlideOutSignal: {
      name: 'AllowSlideOutSignal',
      resetMode: 'AutoReset',
      references: [
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Set',
        },
        {
          operation: 'Wait',
        },
        {
          operation: 'ReSet',
        },
      ],
    },
  },
  reviewSummary: {
    nodeIds: [
      'startup-workflow/entry',
      'startup-workflow/init',
      'startup-workflow/home',
      'startup-workflow/form',
      'startup-workflow/operator',
      'startup-workflow/checks',
      'startup-workflow/working',
      'startup-workflow/dispatch',
      'startup-workflow/reject',
      'startup-workflow/monitor',
      'startup-workflow/stop',
      'startup-workflow/restart',
      'transport-workflow/start',
      'transport-workflow/mode',
      'transport-workflow/belt',
      'transport-workflow/bin',
      'transport-workflow/s1',
      'transport-workflow/s2',
      'transport-workflow/wait',
      'transport-workflow/out',
      'transport-workflow/online',
      'transport-workflow/unloader',
      'transport-workflow/alarm',
      'dispense-workflow/sort',
      'dispense-workflow/wait',
      'dispense-workflow/inject',
      'dispense-workflow/next',
      'dispense-workflow/gate',
      'dispense-workflow/work',
      'dispense-workflow/result',
      'dispense-workflow/finish',
      'dispense-workflow/stop',
      'dispense-workflow/release',
      'wafer-supply-workflow/need',
      'wafer-supply-workflow/valid',
      'wafer-supply-workflow/change',
      'wafer-supply-workflow/search',
      'wafer-supply-workflow/found',
      'wafer-supply-workflow/replace',
      'wafer-supply-workflow/retry',
      'wafer-supply-workflow/stop',
      'wafer-supply-workflow/ready',
      'wafer-supply-workflow/route',
      'wafer-supply-workflow/flip',
      'wafer-supply-workflow/pick',
      'bonding-workflow/wait',
      'bonding-workflow/prepare',
      'bonding-workflow/next',
      'bonding-workflow/type',
      'bonding-workflow/component',
      'bonding-workflow/inspect',
      'bonding-workflow/outcome',
      'bonding-workflow/operator',
      'bonding-workflow/stop',
      'bonding-workflow/complete',
      'bonding-workflow/release',
      'bonding-workflow/flux',
      'pickup-workflow/prepare',
      'pickup-workflow/ready',
      'pickup-workflow/position',
      'pickup-workflow/pick',
      'pickup-workflow/check',
      'pickup-workflow/handoff',
      'pickup-workflow/result',
      'pickup-workflow/operator',
      'pickup-workflow/nextdie',
      'pickup-workflow/abort',
      'bond-action-workflow/prepare',
      'bond-action-workflow/move',
      'bond-action-workflow/bond',
      'bond-action-workflow/check',
      'bond-action-workflow/finish',
      'bond-action-workflow/return',
      'bond-action-workflow/choice',
      'bond-action-workflow/repick',
      'bond-action-workflow/throw',
      'bond-action-workflow/stop',
      'failure-recovery-workflow/ret',
      'failure-recovery-workflow/retry',
      'failure-recovery-workflow/alarm',
      'failure-recovery-workflow/next',
      'failure-recovery-workflow/door',
      'failure-recovery-workflow/pause',
      'failure-recovery-workflow/continue',
      'failure-recovery-workflow/running',
      'failure-recovery-workflow/fault',
      'failure-recovery-workflow/emergency',
      'failure-recovery-workflow/stop',
      'failure-recovery-workflow/exit',
    ],
    edgeIds: [
      'startup-workflow/entry-init',
      'startup-workflow/init-home',
      'startup-workflow/home-form',
      'startup-workflow/form-operator',
      'startup-workflow/operator-checks',
      'startup-workflow/checks-working',
      'startup-workflow/working-dispatch',
      'startup-workflow/checks-reject',
      'startup-workflow/form-monitor',
      'startup-workflow/stop-restart',
      'transport-workflow/start-mode',
      'transport-workflow/mode-belt',
      'transport-workflow/mode-bin',
      'transport-workflow/belt-s1',
      'transport-workflow/bin-s1',
      'transport-workflow/s1-s2',
      'transport-workflow/s2-wait',
      'transport-workflow/wait-out',
      'transport-workflow/out-online',
      'transport-workflow/out-unloader',
      'transport-workflow/belt-alarm',
      'transport-workflow/alarm-belt',
      'dispense-workflow/sort-wait',
      'dispense-workflow/wait-inject',
      'dispense-workflow/inject-next',
      'dispense-workflow/next-gate',
      'dispense-workflow/next-release',
      'dispense-workflow/gate-work',
      'dispense-workflow/gate-finish',
      'dispense-workflow/work-result',
      'dispense-workflow/result-finish',
      'dispense-workflow/finish-next',
      'dispense-workflow/result-next',
      'dispense-workflow/result-stop',
      'wafer-supply-workflow/need-valid',
      'wafer-supply-workflow/valid-change',
      'wafer-supply-workflow/change-search',
      'wafer-supply-workflow/change-replace',
      'wafer-supply-workflow/replace-search',
      'wafer-supply-workflow/search-found',
      'wafer-supply-workflow/found-ready',
      'wafer-supply-workflow/found-retry',
      'wafer-supply-workflow/retry-change',
      'wafer-supply-workflow/found-stop',
      'wafer-supply-workflow/valid-stop',
      'wafer-supply-workflow/ready-route',
      'wafer-supply-workflow/route-pick',
      'wafer-supply-workflow/route-flip',
      'wafer-supply-workflow/flip-pick',
      'bonding-workflow/wait-prepare',
      'bonding-workflow/prepare-next',
      'bonding-workflow/next-type',
      'bonding-workflow/type-component',
      'bonding-workflow/type-inspect',
      'bonding-workflow/component-outcome',
      'bonding-workflow/inspect-outcome',
      'bonding-workflow/outcome-next',
      'bonding-workflow/outcome-operator',
      'bonding-workflow/operator-next',
      'bonding-workflow/operator-stop',
      'bonding-workflow/outcome-stop',
      'bonding-workflow/next-complete',
      'bonding-workflow/complete-release',
      'bonding-workflow/operator-type',
      'pickup-workflow/prepare-ready',
      'pickup-workflow/ready-position',
      'pickup-workflow/position-pick',
      'pickup-workflow/pick-check',
      'pickup-workflow/check-handoff',
      'pickup-workflow/handoff-result',
      'pickup-workflow/check-operator',
      'pickup-workflow/operator-check',
      'pickup-workflow/operator-pick',
      'pickup-workflow/operator-nextdie',
      'pickup-workflow/nextdie-ready',
      'pickup-workflow/operator-handoff',
      'pickup-workflow/operator-abort',
      'bond-action-workflow/prepare-move',
      'bond-action-workflow/move-bond',
      'bond-action-workflow/bond-check',
      'bond-action-workflow/check-finish',
      'bond-action-workflow/finish-return',
      'bond-action-workflow/check-choice',
      'bond-action-workflow/choice-bond',
      'bond-action-workflow/choice-repick',
      'bond-action-workflow/choice-throw',
      'bond-action-workflow/throw-finish',
      'bond-action-workflow/choice-stop',
      'failure-recovery-workflow/ret-retry',
      'failure-recovery-workflow/retry-next',
      'failure-recovery-workflow/ret-alarm',
      'failure-recovery-workflow/alarm-next',
      'failure-recovery-workflow/alarm-stop',
      'failure-recovery-workflow/ret-stop',
      'failure-recovery-workflow/door-pause',
      'failure-recovery-workflow/pause-continue',
      'failure-recovery-workflow/continue-running',
      'failure-recovery-workflow/fault-stop',
      'failure-recovery-workflow/emergency-stop',
      'failure-recovery-workflow/stop-exit',
      'failure-recovery-workflow/alarm-ret',
    ],
  },
  resourceLinks: [
    {
      href: 'action-catalog-binary-reference-audit.json',
      label: 'action catalog binary reference audit',
    },
    {
      href: 'action-catalog-binary-reference-review.md',
      label: 'action catalog binary reference review',
    },
    {
      href: 'action-controller-audit.json',
      label: 'action controller audit',
    },
    {
      href: 'action-controller-current-progress.json',
      label: 'action controller current progress',
    },
    {
      href: 'action-controller-current-review.md',
      label: 'action controller current review',
    },
    {
      href: 'action-controller-review.md',
      label: 'action controller review',
    },
    {
      href: 'action-controller-test.json',
      label: 'action controller test',
    },
    {
      href: 'action-sort-audit.json',
      label: 'action sort audit',
    },
    {
      href: 'action-sort-current-progress.json',
      label: 'action sort current progress',
    },
    {
      href: 'action-sort-current-review.md',
      label: 'action sort current review',
    },
    {
      href: 'action-sort-review.md',
      label: 'action sort review',
    },
    {
      href: 'action-sort-test.json',
      label: 'action sort test',
    },
    {
      href: 'after-bond-offline-extension-progress.json',
      label: 'after bond offline extension progress',
    },
    {
      href: 'after-bond-offline-extension-review.md',
      label: 'after bond offline extension review',
    },
    {
      href: 'all-project-source-build-audit.json',
      label: 'all project source build audit',
    },
    {
      href: 'all-project-source-build-progress.json',
      label: 'all project source build progress',
    },
    {
      href: 'all-project-source-build-review.md',
      label: 'all project source build review',
    },
    {
      href: 'all-project-source-build-test.json',
      label: 'all project source build test',
    },
    {
      href: 'all-project-source-compatibility-progress.json',
      label: 'all project source compatibility progress',
    },
    {
      href: 'all-project-source-compatibility-review.md',
      label: 'all project source compatibility review',
    },
    {
      href: 'application-entry-module-review.md',
      label: 'application entry module review',
    },
    {
      href: 'artifact-manifest.json',
      label: 'artifact manifest',
    },
    {
      href: 'assistant-predispense-gates-current-progress.json',
      label: 'assistant predispense gates current progress',
    },
    {
      href: 'assistant-predispense-gates-current-review.md',
      label: 'assistant predispense gates current review',
    },
    {
      href: 'assistant-predispense-gates-test.json',
      label: 'assistant predispense gates test',
    },
    {
      href: 'async-db-consumer-test.json',
      label: 'async db consumer test',
    },
    {
      href: 'async-notification-exception-review.md',
      label: 'async notification exception review',
    },
    {
      href: 'async-notification-il-audit.json',
      label: 'async notification il audit',
    },
    {
      href: 'async-notification-il-review.md',
      label: 'async notification il review',
    },
    {
      href: 'async-notification-task-lifecycle-audit.json',
      label: 'async notification task lifecycle audit',
    },
    {
      href: 'async-notification-task-lifecycle-review.md',
      label: 'async notification task lifecycle review',
    },
    {
      href: 'async-notification-write-surface-audit.json',
      label: 'async notification write surface audit',
    },
    {
      href: 'async-notification-write-surface-review.md',
      label: 'async notification write surface review',
    },
    {
      href: 'async-persistence-dataflow.archify.json',
      label: 'async persistence dataflow.archify',
    },
    {
      href: 'async-persistence-dataflow.html',
      label: 'async persistence dataflow',
    },
    {
      href: 'async-persistence-dataflow.visual-check.html',
      label: 'async persistence dataflow.visual check',
    },
    {
      href: 'async-persistence-dataflow.visual-check.json',
      label: 'async persistence dataflow.visual check',
    },
    {
      href: 'async-persistence-ingress-review.md',
      label: 'async persistence ingress review',
    },
    {
      href: 'async-persistence-ingress.json',
      label: 'async persistence ingress',
    },
    {
      href: 'authorization-background-source-review.md',
      label: 'authorization background source review',
    },
    {
      href: 'autofocus-alternatives-review.md',
      label: 'autofocus alternatives review',
    },
    {
      href: 'autofocus-alternatives-test.json',
      label: 'autofocus alternatives test',
    },
    {
      href: 'autofocus-entry-evidence.json',
      label: 'autofocus entry evidence',
    },
    {
      href: 'autofocus-entry-review.md',
      label: 'autofocus entry review',
    },
    {
      href: 'autofocus-module-review.md',
      label: 'autofocus module review',
    },
    {
      href: 'automation-entrypoint-matrix.md',
      label: 'automation entrypoint matrix',
    },
    {
      href: 'automation-sequence.archify.json',
      label: 'automation sequence.archify',
    },
    {
      href: 'automation-sequence.html',
      label: 'automation sequence',
    },
    {
      href: 'automation-signal-matrix.md',
      label: 'automation signal matrix',
    },
    {
      href: 'automation-source-analysis.md',
      label: 'automation source analysis',
    },
    {
      href: 'automation-traceability.json',
      label: 'automation traceability',
    },
    {
      href: 'automation-traceability.md',
      label: 'automation traceability',
    },
    {
      href: 'automation-workflow-summary.md',
      label: 'automation workflow summary',
    },
    {
      href: 'automation-workflow.archify.json',
      label: 'automation workflow.archify',
    },
    {
      href: 'automation-workflow.html',
      label: 'automation workflow',
    },
    {
      href: 'axis-compensate-module-review.md',
      label: 'axis compensate module review',
    },
    {
      href: 'axis-fit-scale-current-progress.json',
      label: 'axis fit scale current progress',
    },
    {
      href: 'axis-fit-scale-current-review.md',
      label: 'axis fit scale current review',
    },
    {
      href: 'axis-fit-scale-review.md',
      label: 'axis fit scale review',
    },
    {
      href: 'axis-fit-scale-test.json',
      label: 'axis fit scale test',
    },
    {
      href: 'axis-numeric-current-progress.json',
      label: 'axis numeric current progress',
    },
    {
      href: 'axis-numeric-current-review.md',
      label: 'axis numeric current review',
    },
    {
      href: 'axis-numeric-test.json',
      label: 'axis numeric test',
    },
    {
      href: 'axis-relative-command-pending-evidence.json',
      label: 'axis relative command pending evidence',
    },
    {
      href: 'axis-relative-contract-evidence.json',
      label: 'axis relative contract evidence',
    },
    {
      href: 'axis-return-transfer-audit.json',
      label: 'axis return transfer audit',
    },
    {
      href: 'axis-return-transfer-current-progress.json',
      label: 'axis return transfer current progress',
    },
    {
      href: 'axis-return-transfer-current-review.md',
      label: 'axis return transfer current review',
    },
    {
      href: 'axis-return-transfer-integration-verification.json',
      label: 'axis return transfer integration verification',
    },
    {
      href: 'axis-return-transfer-review.md',
      label: 'axis return transfer review',
    },
    {
      href: 'axis-return-transfer-test.json',
      label: 'axis return transfer test',
    },
    {
      href: 'background-edit-audit.json',
      label: 'background edit audit',
    },
    {
      href: 'background-edit-test.json',
      label: 'background edit test',
    },
    {
      href: 'background-lifecycle-workflow-evidence.json',
      label: 'background lifecycle workflow evidence',
    },
    {
      href: 'background-lifecycle-workflow.archify.json',
      label: 'background lifecycle workflow.archify',
    },
    {
      href: 'background-lifecycle-workflow.html',
      label: 'background lifecycle workflow',
    },
    {
      href: 'background-lifecycle-workflow.visual-check.html',
      label: 'background lifecycle workflow.visual check',
    },
    {
      href: 'background-lifecycle-workflow.visual-check.json',
      label: 'background lifecycle workflow.visual check',
    },
    {
      href: 'background-monitor-audit.json',
      label: 'background monitor audit',
    },
    {
      href: 'background-monitor-review.md',
      label: 'background monitor review',
    },
    {
      href: 'background-monitor-test.json',
      label: 'background monitor test',
    },
    {
      href: 'background-task-binary-evidence.json',
      label: 'background task binary evidence',
    },
    {
      href: 'background-task-contract-review.md',
      label: 'background task contract review',
    },
    {
      href: 'background-task-sequence.archify.json',
      label: 'background task sequence.archify',
    },
    {
      href: 'background-task-sequence.html',
      label: 'background task sequence',
    },
    {
      href: 'background-task-sequence.visual-check.html',
      label: 'background task sequence.visual check',
    },
    {
      href: 'background-task-sequence.visual-check.json',
      label: 'background task sequence.visual check',
    },
    {
      href: 'bin-configuration-selection-review.md',
      label: 'bin configuration selection review',
    },
    {
      href: 'bin-configuration-sequence.archify.json',
      label: 'bin configuration sequence.archify',
    },
    {
      href: 'bin-configuration-sequence.delivery.json',
      label: 'bin configuration sequence.delivery',
    },
    {
      href: 'bin-configuration-sequence.html',
      label: 'bin configuration sequence',
    },
    {
      href: 'bin-configuration-sequence.review.json',
      label: 'bin configuration sequence.review',
    },
    {
      href: 'bin-configuration-sequence.validation.json',
      label: 'bin configuration sequence.validation',
    },
    {
      href: 'bin-configuration-sequence.visual-check.html',
      label: 'bin configuration sequence.visual check',
    },
    {
      href: 'bin-configuration-sequence.visual-check.json',
      label: 'bin configuration sequence.visual check',
    },
    {
      href: 'bin-failure-handshake-recovery-review.md',
      label: 'bin failure handshake recovery review',
    },
    {
      href: 'bin-failure-handshake-sequence.archify.json',
      label: 'bin failure handshake sequence.archify',
    },
    {
      href: 'bin-failure-handshake-sequence.html',
      label: 'bin failure handshake sequence',
    },
    {
      href: 'bin-failure-handshake-sequence.review.json',
      label: 'bin failure handshake sequence.review',
    },
    {
      href: 'bin-failure-handshake-sequence.visual-check.html',
      label: 'bin failure handshake sequence.visual check',
    },
    {
      href: 'bin-failure-handshake-sequence.visual-check.json',
      label: 'bin failure handshake sequence.visual check',
    },
    {
      href: 'bin-layer-motion-persistence-review.md',
      label: 'bin layer motion persistence review',
    },
    {
      href: 'bin-missing-configuration-audit.json',
      label: 'bin missing configuration audit',
    },
    {
      href: 'bin-missing-configuration-current-progress.json',
      label: 'bin missing configuration current progress',
    },
    {
      href: 'bin-missing-configuration-current-review.md',
      label: 'bin missing configuration current review',
    },
    {
      href: 'bin-missing-configuration-review.md',
      label: 'bin missing configuration review',
    },
    {
      href: 'bin-missing-configuration-test.json',
      label: 'bin missing configuration test',
    },
    {
      href: 'bin-repository-lookup-audit.json',
      label: 'bin repository lookup audit',
    },
    {
      href: 'bin-repository-lookup-current-progress.json',
      label: 'bin repository lookup current progress',
    },
    {
      href: 'bin-repository-lookup-current-review.md',
      label: 'bin repository lookup current review',
    },
    {
      href: 'bin-repository-lookup-test.json',
      label: 'bin repository lookup test',
    },
    {
      href: 'bin-stop-resume-source-review.md',
      label: 'bin stop resume source review',
    },
    {
      href: 'bin-transfer-controller-source-review.md',
      label: 'bin transfer controller source review',
    },
    {
      href: 'bond-action-review-evidence.json',
      label: 'bond action review evidence',
    },
    {
      href: 'bond-action-semantic-revalidation.md',
      label: 'bond action semantic revalidation',
    },
    {
      href: 'bond-action-workflow.archify.json',
      label: 'bond action workflow.archify',
    },
    {
      href: 'bond-action-workflow.browser-check.json',
      label: 'bond action workflow.browser check',
    },
    {
      href: 'bond-action-workflow.delivery.json',
      label: 'bond action workflow.delivery',
    },
    {
      href: 'bond-action-workflow.html',
      label: 'bond action workflow',
    },
    {
      href: 'bond-action-workflow.visual-check.html',
      label: 'bond action workflow.visual check',
    },
    {
      href: 'bond-action-workflow.visual-check.json',
      label: 'bond action workflow.visual check',
    },
    {
      href: 'bond-camera-calibration-diagram-status.json',
      label: 'bond camera calibration diagram status',
    },
    {
      href: 'bond-camera-calibration-evidence.json',
      label: 'bond camera calibration evidence',
    },
    {
      href: 'bond-camera-calibration-review.md',
      label: 'bond camera calibration review',
    },
    {
      href: 'bond-camera-calibration-workflow.archify.json',
      label: 'bond camera calibration workflow.archify',
    },
    {
      href: 'bond-camera-calibration-workflow.html',
      label: 'bond camera calibration workflow',
    },
    {
      href: 'bond-camera-calibration-workflow.visual-check.html',
      label: 'bond camera calibration workflow.visual check',
    },
    {
      href: 'bond-camera-calibration-workflow.visual-check.json',
      label: 'bond camera calibration workflow.visual check',
    },
    {
      href: 'bond-config-native-source-audit.json',
      label: 'bond config native source audit',
    },
    {
      href: 'bond-config-native-source-current-progress.json',
      label: 'bond config native source current progress',
    },
    {
      href: 'bond-config-native-source-current-review.md',
      label: 'bond config native source current review',
    },
    {
      href: 'bond-config-native-source-progress.json',
      label: 'bond config native source progress',
    },
    {
      href: 'bond-config-native-source-review.md',
      label: 'bond config native source review',
    },
    {
      href: 'bond-config-native-source-test.json',
      label: 'bond config native source test',
    },
    {
      href: 'bond-inspection-readiness-audit.json',
      label: 'bond inspection readiness audit',
    },
    {
      href: 'bond-inspection-readiness-current-progress.json',
      label: 'bond inspection readiness current progress',
    },
    {
      href: 'bond-inspection-readiness-current-review.md',
      label: 'bond inspection readiness current review',
    },
    {
      href: 'bond-inspection-readiness-preparation-progress.json',
      label: 'bond inspection readiness preparation progress',
    },
    {
      href: 'bond-inspection-readiness-test.json',
      label: 'bond inspection readiness test',
    },
    {
      href: 'bond-motion-single-step-source-review.md',
      label: 'bond motion single step source review',
    },
    {
      href: 'bond-system-module-review.md',
      label: 'bond system module review',
    },
    {
      href: 'bond-transport-failure-handshake-review.md',
      label: 'bond transport failure handshake review',
    },
    {
      href: 'bonding-review-evidence.json',
      label: 'bonding review evidence',
    },
    {
      href: 'bonding-semantic-revalidation.md',
      label: 'bonding semantic revalidation',
    },
    {
      href: 'bonding-workflow.archify.json',
      label: 'bonding workflow.archify',
    },
    {
      href: 'bonding-workflow.browser-check.json',
      label: 'bonding workflow.browser check',
    },
    {
      href: 'bonding-workflow.delivery.json',
      label: 'bonding workflow.delivery',
    },
    {
      href: 'bonding-workflow.html',
      label: 'bonding workflow',
    },
    {
      href: 'bonding-workflow.visual-check.html',
      label: 'bonding workflow.visual check',
    },
    {
      href: 'bonding-workflow.visual-check.json',
      label: 'bonding workflow.visual check',
    },
    {
      href: 'build-dependency-inventory.md',
      label: 'build dependency inventory',
    },
    {
      href: 'business-branch-coverage.md',
      label: 'business branch coverage',
    },
    {
      href: 'calibration-coordinate-persistence-evidence.json',
      label: 'calibration coordinate persistence evidence',
    },
    {
      href: 'calibration-coordinate-persistence-review.md',
      label: 'calibration coordinate persistence review',
    },
    {
      href: 'calibration-dependency-contract-evidence.json',
      label: 'calibration dependency contract evidence',
    },
    {
      href: 'calibration-dependency-contract-review.md',
      label: 'calibration dependency contract review',
    },
    {
      href: 'calibration-execution-workflow-evidence.json',
      label: 'calibration execution workflow evidence',
    },
    {
      href: 'calibration-execution-workflow-evidence.md',
      label: 'calibration execution workflow evidence',
    },
    {
      href: 'calibration-execution-workflow.archify.json',
      label: 'calibration execution workflow.archify',
    },
    {
      href: 'calibration-execution-workflow.delivery.json',
      label: 'calibration execution workflow.delivery',
    },
    {
      href: 'calibration-execution-workflow.html',
      label: 'calibration execution workflow',
    },
    {
      href: 'calibration-execution-workflow.visual-check.html',
      label: 'calibration execution workflow.visual check',
    },
    {
      href: 'calibration-execution-workflow.visual-check.json',
      label: 'calibration execution workflow.visual check',
    },
    {
      href: 'calibration-height-motion-source-review.md',
      label: 'calibration height motion source review',
    },
    {
      href: 'calibration-module-review.md',
      label: 'calibration module review',
    },
    {
      href: 'calibration-parameter-pr-evidence.json',
      label: 'calibration parameter pr evidence',
    },
    {
      href: 'calibration-parameter-pr-review.md',
      label: 'calibration parameter pr review',
    },
    {
      href: 'calibration-stop-coverage-evidence.json',
      label: 'calibration stop coverage evidence',
    },
    {
      href: 'calibration-stop-coverage-review.md',
      label: 'calibration stop coverage review',
    },
    {
      href: 'calibration-task-analysis.md',
      label: 'calibration task analysis',
    },
    {
      href: 'calibration-task-entry-current-progress.json',
      label: 'calibration task entry current progress',
    },
    {
      href: 'calibration-task-entry-current-review.md',
      label: 'calibration task entry current review',
    },
    {
      href: 'calibration-task-lifecycle-evidence.json',
      label: 'calibration task lifecycle evidence',
    },
    {
      href: 'calibration-task-lifecycle-review.md',
      label: 'calibration task lifecycle review',
    },
    {
      href: 'calibration-task-workflow.archify.json',
      label: 'calibration task workflow.archify',
    },
    {
      href: 'calibration-task-workflow.html',
      label: 'calibration task workflow',
    },
    {
      href: 'calibration-tool-dependency-audit.json',
      label: 'calibration tool dependency audit',
    },
    {
      href: 'calibration-tool-module-review.md',
      label: 'calibration tool module review',
    },
    {
      href: 'callsite-evidence.json',
      label: 'callsite evidence',
    },
    {
      href: 'camera-calibration-source-review.md',
      label: 'camera calibration source review',
    },
    {
      href: 'carrier-change-evidence.json',
      label: 'carrier change evidence',
    },
    {
      href: 'carrier-change-review.md',
      label: 'carrier change review',
    },
    {
      href: 'catalog-init-sdk-audit.json',
      label: 'catalog init sdk audit',
    },
    {
      href: 'catalog-init-sdk-progress.json',
      label: 'catalog init sdk progress',
    },
    {
      href: 'catalog-init-sdk-review.md',
      label: 'catalog init sdk review',
    },
    {
      href: 'catalog-init-sdk-test.json',
      label: 'catalog init sdk test',
    },
    {
      href: 'change-json-module-review.md',
      label: 'change json module review',
    },
    {
      href: 'changejson-assets-review.md',
      label: 'changejson assets review',
    },
    {
      href: 'changejson-assets.json',
      label: 'changejson assets',
    },
    {
      href: 'changejson-files-review.md',
      label: 'changejson files review',
    },
    {
      href: 'changejson-files-test.json',
      label: 'changejson files test',
    },
    {
      href: 'changejson-reflection-review.md',
      label: 'changejson reflection review',
    },
    {
      href: 'changejson-reflection-test.json',
      label: 'changejson reflection test',
    },
    {
      href: 'changejson-update-test.json',
      label: 'changejson update test',
    },
    {
      href: 'common-types-module-review.md',
      label: 'common types module review',
    },
    {
      href: 'compensation-production-source-review.md',
      label: 'compensation production source review',
    },
    {
      href: 'compile-scope-impact.md',
      label: 'compile scope impact',
    },
    {
      href: 'completeness-audit.md',
      label: 'completeness audit',
    },
    {
      href: 'component-code-mapping-review.md',
      label: 'component code mapping review',
    },
    {
      href: 'component-demo-module-review.md',
      label: 'component demo module review',
    },
    {
      href: 'config-edit-consistency-review.md',
      label: 'config edit consistency review',
    },
    {
      href: 'config-production-gates-browser-check.json',
      label: 'config production gates browser check',
    },
    {
      href: 'config-production-gates.html',
      label: 'config production gates',
    },
    {
      href: 'config-production-gates.json',
      label: 'config production gates',
    },
    {
      href: 'config-production-gates.md',
      label: 'config production gates',
    },
    {
      href: 'config-rename-test.json',
      label: 'config rename test',
    },
    {
      href: 'config-submit-reload-review.md',
      label: 'config submit reload review',
    },
    {
      href: 'config-submit-test.json',
      label: 'config submit test',
    },
    {
      href: 'configuration-persistence-source-review.md',
      label: 'configuration persistence source review',
    },
    {
      href: 'coordinate-lifecycle-audit.json',
      label: 'coordinate lifecycle audit',
    },
    {
      href: 'coordinate-lifecycle-current-progress.json',
      label: 'coordinate lifecycle current progress',
    },
    {
      href: 'coordinate-lifecycle-current-review.md',
      label: 'coordinate lifecycle current review',
    },
    {
      href: 'coordinate-lifecycle-test.json',
      label: 'coordinate lifecycle test',
    },
    {
      href: 'coordinate-native-source-audit.json',
      label: 'coordinate native source audit',
    },
    {
      href: 'coordinate-native-source-progress.json',
      label: 'coordinate native source progress',
    },
    {
      href: 'coordinate-native-source-review.md',
      label: 'coordinate native source review',
    },
    {
      href: 'coordinate-native-source-test.json',
      label: 'coordinate native source test',
    },
    {
      href: 'coordinate-product-lifecycle-preparation-progress.json',
      label: 'coordinate product lifecycle preparation progress',
    },
    {
      href: 'coordinate-system-module-review.md',
      label: 'coordinate system module review',
    },
    {
      href: 'current-monitor-evidence-status.md',
      label: 'current monitor evidence status',
    },
    {
      href: 'curve-geometry-audit.json',
      label: 'curve geometry audit',
    },
    {
      href: 'curve-geometry-test.json',
      label: 'curve geometry test',
    },
    {
      href: 'cycle-config-audit.json',
      label: 'cycle config audit',
    },
    {
      href: 'cycle-config-review.md',
      label: 'cycle config review',
    },
    {
      href: 'cycle-config-test.json',
      label: 'cycle config test',
    },
    {
      href: 'data-lifecycle-source-review.md',
      label: 'data lifecycle source review',
    },
    {
      href: 'delegate-provenance-audit.json',
      label: 'delegate provenance audit',
    },
    {
      href: 'delegate-provenance-progress.json',
      label: 'delegate provenance progress',
    },
    {
      href: 'delegate-provenance-review.md',
      label: 'delegate provenance review',
    },
    {
      href: 'delegate-provenance-test.json',
      label: 'delegate provenance test',
    },
    {
      href: 'dependency-audit-verification.md',
      label: 'dependency audit verification',
    },
    {
      href: 'diagram-structure-audit.md',
      label: 'diagram structure audit',
    },
    {
      href: 'dispatch-source-reader-audit.json',
      label: 'dispatch source reader audit',
    },
    {
      href: 'dispatch-source-reader-progress.json',
      label: 'dispatch source reader progress',
    },
    {
      href: 'dispatch-source-reader-review.md',
      label: 'dispatch source reader review',
    },
    {
      href: 'dispatch-source-reader-test.json',
      label: 'dispatch source reader test',
    },
    {
      href: 'dispense-background-edit-review.md',
      label: 'dispense background edit review',
    },
    {
      href: 'dispense-config-consumption-workflow.archify.json',
      label: 'dispense config consumption workflow.archify',
    },
    {
      href: 'dispense-config-consumption-workflow.html',
      label: 'dispense config consumption workflow',
    },
    {
      href: 'dispense-config-consumption-workflow.review.json',
      label: 'dispense config consumption workflow.review',
    },
    {
      href: 'dispense-config-consumption-workflow.visual-check.html',
      label: 'dispense config consumption workflow.visual check',
    },
    {
      href: 'dispense-config-consumption-workflow.visual-check.json',
      label: 'dispense config consumption workflow.visual check',
    },
    {
      href: 'dispense-curve-geometry-review.md',
      label: 'dispense curve geometry review',
    },
    {
      href: 'dispense-draw-edit-review.md',
      label: 'dispense draw edit review',
    },
    {
      href: 'dispense-driver-consumption-review.md',
      label: 'dispense driver consumption review',
    },
    {
      href: 'dispense-driver-lifecycle-review.md',
      label: 'dispense driver lifecycle review',
    },
    {
      href: 'dispense-editor-bridge-review.md',
      label: 'dispense editor bridge review',
    },
    {
      href: 'dispense-mode-lifecycle-review.md',
      label: 'dispense mode lifecycle review',
    },
    {
      href: 'dispense-motion-source-review.md',
      label: 'dispense motion source review',
    },
    {
      href: 'dispense-mouse-edit-review.md',
      label: 'dispense mouse edit review',
    },
    {
      href: 'dispense-node-audit.json',
      label: 'dispense node audit',
    },
    {
      href: 'dispense-node-current-progress.json',
      label: 'dispense node current progress',
    },
    {
      href: 'dispense-node-current-review.md',
      label: 'dispense node current review',
    },
    {
      href: 'dispense-node-failure-review.md',
      label: 'dispense node failure review',
    },
    {
      href: 'dispense-node-test.json',
      label: 'dispense node test',
    },
    {
      href: 'dispense-parameter-roundtrip-review.md',
      label: 'dispense parameter roundtrip review',
    },
    {
      href: 'dispense-pattern-editor-source-review.md',
      label: 'dispense pattern editor source review',
    },
    {
      href: 'dispense-pattern-roundtrip-review.md',
      label: 'dispense pattern roundtrip review',
    },
    {
      href: 'dispense-pretreatment-review.md',
      label: 'dispense pretreatment review',
    },
    {
      href: 'dispense-repository-delete-review.md',
      label: 'dispense repository delete review',
    },
    {
      href: 'dispense-review-evidence.json',
      label: 'dispense review evidence',
    },
    {
      href: 'dispense-semantic-revalidation.md',
      label: 'dispense semantic revalidation',
    },
    {
      href: 'dispense-system-module-review.md',
      label: 'dispense system module review',
    },
    {
      href: 'dispense-transform-select-review.md',
      label: 'dispense transform select review',
    },
    {
      href: 'dispense-workflow.archify.json',
      label: 'dispense workflow.archify',
    },
    {
      href: 'dispense-workflow.delivery.json',
      label: 'dispense workflow.delivery',
    },
    {
      href: 'dispense-workflow.html',
      label: 'dispense workflow',
    },
    {
      href: 'dispense-workflow.visual-check.html',
      label: 'dispense workflow.visual check',
    },
    {
      href: 'dispense-workflow.visual-check.json',
      label: 'dispense workflow.visual check',
    },
    {
      href: 'door-task-pause-audit.json',
      label: 'door task pause audit',
    },
    {
      href: 'door-task-pause-current-progress.json',
      label: 'door task pause current progress',
    },
    {
      href: 'door-task-pause-current-review.md',
      label: 'door task pause current review',
    },
    {
      href: 'door-task-pause-integration-verification.json',
      label: 'door task pause integration verification',
    },
    {
      href: 'door-task-pause-review.md',
      label: 'door task pause review',
    },
    {
      href: 'door-task-pause-test.json',
      label: 'door task pause test',
    },
    {
      href: 'draw-edit-audit.json',
      label: 'draw edit audit',
    },
    {
      href: 'draw-edit-test.json',
      label: 'draw edit test',
    },
    {
      href: 'driver-consumption-audit.json',
      label: 'driver consumption audit',
    },
    {
      href: 'driver-consumption-test.json',
      label: 'driver consumption test',
    },
    {
      href: 'driver-lifecycle-audit.json',
      label: 'driver lifecycle audit',
    },
    {
      href: 'driver-lifecycle-test.json',
      label: 'driver lifecycle test',
    },
    {
      href: 'dry-run-task-audit.json',
      label: 'dry run task audit',
    },
    {
      href: 'dry-run-task-current-progress.json',
      label: 'dry run task current progress',
    },
    {
      href: 'dry-run-task-current-review.md',
      label: 'dry run task current review',
    },
    {
      href: 'dry-run-task-integration-verification.json',
      label: 'dry run task integration verification',
    },
    {
      href: 'dry-run-task-review.md',
      label: 'dry run task review',
    },
    {
      href: 'dry-run-task-test.json',
      label: 'dry run task test',
    },
    {
      href: 'editor-bridge-audit.json',
      label: 'editor bridge audit',
    },
    {
      href: 'editor-bridge-test.json',
      label: 'editor bridge test',
    },
    {
      href: 'emergency-abort-audit.json',
      label: 'emergency abort audit',
    },
    {
      href: 'emergency-abort-current-progress.json',
      label: 'emergency abort current progress',
    },
    {
      href: 'emergency-abort-current-review.md',
      label: 'emergency abort current review',
    },
    {
      href: 'emergency-abort-review.md',
      label: 'emergency abort review',
    },
    {
      href: 'emergency-abort-test.json',
      label: 'emergency abort test',
    },
    {
      href: 'emergency-entry-audit.json',
      label: 'emergency entry audit',
    },
    {
      href: 'emergency-entry-current-progress.json',
      label: 'emergency entry current progress',
    },
    {
      href: 'emergency-entry-current-review.md',
      label: 'emergency entry current review',
    },
    {
      href: 'emergency-entry-review.md',
      label: 'emergency entry review',
    },
    {
      href: 'emergency-entry-test.json',
      label: 'emergency entry test',
    },
    {
      href: 'encoding-preserving-resources-audit.json',
      label: 'encoding preserving resources audit',
    },
    {
      href: 'encoding-preserving-resources-progress.json',
      label: 'encoding preserving resources progress',
    },
    {
      href: 'encoding-preserving-resources-review.md',
      label: 'encoding preserving resources review',
    },
    {
      href: 'encoding-preserving-resources-test.json',
      label: 'encoding preserving resources test',
    },
    {
      href: 'epoxy-algorithm-source-review.md',
      label: 'epoxy algorithm source review',
    },
    {
      href: 'epoxy-confirm-test.json',
      label: 'epoxy confirm test',
    },
    {
      href: 'epoxy-list-save-test.json',
      label: 'epoxy list save test',
    },
    {
      href: 'epoxy-name-resolution-test.json',
      label: 'epoxy name resolution test',
    },
    {
      href: 'epoxy-pretreatment-test.json',
      label: 'epoxy pretreatment test',
    },
    {
      href: 'epoxy-template-structure.json',
      label: 'epoxy template structure',
    },
    {
      href: 'epoxy-template.delivery.json',
      label: 'epoxy template.delivery',
    },
    {
      href: 'epoxy-template.evidence.json',
      label: 'epoxy template.evidence',
    },
    {
      href: 'epoxy-template.workflow.archify.json',
      label: 'epoxy template.workflow.archify',
    },
    {
      href: 'epoxy-template.workflow.html',
      label: 'epoxy template.workflow',
    },
    {
      href: 'epoxy-template.workflow.visual-check.html',
      label: 'epoxy template.workflow.visual check',
    },
    {
      href: 'epoxy-template.workflow.visual-check.json',
      label: 'epoxy template.workflow.visual check',
    },
    {
      href: 'external-dependency-audit.json',
      label: 'external dependency audit',
    },
    {
      href: 'external-dependency-audit.md',
      label: 'external dependency audit',
    },
    {
      href: 'failure-recovery-review-evidence.json',
      label: 'failure recovery review evidence',
    },
    {
      href: 'failure-recovery-semantic-revalidation.md',
      label: 'failure recovery semantic revalidation',
    },
    {
      href: 'failure-recovery-workflow.archify.json',
      label: 'failure recovery workflow.archify',
    },
    {
      href: 'failure-recovery-workflow.browser-check.json',
      label: 'failure recovery workflow.browser check',
    },
    {
      href: 'failure-recovery-workflow.delivery.json',
      label: 'failure recovery workflow.delivery',
    },
    {
      href: 'failure-recovery-workflow.html',
      label: 'failure recovery workflow',
    },
    {
      href: 'failure-recovery-workflow.visual-check.html',
      label: 'failure recovery workflow.visual check',
    },
    {
      href: 'failure-recovery-workflow.visual-check.json',
      label: 'failure recovery workflow.visual check',
    },
    {
      href: 'framework-runtime-analysis.md',
      label: 'framework runtime analysis',
    },
    {
      href: 'framework-runtime-architecture.archify.json',
      label: 'framework runtime architecture.archify',
    },
    {
      href: 'framework-runtime-architecture.html',
      label: 'framework runtime architecture',
    },
    {
      href: 'fresh-project-dependencies-audit.json',
      label: 'fresh project dependencies audit',
    },
    {
      href: 'fresh-project-dependencies-progress.json',
      label: 'fresh project dependencies progress',
    },
    {
      href: 'fresh-project-dependencies-review.md',
      label: 'fresh project dependencies review',
    },
    {
      href: 'fresh-project-dependencies-test.json',
      label: 'fresh project dependencies test',
    },
    {
      href: 'full-original-source-build-audit.json',
      label: 'full original source build audit',
    },
    {
      href: 'full-original-source-build-progress.json',
      label: 'full original source build progress',
    },
    {
      href: 'full-original-source-build-review.md',
      label: 'full original source build review',
    },
    {
      href: 'full-original-source-build-test.json',
      label: 'full original source build test',
    },
    {
      href: 'global-calibration-ex-source-review.md',
      label: 'global calibration ex source review',
    },
    {
      href: 'global-calibration-scale-record-source-review.md',
      label: 'global calibration scale record source review',
    },
    {
      href: 'global-calibration-source-review.md',
      label: 'global calibration source review',
    },
    {
      href: 'gugao-command-loop-test.json',
      label: 'gugao command loop test',
    },
    {
      href: 'hardware-product-state-pending-evidence.json',
      label: 'hardware product state pending evidence',
    },
    {
      href: 'heating-host-audit.json',
      label: 'heating host audit',
    },
    {
      href: 'heating-host-integration-verification.json',
      label: 'heating host integration verification',
    },
    {
      href: 'heating-host-review.md',
      label: 'heating host review',
    },
    {
      href: 'heating-host-test.json',
      label: 'heating host test',
    },
    {
      href: 'index.visual-check.json',
      label: 'index.visual check',
    },
    {
      href: 'inspection-repository-json-sdk-evidence.json',
      label: 'inspection repository json sdk evidence',
    },
    {
      href: 'inspection-repository-json-sdk-progress.json',
      label: 'inspection repository json sdk progress',
    },
    {
      href: 'inspection-repository-json-sdk-runtime-audit.json',
      label: 'inspection repository json sdk runtime audit',
    },
    {
      href: 'inspection-repository-json-sdk-runtime-current-progress.json',
      label: 'inspection repository json sdk runtime current progress',
    },
    {
      href: 'inspection-repository-json-sdk-runtime-current-review.md',
      label: 'inspection repository json sdk runtime current review',
    },
    {
      href: 'inspection-repository-json-sdk-runtime-test.json',
      label: 'inspection repository json sdk runtime test',
    },
    {
      href: 'inspection-repository-native-source-audit.json',
      label: 'inspection repository native source audit',
    },
    {
      href: 'inspection-repository-native-source-progress.json',
      label: 'inspection repository native source progress',
    },
    {
      href: 'inspection-repository-native-source-test.json',
      label: 'inspection repository native source test',
    },
    {
      href: 'inspection-repository-preparation-audit.json',
      label: 'inspection repository preparation audit',
    },
    {
      href: 'inspection-repository-preparation-current-progress.json',
      label: 'inspection repository preparation current progress',
    },
    {
      href: 'inspection-repository-preparation-current-review.md',
      label: 'inspection repository preparation current review',
    },
    {
      href: 'inspection-repository-preparation-progress.json',
      label: 'inspection repository preparation progress',
    },
    {
      href: 'inspection-repository-preparation-test.json',
      label: 'inspection repository preparation test',
    },
    {
      href: 'interpolation-test-module-review.md',
      label: 'interpolation test module review',
    },
    {
      href: 'laser-monitor-shutdown-review.md',
      label: 'laser monitor shutdown review',
    },
    {
      href: 'lexical-source-reader-audit.json',
      label: 'lexical source reader audit',
    },
    {
      href: 'lexical-source-reader-evidence.json',
      label: 'lexical source reader evidence',
    },
    {
      href: 'lexical-source-reader-progress.json',
      label: 'lexical source reader progress',
    },
    {
      href: 'lexical-source-reader-review.md',
      label: 'lexical source reader review',
    },
    {
      href: 'lexical-source-reader-test.json',
      label: 'lexical source reader test',
    },
    {
      href: 'license-weaving-probe-audit.json',
      label: 'license weaving probe audit',
    },
    {
      href: 'license-weaving-probe-progress.json',
      label: 'license weaving probe progress',
    },
    {
      href: 'license-weaving-probe-review.md',
      label: 'license weaving probe review',
    },
    {
      href: 'license-weaving-probe-test.json',
      label: 'license weaving probe test',
    },
    {
      href: 'loader-unloader-handshake-source-review.md',
      label: 'loader unloader handshake source review',
    },
    {
      href: 'localization-module-review.md',
      label: 'localization module review',
    },
    {
      href: 'log-test-module-review.md',
      label: 'log test module review',
    },
    {
      href: 'machine-framework-module-review.md',
      label: 'machine framework module review',
    },
    {
      href: 'machine-start-readiness-audit.json',
      label: 'machine start readiness audit',
    },
    {
      href: 'machine-start-readiness-review.md',
      label: 'machine start readiness review',
    },
    {
      href: 'machine-stop-signal-audit.json',
      label: 'machine stop signal audit',
    },
    {
      href: 'machine-stop-signal-current-progress.json',
      label: 'machine stop signal current progress',
    },
    {
      href: 'machine-stop-signal-current-review.md',
      label: 'machine stop signal current review',
    },
    {
      href: 'machine-stop-signal-review.md',
      label: 'machine stop signal review',
    },
    {
      href: 'machine-stop-signal-test.json',
      label: 'machine stop signal test',
    },
    {
      href: 'machine-task-lifecycle-audit.json',
      label: 'machine task lifecycle audit',
    },
    {
      href: 'machine-task-lifecycle-review.md',
      label: 'machine task lifecycle review',
    },
    {
      href: 'magazine-transfer-review.md',
      label: 'magazine transfer review',
    },
    {
      href: 'main-entry-gating-audit.json',
      label: 'main entry gating audit',
    },
    {
      href: 'main-entry-gating-review.md',
      label: 'main entry gating review',
    },
    {
      href: 'main-init-program-nodes-audit.json',
      label: 'main init program nodes audit',
    },
    {
      href: 'main-init-program-nodes-review.md',
      label: 'main init program nodes review',
    },
    {
      href: 'main-module-review.md',
      label: 'main module review',
    },
    {
      href: 'main-pr-reload-audit.json',
      label: 'main pr reload audit',
    },
    {
      href: 'main-pr-reload-review.md',
      label: 'main pr reload review',
    },
    {
      href: 'maintenance-calibration-analysis.md',
      label: 'maintenance calibration analysis',
    },
    {
      href: 'maintenance-calibration-workflow.archify.json',
      label: 'maintenance calibration workflow.archify',
    },
    {
      href: 'maintenance-calibration-workflow.html',
      label: 'maintenance calibration workflow',
    },
    {
      href: 'manual-epoxy-trial-browser-check.json',
      label: 'manual epoxy trial browser check',
    },
    {
      href: 'manual-epoxy-trial-source.html',
      label: 'manual epoxy trial source',
    },
    {
      href: 'manual-epoxy-trial-summary.md',
      label: 'manual epoxy trial summary',
    },
    {
      href: 'manual-epoxy-trial.delivery.json',
      label: 'manual epoxy trial.delivery',
    },
    {
      href: 'manual-epoxy-trial.evidence.json',
      label: 'manual epoxy trial.evidence',
    },
    {
      href: 'manual-epoxy-trial.html',
      label: 'manual epoxy trial',
    },
    {
      href: 'manual-epoxy-trial.validation.json',
      label: 'manual epoxy trial.validation',
    },
    {
      href: 'manual-epoxy-trial.visual-check.html',
      label: 'manual epoxy trial.visual check',
    },
    {
      href: 'manual-epoxy-trial.visual-check.json',
      label: 'manual epoxy trial.visual check',
    },
    {
      href: 'manual-epoxy-trial.visual-review.json',
      label: 'manual epoxy trial.visual review',
    },
    {
      href: 'manual-epoxy-trial.workflow.archify.json',
      label: 'manual epoxy trial.workflow.archify',
    },
    {
      href: 'manual-wafer-change-evidence.json',
      label: 'manual wafer change evidence',
    },
    {
      href: 'manual-wafer-change-review.md',
      label: 'manual wafer change review',
    },
    {
      href: 'mapping-action-gates-current-progress.json',
      label: 'mapping action gates current progress',
    },
    {
      href: 'mapping-action-gates-current-review.md',
      label: 'mapping action gates current review',
    },
    {
      href: 'mapping-action-gates-test.json',
      label: 'mapping action gates test',
    },
    {
      href: 'mapping-codec-sample-review.md',
      label: 'mapping codec sample review',
    },
    {
      href: 'mapping-codec-test.json',
      label: 'mapping codec test',
    },
    {
      href: 'mapping-constructor-config-review.md',
      label: 'mapping constructor config review',
    },
    {
      href: 'mapping-constructor-state-test.json',
      label: 'mapping constructor state test',
    },
    {
      href: 'mapping-material-inventory-verification.md',
      label: 'mapping material inventory verification',
    },
    {
      href: 'mapping-material-inventory.json',
      label: 'mapping material inventory',
    },
    {
      href: 'mapping-material-inventory.md',
      label: 'mapping material inventory',
    },
    {
      href: 'mapping-recovery-acceptance-check.json',
      label: 'mapping recovery acceptance check',
    },
    {
      href: 'mapping-recovery-acceptance.browser-check.json',
      label: 'mapping recovery acceptance.browser check',
    },
    {
      href: 'mapping-recovery-acceptance.html',
      label: 'mapping recovery acceptance',
    },
    {
      href: 'mapping-recovery-acceptance.json',
      label: 'mapping recovery acceptance',
    },
    {
      href: 'mapping-recovery-acceptance.md',
      label: 'mapping recovery acceptance',
    },
    {
      href: 'mapping-restore-dispatch-review.md',
      label: 'mapping restore dispatch review',
    },
    {
      href: 'mapping-restore-step-review.md',
      label: 'mapping restore step review',
    },
    {
      href: 'mapping-restore-workflow.archify.json',
      label: 'mapping restore workflow.archify',
    },
    {
      href: 'mapping-restore-workflow.entry-check.json',
      label: 'mapping restore workflow.entry check',
    },
    {
      href: 'mapping-restore-workflow.evidence.json',
      label: 'mapping restore workflow.evidence',
    },
    {
      href: 'mapping-restore-workflow.html',
      label: 'mapping restore workflow',
    },
    {
      href: 'mapping-restore-workflow.review.json',
      label: 'mapping restore workflow.review',
    },
    {
      href: 'mapping-restore-workflow.validation.json',
      label: 'mapping restore workflow.validation',
    },
    {
      href: 'mapping-restore-workflow.visual-check.html',
      label: 'mapping restore workflow.visual check',
    },
    {
      href: 'mapping-restore-workflow.visual-check.json',
      label: 'mapping restore workflow.visual check',
    },
    {
      href: 'mapping-restore-workflow.visual-review.json',
      label: 'mapping restore workflow.visual review',
    },
    {
      href: 'mapping-start-object-review.md',
      label: 'mapping start object review',
    },
    {
      href: 'mapping-step-semantics-test.json',
      label: 'mapping step semantics test',
    },
    {
      href: 'mapping-transport-object-review.md',
      label: 'mapping transport object review',
    },
    {
      href: 'missing-parameters-project-audit.json',
      label: 'missing parameters project audit',
    },
    {
      href: 'missing-parameters-project-review.md',
      label: 'missing parameters project review',
    },
    {
      href: 'mode-lifecycle-audit.json',
      label: 'mode lifecycle audit',
    },
    {
      href: 'mode-lifecycle-current-progress.json',
      label: 'mode lifecycle current progress',
    },
    {
      href: 'mode-lifecycle-current-review.md',
      label: 'mode lifecycle current review',
    },
    {
      href: 'mode-lifecycle-test.json',
      label: 'mode lifecycle test',
    },
    {
      href: 'module-review-binding-repair.md',
      label: 'module review binding repair',
    },
    {
      href: 'module-review-evidence.json',
      label: 'module review evidence',
    },
    {
      href: 'module-review-status.md',
      label: 'module review status',
    },
    {
      href: 'module-reviews.json',
      label: 'module reviews',
    },
    {
      href: 'module-source-explorer-dispatch.html',
      label: 'module source explorer dispatch',
    },
    {
      href: 'module-source-explorer-encoding-preserving.html',
      label: 'module source explorer encoding preserving',
    },
    {
      href: 'module-source-explorer-lexical.html',
      label: 'module source explorer lexical',
    },
    {
      href: 'module-source-explorer-native-dispense.html',
      label: 'module source explorer native dispense',
    },
    {
      href: 'module-source-explorer-native-runtime.html',
      label: 'module source explorer native runtime',
    },
    {
      href: 'module-source-explorer-repair.md',
      label: 'module source explorer repair',
    },
    {
      href: 'module-source-explorer-semantic.html',
      label: 'module source explorer semantic',
    },
    {
      href: 'module-source-explorer.browser-check.json',
      label: 'module source explorer.browser check',
    },
    {
      href: 'module-source-explorer.html',
      label: 'module source explorer',
    },
    {
      href: 'motion-arrival-binary-evidence.json',
      label: 'motion arrival binary evidence',
    },
    {
      href: 'motion-arrival-contract-review.md',
      label: 'motion arrival contract review',
    },
    {
      href: 'motion-arrival-sequence.archify.json',
      label: 'motion arrival sequence.archify',
    },
    {
      href: 'motion-arrival-sequence.evidence.json',
      label: 'motion arrival sequence.evidence',
    },
    {
      href: 'motion-arrival-sequence.html',
      label: 'motion arrival sequence',
    },
    {
      href: 'motion-arrival-sequence.visual-check.html',
      label: 'motion arrival sequence.visual check',
    },
    {
      href: 'motion-arrival-sequence.visual-check.json',
      label: 'motion arrival sequence.visual check',
    },
    {
      href: 'mouse-edit-audit.json',
      label: 'mouse edit audit',
    },
    {
      href: 'mouse-edit-test.json',
      label: 'mouse edit test',
    },
    {
      href: 'msbuild-evaluation-review.md',
      label: 'msbuild evaluation review',
    },
    {
      href: 'msbuild-evaluation.json',
      label: 'msbuild evaluation',
    },
    {
      href: 'native-action-controller-audit.json',
      label: 'native action controller audit',
    },
    {
      href: 'native-action-controller-current-progress.json',
      label: 'native action controller current progress',
    },
    {
      href: 'native-action-controller-current-review.md',
      label: 'native action controller current review',
    },
    {
      href: 'native-action-controller-progress.json',
      label: 'native action controller progress',
    },
    {
      href: 'native-action-controller-review.md',
      label: 'native action controller review',
    },
    {
      href: 'native-action-controller-test.json',
      label: 'native action controller test',
    },
    {
      href: 'native-action-selection-audit.json',
      label: 'native action selection audit',
    },
    {
      href: 'native-action-selection-current-progress.json',
      label: 'native action selection current progress',
    },
    {
      href: 'native-action-selection-current-review.md',
      label: 'native action selection current review',
    },
    {
      href: 'native-action-selection-progress.json',
      label: 'native action selection progress',
    },
    {
      href: 'native-action-selection-review.md',
      label: 'native action selection review',
    },
    {
      href: 'native-action-selection-test.json',
      label: 'native action selection test',
    },
    {
      href: 'native-algorithm-selection-audit.json',
      label: 'native algorithm selection audit',
    },
    {
      href: 'native-algorithm-selection-current-progress.json',
      label: 'native algorithm selection current progress',
    },
    {
      href: 'native-algorithm-selection-current-review.md',
      label: 'native algorithm selection current review',
    },
    {
      href: 'native-algorithm-selection-progress.json',
      label: 'native algorithm selection progress',
    },
    {
      href: 'native-algorithm-selection-review.md',
      label: 'native algorithm selection review',
    },
    {
      href: 'native-algorithm-selection-test.json',
      label: 'native algorithm selection test',
    },
    {
      href: 'native-aux-task-entry-audit.json',
      label: 'native aux task entry audit',
    },
    {
      href: 'native-aux-task-entry-current-progress.json',
      label: 'native aux task entry current progress',
    },
    {
      href: 'native-aux-task-entry-current-review.md',
      label: 'native aux task entry current review',
    },
    {
      href: 'native-aux-task-entry-progress.json',
      label: 'native aux task entry progress',
    },
    {
      href: 'native-aux-task-entry-review.md',
      label: 'native aux task entry review',
    },
    {
      href: 'native-aux-task-entry-test.json',
      label: 'native aux task entry test',
    },
    {
      href: 'native-bin-handshake-readiness-audit.json',
      label: 'native bin handshake readiness audit',
    },
    {
      href: 'native-bin-handshake-readiness-current-progress.json',
      label: 'native bin handshake readiness current progress',
    },
    {
      href: 'native-bin-handshake-readiness-current-review.md',
      label: 'native bin handshake readiness current review',
    },
    {
      href: 'native-bin-handshake-readiness-progress.json',
      label: 'native bin handshake readiness progress',
    },
    {
      href: 'native-bin-handshake-readiness-review.md',
      label: 'native bin handshake readiness review',
    },
    {
      href: 'native-bin-handshake-readiness-test.json',
      label: 'native bin handshake readiness test',
    },
    {
      href: 'native-build-deployment-current-rebind-review.md',
      label: 'native build deployment current rebind review',
    },
    {
      href: 'native-build-deployment-current-rebind.json',
      label: 'native build deployment current rebind',
    },
    {
      href: 'native-carrier-readiness-audit.json',
      label: 'native carrier readiness audit',
    },
    {
      href: 'native-carrier-readiness-current-progress.json',
      label: 'native carrier readiness current progress',
    },
    {
      href: 'native-carrier-readiness-current-review.md',
      label: 'native carrier readiness current review',
    },
    {
      href: 'native-carrier-readiness-progress.json',
      label: 'native carrier readiness progress',
    },
    {
      href: 'native-carrier-readiness-review.md',
      label: 'native carrier readiness review',
    },
    {
      href: 'native-carrier-readiness-test.json',
      label: 'native carrier readiness test',
    },
    {
      href: 'native-db-saver-audit.json',
      label: 'native db saver audit',
    },
    {
      href: 'native-db-saver-current-progress.json',
      label: 'native db saver current progress',
    },
    {
      href: 'native-db-saver-current-review.md',
      label: 'native db saver current review',
    },
    {
      href: 'native-db-saver-progress.json',
      label: 'native db saver progress',
    },
    {
      href: 'native-db-saver-review.md',
      label: 'native db saver review',
    },
    {
      href: 'native-db-saver-test.json',
      label: 'native db saver test',
    },
    {
      href: 'native-dispense-control-audit.json',
      label: 'native dispense control audit',
    },
    {
      href: 'native-dispense-control-current-progress.json',
      label: 'native dispense control current progress',
    },
    {
      href: 'native-dispense-control-current-review.md',
      label: 'native dispense control current review',
    },
    {
      href: 'native-dispense-control-progress.json',
      label: 'native dispense control progress',
    },
    {
      href: 'native-dispense-control-review.md',
      label: 'native dispense control review',
    },
    {
      href: 'native-dispense-control-test.json',
      label: 'native dispense control test',
    },
    {
      href: 'native-dispense-controller-audit.json',
      label: 'native dispense controller audit',
    },
    {
      href: 'native-dispense-controller-current-progress.json',
      label: 'native dispense controller current progress',
    },
    {
      href: 'native-dispense-controller-current-review.md',
      label: 'native dispense controller current review',
    },
    {
      href: 'native-dispense-controller-progress.json',
      label: 'native dispense controller progress',
    },
    {
      href: 'native-dispense-controller-review.md',
      label: 'native dispense controller review',
    },
    {
      href: 'native-dispense-controller-test.json',
      label: 'native dispense controller test',
    },
    {
      href: 'native-dispense-form-audit.json',
      label: 'native dispense form audit',
    },
    {
      href: 'native-dispense-form-current-progress.json',
      label: 'native dispense form current progress',
    },
    {
      href: 'native-dispense-form-current-review.md',
      label: 'native dispense form current review',
    },
    {
      href: 'native-dispense-form-progress.json',
      label: 'native dispense form progress',
    },
    {
      href: 'native-dispense-form-review.md',
      label: 'native dispense form review',
    },
    {
      href: 'native-dispense-form-test.json',
      label: 'native dispense form test',
    },
    {
      href: 'native-dispense-geometry-audit.json',
      label: 'native dispense geometry audit',
    },
    {
      href: 'native-dispense-geometry-current-progress.json',
      label: 'native dispense geometry current progress',
    },
    {
      href: 'native-dispense-geometry-current-review.md',
      label: 'native dispense geometry current review',
    },
    {
      href: 'native-dispense-geometry-progress.json',
      label: 'native dispense geometry progress',
    },
    {
      href: 'native-dispense-geometry-review.md',
      label: 'native dispense geometry review',
    },
    {
      href: 'native-dispense-geometry-test.json',
      label: 'native dispense geometry test',
    },
    {
      href: 'native-dispense-input-audit.json',
      label: 'native dispense input audit',
    },
    {
      href: 'native-dispense-input-current-progress.json',
      label: 'native dispense input current progress',
    },
    {
      href: 'native-dispense-input-current-review.md',
      label: 'native dispense input current review',
    },
    {
      href: 'native-dispense-input-progress.json',
      label: 'native dispense input progress',
    },
    {
      href: 'native-dispense-input-review.md',
      label: 'native dispense input review',
    },
    {
      href: 'native-dispense-input-test.json',
      label: 'native dispense input test',
    },
    {
      href: 'native-dispense-policy-audit.json',
      label: 'native dispense policy audit',
    },
    {
      href: 'native-dispense-policy-current-progress.json',
      label: 'native dispense policy current progress',
    },
    {
      href: 'native-dispense-policy-current-review.md',
      label: 'native dispense policy current review',
    },
    {
      href: 'native-dispense-policy-progress.json',
      label: 'native dispense policy progress',
    },
    {
      href: 'native-dispense-policy-review.md',
      label: 'native dispense policy review',
    },
    {
      href: 'native-dispense-policy-test.json',
      label: 'native dispense policy test',
    },
    {
      href: 'native-dispense-reader-audit.json',
      label: 'native dispense reader audit',
    },
    {
      href: 'native-dispense-reader-current-progress.json',
      label: 'native dispense reader current progress',
    },
    {
      href: 'native-dispense-reader-current-review.md',
      label: 'native dispense reader current review',
    },
    {
      href: 'native-dispense-reader-evidence.json',
      label: 'native dispense reader evidence',
    },
    {
      href: 'native-dispense-reader-progress.json',
      label: 'native dispense reader progress',
    },
    {
      href: 'native-dispense-reader-review.md',
      label: 'native dispense reader review',
    },
    {
      href: 'native-dispense-reader-test.json',
      label: 'native dispense reader test',
    },
    {
      href: 'native-dispense-rendering-audit.json',
      label: 'native dispense rendering audit',
    },
    {
      href: 'native-dispense-rendering-current-progress.json',
      label: 'native dispense rendering current progress',
    },
    {
      href: 'native-dispense-rendering-current-review.md',
      label: 'native dispense rendering current review',
    },
    {
      href: 'native-dispense-rendering-progress.json',
      label: 'native dispense rendering progress',
    },
    {
      href: 'native-dispense-rendering-review.md',
      label: 'native dispense rendering review',
    },
    {
      href: 'native-dispense-rendering-test.json',
      label: 'native dispense rendering test',
    },
    {
      href: 'native-dispense-source-explorer-browser-current-progress.json',
      label: 'native dispense source explorer browser current progress',
    },
    {
      href: 'native-dispense-source-explorer-browser-current-review.md',
      label: 'native dispense source explorer browser current review',
    },
    {
      href: 'native-exit-consumer-pending-audit.json',
      label: 'native exit consumer pending audit',
    },
    {
      href: 'native-exit-consumer-pending-current-progress.json',
      label: 'native exit consumer pending current progress',
    },
    {
      href: 'native-exit-consumer-pending-current-review.md',
      label: 'native exit consumer pending current review',
    },
    {
      href: 'native-exit-consumer-pending-progress.json',
      label: 'native exit consumer pending progress',
    },
    {
      href: 'native-exit-consumer-pending-review.md',
      label: 'native exit consumer pending review',
    },
    {
      href: 'native-exit-consumer-pending-test.json',
      label: 'native exit consumer pending test',
    },
    {
      href: 'native-force-calibration-audit.json',
      label: 'native force calibration audit',
    },
    {
      href: 'native-force-calibration-current-progress.json',
      label: 'native force calibration current progress',
    },
    {
      href: 'native-force-calibration-current-review.md',
      label: 'native force calibration current review',
    },
    {
      href: 'native-force-calibration-progress.json',
      label: 'native force calibration progress',
    },
    {
      href: 'native-force-calibration-review.md',
      label: 'native force calibration review',
    },
    {
      href: 'native-force-calibration-test.json',
      label: 'native force calibration test',
    },
    {
      href: 'native-inout-handshake-audit.json',
      label: 'native inout handshake audit',
    },
    {
      href: 'native-inout-handshake-current-progress.json',
      label: 'native inout handshake current progress',
    },
    {
      href: 'native-inout-handshake-current-review.md',
      label: 'native inout handshake current review',
    },
    {
      href: 'native-inout-handshake-progress.json',
      label: 'native inout handshake progress',
    },
    {
      href: 'native-inout-handshake-review.md',
      label: 'native inout handshake review',
    },
    {
      href: 'native-inout-handshake-test.json',
      label: 'native inout handshake test',
    },
    {
      href: 'native-inspection-readiness-audit.json',
      label: 'native inspection readiness audit',
    },
    {
      href: 'native-inspection-readiness-current-progress.json',
      label: 'native inspection readiness current progress',
    },
    {
      href: 'native-inspection-readiness-current-review.md',
      label: 'native inspection readiness current review',
    },
    {
      href: 'native-inspection-readiness-progress.json',
      label: 'native inspection readiness progress',
    },
    {
      href: 'native-inspection-readiness-review.md',
      label: 'native inspection readiness review',
    },
    {
      href: 'native-inspection-readiness-test.json',
      label: 'native inspection readiness test',
    },
    {
      href: 'native-loader-unloader-entry-audit.json',
      label: 'native loader unloader entry audit',
    },
    {
      href: 'native-loader-unloader-entry-current-progress.json',
      label: 'native loader unloader entry current progress',
    },
    {
      href: 'native-loader-unloader-entry-current-review.md',
      label: 'native loader unloader entry current review',
    },
    {
      href: 'native-loader-unloader-entry-progress.json',
      label: 'native loader unloader entry progress',
    },
    {
      href: 'native-loader-unloader-entry-review.md',
      label: 'native loader unloader entry review',
    },
    {
      href: 'native-loader-unloader-entry-test.json',
      label: 'native loader unloader entry test',
    },
    {
      href: 'native-machine-environment-audit.json',
      label: 'native machine environment audit',
    },
    {
      href: 'native-machine-environment-current-progress.json',
      label: 'native machine environment current progress',
    },
    {
      href: 'native-machine-environment-current-review.md',
      label: 'native machine environment current review',
    },
    {
      href: 'native-machine-environment-progress.json',
      label: 'native machine environment progress',
    },
    {
      href: 'native-machine-environment-review.md',
      label: 'native machine environment review',
    },
    {
      href: 'native-machine-environment-test.json',
      label: 'native machine environment test',
    },
    {
      href: 'native-machine-stop-audit.json',
      label: 'native machine stop audit',
    },
    {
      href: 'native-machine-stop-current-progress.json',
      label: 'native machine stop current progress',
    },
    {
      href: 'native-machine-stop-current-review.md',
      label: 'native machine stop current review',
    },
    {
      href: 'native-machine-stop-progress.json',
      label: 'native machine stop progress',
    },
    {
      href: 'native-machine-stop-review.md',
      label: 'native machine stop review',
    },
    {
      href: 'native-machine-stop-test.json',
      label: 'native machine stop test',
    },
    {
      href: 'native-machine-task-closure-audit.json',
      label: 'native machine task closure audit',
    },
    {
      href: 'native-machine-task-closure-current-progress.json',
      label: 'native machine task closure current progress',
    },
    {
      href: 'native-machine-task-closure-current-review.md',
      label: 'native machine task closure current review',
    },
    {
      href: 'native-machine-task-closure-progress.json',
      label: 'native machine task closure progress',
    },
    {
      href: 'native-machine-task-closure-review.md',
      label: 'native machine task closure review',
    },
    {
      href: 'native-machine-task-closure-test.json',
      label: 'native machine task closure test',
    },
    {
      href: 'native-mainform-close-save-audit.json',
      label: 'native mainform close save audit',
    },
    {
      href: 'native-mainform-close-save-current-progress.json',
      label: 'native mainform close save current progress',
    },
    {
      href: 'native-mainform-close-save-current-review.md',
      label: 'native mainform close save current review',
    },
    {
      href: 'native-mainform-close-save-progress.json',
      label: 'native mainform close save progress',
    },
    {
      href: 'native-mainform-close-save-review.md',
      label: 'native mainform close save review',
    },
    {
      href: 'native-mainform-close-save-test.json',
      label: 'native mainform close save test',
    },
    {
      href: 'native-mainform-context-audit.json',
      label: 'native mainform context audit',
    },
    {
      href: 'native-mainform-context-current-progress.json',
      label: 'native mainform context current progress',
    },
    {
      href: 'native-mainform-context-current-review.md',
      label: 'native mainform context current review',
    },
    {
      href: 'native-mainform-context-progress.json',
      label: 'native mainform context progress',
    },
    {
      href: 'native-mainform-context-review.md',
      label: 'native mainform context review',
    },
    {
      href: 'native-mainform-context-test.json',
      label: 'native mainform context test',
    },
    {
      href: 'native-mainform-dpi-adaptation-audit.json',
      label: 'native mainform dpi adaptation audit',
    },
    {
      href: 'native-mainform-dpi-adaptation-progress.json',
      label: 'native mainform dpi adaptation progress',
    },
    {
      href: 'native-mainform-dpi-adaptation-review.md',
      label: 'native mainform dpi adaptation review',
    },
    {
      href: 'native-mainform-layout-audit.json',
      label: 'native mainform layout audit',
    },
    {
      href: 'native-mainform-layout-current-progress.json',
      label: 'native mainform layout current progress',
    },
    {
      href: 'native-mainform-layout-current-review.md',
      label: 'native mainform layout current review',
    },
    {
      href: 'native-mainform-layout-progress.json',
      label: 'native mainform layout progress',
    },
    {
      href: 'native-mainform-layout-review.md',
      label: 'native mainform layout review',
    },
    {
      href: 'native-mainform-layout-test.json',
      label: 'native mainform layout test',
    },
    {
      href: 'native-mainform-viewport-audit.json',
      label: 'native mainform viewport audit',
    },
    {
      href: 'native-mainform-viewport-current-progress.json',
      label: 'native mainform viewport current progress',
    },
    {
      href: 'native-mainform-viewport-current-rebind-review.md',
      label: 'native mainform viewport current rebind review',
    },
    {
      href: 'native-mainform-viewport-current-rebind.json',
      label: 'native mainform viewport current rebind',
    },
    {
      href: 'native-mainform-viewport-current-review.md',
      label: 'native mainform viewport current review',
    },
    {
      href: 'native-mainform-viewport-progress.json',
      label: 'native mainform viewport progress',
    },
    {
      href: 'native-mainform-viewport-review.md',
      label: 'native mainform viewport review',
    },
    {
      href: 'native-mainform-viewport-test.json',
      label: 'native mainform viewport test',
    },
    {
      href: 'native-monitor-consumer-startup-audit.json',
      label: 'native monitor consumer startup audit',
    },
    {
      href: 'native-monitor-consumer-startup-current-progress.json',
      label: 'native monitor consumer startup current progress',
    },
    {
      href: 'native-monitor-consumer-startup-current-review.md',
      label: 'native monitor consumer startup current review',
    },
    {
      href: 'native-monitor-consumer-startup-progress.json',
      label: 'native monitor consumer startup progress',
    },
    {
      href: 'native-monitor-consumer-startup-review.md',
      label: 'native monitor consumer startup review',
    },
    {
      href: 'native-monitor-consumer-startup-test.json',
      label: 'native monitor consumer startup test',
    },
    {
      href: 'native-msbuild-build-audit.json',
      label: 'native msbuild build audit',
    },
    {
      href: 'native-msbuild-build-current-progress.json',
      label: 'native msbuild build current progress',
    },
    {
      href: 'native-msbuild-build-current-review.md',
      label: 'native msbuild build current review',
    },
    {
      href: 'native-msbuild-build-progress.json',
      label: 'native msbuild build progress',
    },
    {
      href: 'native-msbuild-build-review.md',
      label: 'native msbuild build review',
    },
    {
      href: 'native-msbuild-build-test.json',
      label: 'native msbuild build test',
    },
    {
      href: 'native-node-do-work-branches-progress.json',
      label: 'native node do work branches progress',
    },
    {
      href: 'native-node-do-work-branches-review.md',
      label: 'native node do work branches review',
    },
    {
      href: 'native-node-preconditions-audit.json',
      label: 'native node preconditions audit',
    },
    {
      href: 'native-node-preconditions-current-progress.json',
      label: 'native node preconditions current progress',
    },
    {
      href: 'native-node-preconditions-current-review.md',
      label: 'native node preconditions current review',
    },
    {
      href: 'native-node-preconditions-progress.json',
      label: 'native node preconditions progress',
    },
    {
      href: 'native-node-preconditions-review.md',
      label: 'native node preconditions review',
    },
    {
      href: 'native-node-preconditions-test.json',
      label: 'native node preconditions test',
    },
    {
      href: 'native-online-monitor-boundary-audit.json',
      label: 'native online monitor boundary audit',
    },
    {
      href: 'native-online-monitor-boundary-progress.json',
      label: 'native online monitor boundary progress',
    },
    {
      href: 'native-online-monitor-boundary-review.md',
      label: 'native online monitor boundary review',
    },
    {
      href: 'native-online-monitor-fault-audit.json',
      label: 'native online monitor fault audit',
    },
    {
      href: 'native-online-monitor-fault-progress.json',
      label: 'native online monitor fault progress',
    },
    {
      href: 'native-online-monitor-fault-replay-audit.json',
      label: 'native online monitor fault replay audit',
    },
    {
      href: 'native-online-monitor-fault-replay-progress.json',
      label: 'native online monitor fault replay progress',
    },
    {
      href: 'native-online-monitor-fault-replay-review.md',
      label: 'native online monitor fault replay review',
    },
    {
      href: 'native-online-monitor-fault-review.md',
      label: 'native online monitor fault review',
    },
    {
      href: 'native-online-monitor-loop-audit.json',
      label: 'native online monitor loop audit',
    },
    {
      href: 'native-online-monitor-loop-progress.json',
      label: 'native online monitor loop progress',
    },
    {
      href: 'native-online-monitor-loop-review.md',
      label: 'native online monitor loop review',
    },
    {
      href: 'native-pr-init-boundary-audit.json',
      label: 'native pr init boundary audit',
    },
    {
      href: 'native-pr-init-boundary-current-progress.json',
      label: 'native pr init boundary current progress',
    },
    {
      href: 'native-pr-init-boundary-current-review.md',
      label: 'native pr init boundary current review',
    },
    {
      href: 'native-pr-init-boundary-progress.json',
      label: 'native pr init boundary progress',
    },
    {
      href: 'native-pr-init-boundary-review.md',
      label: 'native pr init boundary review',
    },
    {
      href: 'native-pr-init-boundary-test.json',
      label: 'native pr init boundary test',
    },
    {
      href: 'native-predispense-prerequisites-audit.json',
      label: 'native predispense prerequisites audit',
    },
    {
      href: 'native-predispense-prerequisites-current-progress.json',
      label: 'native predispense prerequisites current progress',
    },
    {
      href: 'native-predispense-prerequisites-current-review.md',
      label: 'native predispense prerequisites current review',
    },
    {
      href: 'native-predispense-prerequisites-progress.json',
      label: 'native predispense prerequisites progress',
    },
    {
      href: 'native-predispense-prerequisites-review.md',
      label: 'native predispense prerequisites review',
    },
    {
      href: 'native-predispense-prerequisites-test.json',
      label: 'native predispense prerequisites test',
    },
    {
      href: 'native-preparation-current-rebind-review.md',
      label: 'native preparation current rebind review',
    },
    {
      href: 'native-preparation-current-rebind.json',
      label: 'native preparation current rebind',
    },
    {
      href: 'native-program-exception-handlers-narrow-progress.json',
      label: 'native program exception handlers narrow progress',
    },
    {
      href: 'native-program-exception-handlers-narrow-review.md',
      label: 'native program exception handlers narrow review',
    },
    {
      href: 'native-program-exception-handlers-progress.json',
      label: 'native program exception handlers progress',
    },
    {
      href: 'native-program-exception-handlers-review.md',
      label: 'native program exception handlers review',
    },
    {
      href: 'native-program-main-entry-audit.json',
      label: 'native program main entry audit',
    },
    {
      href: 'native-program-main-entry-current-progress.json',
      label: 'native program main entry current progress',
    },
    {
      href: 'native-program-main-entry-current-review.md',
      label: 'native program main entry current review',
    },
    {
      href: 'native-program-main-entry-duplicate-audit.json',
      label: 'native program main entry duplicate audit',
    },
    {
      href: 'native-program-main-entry-duplicate-progress.json',
      label: 'native program main entry duplicate progress',
    },
    {
      href: 'native-program-main-entry-duplicate-review.md',
      label: 'native program main entry duplicate review',
    },
    {
      href: 'native-program-main-entry-duplicate-test.json',
      label: 'native program main entry duplicate test',
    },
    {
      href: 'native-program-main-entry-progress.json',
      label: 'native program main entry progress',
    },
    {
      href: 'native-program-main-entry-review.md',
      label: 'native program main entry review',
    },
    {
      href: 'native-program-main-entry-test.json',
      label: 'native program main entry test',
    },
    {
      href: 'native-program-readiness-audit.json',
      label: 'native program readiness audit',
    },
    {
      href: 'native-program-readiness-current-progress.json',
      label: 'native program readiness current progress',
    },
    {
      href: 'native-program-readiness-current-review.md',
      label: 'native program readiness current review',
    },
    {
      href: 'native-program-readiness-progress.json',
      label: 'native program readiness progress',
    },
    {
      href: 'native-program-readiness-review.md',
      label: 'native program readiness review',
    },
    {
      href: 'native-program-readiness-test.json',
      label: 'native program readiness test',
    },
    {
      href: 'native-readiness-current-rebind-review.md',
      label: 'native readiness current rebind review',
    },
    {
      href: 'native-readiness-current-rebind.json',
      label: 'native readiness current rebind',
    },
    {
      href: 'native-recipe-action-selection-audit.json',
      label: 'native recipe action selection audit',
    },
    {
      href: 'native-recipe-action-selection-current-progress.json',
      label: 'native recipe action selection current progress',
    },
    {
      href: 'native-recipe-action-selection-current-review.md',
      label: 'native recipe action selection current review',
    },
    {
      href: 'native-recipe-action-selection-progress.json',
      label: 'native recipe action selection progress',
    },
    {
      href: 'native-recipe-action-selection-review.md',
      label: 'native recipe action selection review',
    },
    {
      href: 'native-recipe-action-selection-test.json',
      label: 'native recipe action selection test',
    },
    {
      href: 'native-recipe-create-copy-audit.json',
      label: 'native recipe create copy audit',
    },
    {
      href: 'native-recipe-create-copy-current-progress.json',
      label: 'native recipe create copy current progress',
    },
    {
      href: 'native-recipe-create-copy-current-review.md',
      label: 'native recipe create copy current review',
    },
    {
      href: 'native-recipe-create-copy-progress.json',
      label: 'native recipe create copy progress',
    },
    {
      href: 'native-recipe-create-copy-review.md',
      label: 'native recipe create copy review',
    },
    {
      href: 'native-recipe-create-copy-test.json',
      label: 'native recipe create copy test',
    },
    {
      href: 'native-recipe-dialog-events-audit.json',
      label: 'native recipe dialog events audit',
    },
    {
      href: 'native-recipe-dialog-events-current-progress.json',
      label: 'native recipe dialog events current progress',
    },
    {
      href: 'native-recipe-dialog-events-current-review.md',
      label: 'native recipe dialog events current review',
    },
    {
      href: 'native-recipe-dialog-events-progress.json',
      label: 'native recipe dialog events progress',
    },
    {
      href: 'native-recipe-dialog-events-review.md',
      label: 'native recipe dialog events review',
    },
    {
      href: 'native-recipe-dialog-events-test.json',
      label: 'native recipe dialog events test',
    },
    {
      href: 'native-recipe-live-reload-audit.json',
      label: 'native recipe live reload audit',
    },
    {
      href: 'native-recipe-live-reload-current-progress.json',
      label: 'native recipe live reload current progress',
    },
    {
      href: 'native-recipe-live-reload-current-review.md',
      label: 'native recipe live reload current review',
    },
    {
      href: 'native-recipe-live-reload-progress.json',
      label: 'native recipe live reload progress',
    },
    {
      href: 'native-recipe-live-reload-review.md',
      label: 'native recipe live reload review',
    },
    {
      href: 'native-recipe-live-reload-test.json',
      label: 'native recipe live reload test',
    },
    {
      href: 'native-recipe-task-lifecycle-audit.json',
      label: 'native recipe task lifecycle audit',
    },
    {
      href: 'native-recipe-task-lifecycle-current-progress.json',
      label: 'native recipe task lifecycle current progress',
    },
    {
      href: 'native-recipe-task-lifecycle-current-review.md',
      label: 'native recipe task lifecycle current review',
    },
    {
      href: 'native-recipe-task-lifecycle-progress.json',
      label: 'native recipe task lifecycle progress',
    },
    {
      href: 'native-recipe-task-lifecycle-review.md',
      label: 'native recipe task lifecycle review',
    },
    {
      href: 'native-recipe-task-lifecycle-test.json',
      label: 'native recipe task lifecycle test',
    },
    {
      href: 'native-recipe-ui-reload-audit.json',
      label: 'native recipe ui reload audit',
    },
    {
      href: 'native-recipe-ui-reload-current-progress.json',
      label: 'native recipe ui reload current progress',
    },
    {
      href: 'native-recipe-ui-reload-current-review.md',
      label: 'native recipe ui reload current review',
    },
    {
      href: 'native-recipe-ui-reload-progress.json',
      label: 'native recipe ui reload progress',
    },
    {
      href: 'native-recipe-ui-reload-review.md',
      label: 'native recipe ui reload review',
    },
    {
      href: 'native-recipe-ui-reload-test.json',
      label: 'native recipe ui reload test',
    },
    {
      href: 'native-runtime-reader-audit.json',
      label: 'native runtime reader audit',
    },
    {
      href: 'native-runtime-reader-current-progress.json',
      label: 'native runtime reader current progress',
    },
    {
      href: 'native-runtime-reader-current-review.md',
      label: 'native runtime reader current review',
    },
    {
      href: 'native-runtime-reader-evidence.json',
      label: 'native runtime reader evidence',
    },
    {
      href: 'native-runtime-reader-progress.json',
      label: 'native runtime reader progress',
    },
    {
      href: 'native-runtime-reader-review.md',
      label: 'native runtime reader review',
    },
    {
      href: 'native-runtime-reader-test.json',
      label: 'native runtime reader test',
    },
    {
      href: 'native-runtime-source-explorer-browser-current-progress.json',
      label: 'native runtime source explorer browser current progress',
    },
    {
      href: 'native-runtime-source-explorer-browser-current-review.md',
      label: 'native runtime source explorer browser current review',
    },
    {
      href: 'native-s1-defect-outcomes-audit.json',
      label: 'native s1 defect outcomes audit',
    },
    {
      href: 'native-s1-defect-outcomes-current-progress.json',
      label: 'native s1 defect outcomes current progress',
    },
    {
      href: 'native-s1-defect-outcomes-current-review.md',
      label: 'native s1 defect outcomes current review',
    },
    {
      href: 'native-s1-defect-outcomes-progress.json',
      label: 'native s1 defect outcomes progress',
    },
    {
      href: 'native-s1-defect-outcomes-review.md',
      label: 'native s1 defect outcomes review',
    },
    {
      href: 'native-s1-defect-outcomes-test.json',
      label: 'native s1 defect outcomes test',
    },
    {
      href: 'native-s1-return-gates-audit.json',
      label: 'native s1 return gates audit',
    },
    {
      href: 'native-s1-return-gates-current-progress.json',
      label: 'native s1 return gates current progress',
    },
    {
      href: 'native-s1-return-gates-current-review.md',
      label: 'native s1 return gates current review',
    },
    {
      href: 'native-s1-return-gates-progress.json',
      label: 'native s1 return gates progress',
    },
    {
      href: 'native-s1-return-gates-review.md',
      label: 'native s1 return gates review',
    },
    {
      href: 'native-s1-return-gates-test.json',
      label: 'native s1 return gates test',
    },
    {
      href: 'native-s1-rework-context-audit.json',
      label: 'native s1 rework context audit',
    },
    {
      href: 'native-s1-rework-context-current-progress.json',
      label: 'native s1 rework context current progress',
    },
    {
      href: 'native-s1-rework-context-current-review.md',
      label: 'native s1 rework context current review',
    },
    {
      href: 'native-s1-rework-context-progress.json',
      label: 'native s1 rework context progress',
    },
    {
      href: 'native-s1-rework-context-review.md',
      label: 'native s1 rework context review',
    },
    {
      href: 'native-s1-rework-context-test.json',
      label: 'native s1 rework context test',
    },
    {
      href: 'native-s1-segment-interaction-audit.json',
      label: 'native s1 segment interaction audit',
    },
    {
      href: 'native-s1-segment-interaction-current-progress.json',
      label: 'native s1 segment interaction current progress',
    },
    {
      href: 'native-s1-segment-interaction-current-review.md',
      label: 'native s1 segment interaction current review',
    },
    {
      href: 'native-s1-segment-interaction-progress.json',
      label: 'native s1 segment interaction progress',
    },
    {
      href: 'native-s1-segment-interaction-review.md',
      label: 'native s1 segment interaction review',
    },
    {
      href: 'native-s1-segment-interaction-test.json',
      label: 'native s1 segment interaction test',
    },
    {
      href: 'native-s1-step-commit-audit.json',
      label: 'native s1 step commit audit',
    },
    {
      href: 'native-s1-step-commit-current-progress.json',
      label: 'native s1 step commit current progress',
    },
    {
      href: 'native-s1-step-commit-current-review.md',
      label: 'native s1 step commit current review',
    },
    {
      href: 'native-s1-step-commit-progress.json',
      label: 'native s1 step commit progress',
    },
    {
      href: 'native-s1-step-commit-review.md',
      label: 'native s1 step commit review',
    },
    {
      href: 'native-s1-step-commit-test.json',
      label: 'native s1 step commit test',
    },
    {
      href: 'native-s1-stop-recovery-audit.json',
      label: 'native s1 stop recovery audit',
    },
    {
      href: 'native-s1-stop-recovery-current-progress.json',
      label: 'native s1 stop recovery current progress',
    },
    {
      href: 'native-s1-stop-recovery-current-review.md',
      label: 'native s1 stop recovery current review',
    },
    {
      href: 'native-s1-stop-recovery-progress.json',
      label: 'native s1 stop recovery progress',
    },
    {
      href: 'native-s1-stop-recovery-review.md',
      label: 'native s1 stop recovery review',
    },
    {
      href: 'native-s1-stop-recovery-test.json',
      label: 'native s1 stop recovery test',
    },
    {
      href: 'native-s1-task-loop-audit.json',
      label: 'native s1 task loop audit',
    },
    {
      href: 'native-s1-task-loop-current-progress.json',
      label: 'native s1 task loop current progress',
    },
    {
      href: 'native-s1-task-loop-current-review.md',
      label: 'native s1 task loop current review',
    },
    {
      href: 'native-s1-task-loop-progress.json',
      label: 'native s1 task loop progress',
    },
    {
      href: 'native-s1-task-loop-review.md',
      label: 'native s1 task loop review',
    },
    {
      href: 'native-s1-task-loop-test.json',
      label: 'native s1 task loop test',
    },
    {
      href: 'native-s1-working-pause-audit.json',
      label: 'native s1 working pause audit',
    },
    {
      href: 'native-s1-working-pause-current-progress.json',
      label: 'native s1 working pause current progress',
    },
    {
      href: 'native-s1-working-pause-current-review.md',
      label: 'native s1 working pause current review',
    },
    {
      href: 'native-s1-working-pause-progress.json',
      label: 'native s1 working pause progress',
    },
    {
      href: 'native-s1-working-pause-review.md',
      label: 'native s1 working pause review',
    },
    {
      href: 'native-s1-working-pause-test.json',
      label: 'native s1 working pause test',
    },
    {
      href: 'native-s2-action-boundaries-audit.json',
      label: 'native s2 action boundaries audit',
    },
    {
      href: 'native-s2-action-boundaries-current-progress.json',
      label: 'native s2 action boundaries current progress',
    },
    {
      href: 'native-s2-action-boundaries-current-review.md',
      label: 'native s2 action boundaries current review',
    },
    {
      href: 'native-s2-action-boundaries-progress.json',
      label: 'native s2 action boundaries progress',
    },
    {
      href: 'native-s2-action-boundaries-review.md',
      label: 'native s2 action boundaries review',
    },
    {
      href: 'native-s2-action-boundaries-test.json',
      label: 'native s2 action boundaries test',
    },
    {
      href: 'native-s2-compensation-prerequisites-audit.json',
      label: 'native s2 compensation prerequisites audit',
    },
    {
      href: 'native-s2-compensation-prerequisites-current-progress.json',
      label: 'native s2 compensation prerequisites current progress',
    },
    {
      href: 'native-s2-compensation-prerequisites-current-review.md',
      label: 'native s2 compensation prerequisites current review',
    },
    {
      href: 'native-s2-compensation-prerequisites-progress.json',
      label: 'native s2 compensation prerequisites progress',
    },
    {
      href: 'native-s2-compensation-prerequisites-review.md',
      label: 'native s2 compensation prerequisites review',
    },
    {
      href: 'native-s2-compensation-prerequisites-test.json',
      label: 'native s2 compensation prerequisites test',
    },
    {
      href: 'native-s2-readiness-audit.json',
      label: 'native s2 readiness audit',
    },
    {
      href: 'native-s2-readiness-current-progress.json',
      label: 'native s2 readiness current progress',
    },
    {
      href: 'native-s2-readiness-current-review.md',
      label: 'native s2 readiness current review',
    },
    {
      href: 'native-s2-readiness-progress.json',
      label: 'native s2 readiness progress',
    },
    {
      href: 'native-s2-readiness-review.md',
      label: 'native s2 readiness review',
    },
    {
      href: 'native-s2-readiness-test.json',
      label: 'native s2 readiness test',
    },
    {
      href: 'native-s2-reset-propagation-audit.json',
      label: 'native s2 reset propagation audit',
    },
    {
      href: 'native-s2-reset-propagation-current-progress.json',
      label: 'native s2 reset propagation current progress',
    },
    {
      href: 'native-s2-reset-propagation-current-review.md',
      label: 'native s2 reset propagation current review',
    },
    {
      href: 'native-s2-reset-propagation-progress.json',
      label: 'native s2 reset propagation progress',
    },
    {
      href: 'native-s2-reset-propagation-review.md',
      label: 'native s2 reset propagation review',
    },
    {
      href: 'native-s2-reset-propagation-test.json',
      label: 'native s2 reset propagation test',
    },
    {
      href: 'native-s2-shelf-gates-audit.json',
      label: 'native s2 shelf gates audit',
    },
    {
      href: 'native-s2-shelf-gates-current-progress.json',
      label: 'native s2 shelf gates current progress',
    },
    {
      href: 'native-s2-shelf-gates-current-review.md',
      label: 'native s2 shelf gates current review',
    },
    {
      href: 'native-s2-shelf-gates-progress.json',
      label: 'native s2 shelf gates progress',
    },
    {
      href: 'native-s2-shelf-gates-review.md',
      label: 'native s2 shelf gates review',
    },
    {
      href: 'native-s2-shelf-gates-test.json',
      label: 'native s2 shelf gates test',
    },
    {
      href: 'native-s2-task-entry-audit.json',
      label: 'native s2 task entry audit',
    },
    {
      href: 'native-s2-task-entry-current-progress.json',
      label: 'native s2 task entry current progress',
    },
    {
      href: 'native-s2-task-entry-current-review.md',
      label: 'native s2 task entry current review',
    },
    {
      href: 'native-s2-task-entry-progress.json',
      label: 'native s2 task entry progress',
    },
    {
      href: 'native-s2-task-entry-review.md',
      label: 'native s2 task entry review',
    },
    {
      href: 'native-s2-task-entry-test.json',
      label: 'native s2 task entry test',
    },
    {
      href: 'native-setup-vdproj-audit.json',
      label: 'native setup vdproj audit',
    },
    {
      href: 'native-setup-vdproj-current-progress.json',
      label: 'native setup vdproj current progress',
    },
    {
      href: 'native-setup-vdproj-current-review.md',
      label: 'native setup vdproj current review',
    },
    {
      href: 'native-setup-vdproj-progress.json',
      label: 'native setup vdproj progress',
    },
    {
      href: 'native-setup-vdproj-review.md',
      label: 'native setup vdproj review',
    },
    {
      href: 'native-setup-vdproj-test.json',
      label: 'native setup vdproj test',
    },
    {
      href: 'native-statistics-producer-audit.json',
      label: 'native statistics producer audit',
    },
    {
      href: 'native-statistics-producer-current-progress.json',
      label: 'native statistics producer current progress',
    },
    {
      href: 'native-statistics-producer-current-review.md',
      label: 'native statistics producer current review',
    },
    {
      href: 'native-statistics-producer-progress.json',
      label: 'native statistics producer progress',
    },
    {
      href: 'native-statistics-producer-review.md',
      label: 'native statistics producer review',
    },
    {
      href: 'native-statistics-producer-test.json',
      label: 'native statistics producer test',
    },
    {
      href: 'native-task-input-gates-audit.json',
      label: 'native task input gates audit',
    },
    {
      href: 'native-task-input-gates-current-progress.json',
      label: 'native task input gates current progress',
    },
    {
      href: 'native-task-input-gates-current-review.md',
      label: 'native task input gates current review',
    },
    {
      href: 'native-task-input-gates-progress.json',
      label: 'native task input gates progress',
    },
    {
      href: 'native-task-input-gates-review.md',
      label: 'native task input gates review',
    },
    {
      href: 'native-task-input-gates-test.json',
      label: 'native task input gates test',
    },
    {
      href: 'native-transport-context-audit.json',
      label: 'native transport context audit',
    },
    {
      href: 'native-transport-context-current-progress.json',
      label: 'native transport context current progress',
    },
    {
      href: 'native-transport-context-current-review.md',
      label: 'native transport context current review',
    },
    {
      href: 'native-transport-context-progress.json',
      label: 'native transport context progress',
    },
    {
      href: 'native-transport-context-review.md',
      label: 'native transport context review',
    },
    {
      href: 'native-transport-context-test.json',
      label: 'native transport context test',
    },
    {
      href: 'native-transport-environment-audit.json',
      label: 'native transport environment audit',
    },
    {
      href: 'native-transport-environment-current-progress.json',
      label: 'native transport environment current progress',
    },
    {
      href: 'native-transport-environment-current-review.md',
      label: 'native transport environment current review',
    },
    {
      href: 'native-transport-environment-progress.json',
      label: 'native transport environment progress',
    },
    {
      href: 'native-transport-environment-review.md',
      label: 'native transport environment review',
    },
    {
      href: 'native-transport-environment-test.json',
      label: 'native transport environment test',
    },
    {
      href: 'native-ui-stop-recovery-audit.json',
      label: 'native ui stop recovery audit',
    },
    {
      href: 'native-ui-stop-recovery-current-progress.json',
      label: 'native ui stop recovery current progress',
    },
    {
      href: 'native-ui-stop-recovery-current-review.md',
      label: 'native ui stop recovery current review',
    },
    {
      href: 'native-ui-stop-recovery-progress.json',
      label: 'native ui stop recovery progress',
    },
    {
      href: 'native-ui-stop-recovery-review.md',
      label: 'native ui stop recovery review',
    },
    {
      href: 'native-ui-stop-recovery-test.json',
      label: 'native ui stop recovery test',
    },
    {
      href: 'native-vision-image-queue-audit.json',
      label: 'native vision image queue audit',
    },
    {
      href: 'native-vision-image-queue-current-progress.json',
      label: 'native vision image queue current progress',
    },
    {
      href: 'native-vision-image-queue-current-review.md',
      label: 'native vision image queue current review',
    },
    {
      href: 'native-vision-image-queue-progress.json',
      label: 'native vision image queue progress',
    },
    {
      href: 'native-vision-image-queue-review.md',
      label: 'native vision image queue review',
    },
    {
      href: 'native-vision-image-queue-test.json',
      label: 'native vision image queue test',
    },
    {
      href: 'native-wafer-transport-entry-audit.json',
      label: 'native wafer transport entry audit',
    },
    {
      href: 'native-wafer-transport-entry-current-progress.json',
      label: 'native wafer transport entry current progress',
    },
    {
      href: 'native-wafer-transport-entry-current-review.md',
      label: 'native wafer transport entry current review',
    },
    {
      href: 'native-wafer-transport-entry-progress.json',
      label: 'native wafer transport entry progress',
    },
    {
      href: 'native-wafer-transport-entry-review.md',
      label: 'native wafer transport entry review',
    },
    {
      href: 'native-wafer-transport-entry-test.json',
      label: 'native wafer transport entry test',
    },
    {
      href: 'node-isdo-work-audit.json',
      label: 'node isdo work audit',
    },
    {
      href: 'node-isdo-work-review.md',
      label: 'node isdo work review',
    },
    {
      href: 'noninterface-save-events-review.md',
      label: 'noninterface save events review',
    },
    {
      href: 'noninterface-save-events.json',
      label: 'noninterface save events',
    },
    {
      href: 'noninterface-save-targets.json',
      label: 'noninterface save targets',
    },
    {
      href: 'noninterface-save-targets.md',
      label: 'noninterface save targets',
    },
    {
      href: 'normal-start-integration-audit.json',
      label: 'normal start integration audit',
    },
    {
      href: 'normal-start-integration-current-progress.json',
      label: 'normal start integration current progress',
    },
    {
      href: 'normal-start-integration-current-review.md',
      label: 'normal start integration current review',
    },
    {
      href: 'normal-start-integration-evidence.json',
      label: 'normal start integration evidence',
    },
    {
      href: 'normal-start-integration-next-evidence.json',
      label: 'normal start integration next evidence',
    },
    {
      href: 'normal-start-integration-review.md',
      label: 'normal start integration review',
    },
    {
      href: 'normal-start-integration-test.json',
      label: 'normal start integration test',
    },
    {
      href: 'normal-start-integration-verification.json',
      label: 'normal start integration verification',
    },
    {
      href: 'nozzle-exchange-browser-check.json',
      label: 'nozzle exchange browser check',
    },
    {
      href: 'nozzle-exchange-evidence.json',
      label: 'nozzle exchange evidence',
    },
    {
      href: 'nozzle-exchange-source.html',
      label: 'nozzle exchange source',
    },
    {
      href: 'nozzle-exchange-test.json',
      label: 'nozzle exchange test',
    },
    {
      href: 'nozzle-exchange-workflow-review.md',
      label: 'nozzle exchange workflow review',
    },
    {
      href: 'nozzle-exchange.delivery.json',
      label: 'nozzle exchange.delivery',
    },
    {
      href: 'nozzle-exchange.graph-evidence.json',
      label: 'nozzle exchange.graph evidence',
    },
    {
      href: 'nozzle-exchange.html',
      label: 'nozzle exchange',
    },
    {
      href: 'nozzle-exchange.validation.json',
      label: 'nozzle exchange.validation',
    },
    {
      href: 'nozzle-exchange.visual-check.html',
      label: 'nozzle exchange.visual check',
    },
    {
      href: 'nozzle-exchange.visual-check.json',
      label: 'nozzle exchange.visual check',
    },
    {
      href: 'nozzle-exchange.visual-command.json',
      label: 'nozzle exchange.visual command',
    },
    {
      href: 'nozzle-exchange.visual-review.json',
      label: 'nozzle exchange.visual review',
    },
    {
      href: 'nozzle-exchange.workflow.archify.json',
      label: 'nozzle exchange.workflow.archify',
    },
    {
      href: 'official-net48-autofocusing-build-audit.json',
      label: 'official net48 autofocusing build audit',
    },
    {
      href: 'official-net48-autofocusing-build-review.md',
      label: 'official net48 autofocusing build review',
    },
    {
      href: 'official-net48-axiscompensate-build-audit.json',
      label: 'official net48 axiscompensate build audit',
    },
    {
      href: 'official-net48-axiscompensate-build-review.md',
      label: 'official net48 axiscompensate build review',
    },
    {
      href: 'official-net48-calibration-build-audit.json',
      label: 'official net48 calibration build audit',
    },
    {
      href: 'official-net48-calibration-build-progress.json',
      label: 'official net48 calibration build progress',
    },
    {
      href: 'official-net48-calibration-build-review.md',
      label: 'official net48 calibration build review',
    },
    {
      href: 'official-net48-changejson-build-audit.json',
      label: 'official net48 changejson build audit',
    },
    {
      href: 'official-net48-changejson-build-review.md',
      label: 'official net48 changejson build review',
    },
    {
      href: 'official-net48-changejson-zxvendor-build-audit.json',
      label: 'official net48 changejson zxvendor build audit',
    },
    {
      href: 'official-net48-changejson-zxvendor-build-review.md',
      label: 'official net48 changejson zxvendor build review',
    },
    {
      href: 'official-net48-coordinate-build-audit.json',
      label: 'official net48 coordinate build audit',
    },
    {
      href: 'official-net48-coordinate-build-review.md',
      label: 'official net48 coordinate build review',
    },
    {
      href: 'official-net48-dispense-build-audit.json',
      label: 'official net48 dispense build audit',
    },
    {
      href: 'official-net48-dispense-build-review.md',
      label: 'official net48 dispense build review',
    },
    {
      href: 'official-net48-dispense-zxvendor-build-audit.json',
      label: 'official net48 dispense zxvendor build audit',
    },
    {
      href: 'official-net48-dispense-zxvendor-build-review.md',
      label: 'official net48 dispense zxvendor build review',
    },
    {
      href: 'official-net48-interpolation-build-audit.json',
      label: 'official net48 interpolation build audit',
    },
    {
      href: 'official-net48-interpolation-build-review.md',
      label: 'official net48 interpolation build review',
    },
    {
      href: 'official-net48-interpolation-zxvendor-build-audit.json',
      label: 'official net48 interpolation zxvendor build audit',
    },
    {
      href: 'official-net48-interpolation-zxvendor-build-review.md',
      label: 'official net48 interpolation zxvendor build review',
    },
    {
      href: 'official-net48-logtest-build-audit.json',
      label: 'official net48 logtest build audit',
    },
    {
      href: 'official-net48-logtest-build-review.md',
      label: 'official net48 logtest build review',
    },
    {
      href: 'official-net48-machine-build-audit.json',
      label: 'official net48 machine build audit',
    },
    {
      href: 'official-net48-machine-build-review.md',
      label: 'official net48 machine build review',
    },
    {
      href: 'official-net48-machinesupport-build-audit.json',
      label: 'official net48 machinesupport build audit',
    },
    {
      href: 'official-net48-machinesupport-build-review.md',
      label: 'official net48 machinesupport build review',
    },
    {
      href: 'official-net48-prtest-build-audit.json',
      label: 'official net48 prtest build audit',
    },
    {
      href: 'official-net48-prtest-build-review.md',
      label: 'official net48 prtest build review',
    },
    {
      href: 'official-net48-prtest-zxvendor-build-audit.json',
      label: 'official net48 prtest zxvendor build audit',
    },
    {
      href: 'official-net48-prtest-zxvendor-build-review.md',
      label: 'official net48 prtest zxvendor build review',
    },
    {
      href: 'official-net48-realtimecurve-build-audit.json',
      label: 'official net48 realtimecurve build audit',
    },
    {
      href: 'official-net48-realtimecurve-build-review.md',
      label: 'official net48 realtimecurve build review',
    },
    {
      href: 'official-net48-realtimecurve-zxvendor-build-audit.json',
      label: 'official net48 realtimecurve zxvendor build audit',
    },
    {
      href: 'official-net48-realtimecurve-zxvendor-build-review.md',
      label: 'official net48 realtimecurve zxvendor build review',
    },
    {
      href: 'official-net48-softkey-build-audit.json',
      label: 'official net48 softkey build audit',
    },
    {
      href: 'official-net48-softkey-build-review.md',
      label: 'official net48 softkey build review',
    },
    {
      href: 'official-net48-teachtest-build-audit.json',
      label: 'official net48 teachtest build audit',
    },
    {
      href: 'official-net48-teachtest-build-review.md',
      label: 'official net48 teachtest build review',
    },
    {
      href: 'official-net48-zx2200-build-audit.json',
      label: 'official net48 zx2200 build audit',
    },
    {
      href: 'official-net48-zx2200-build-review.md',
      label: 'official net48 zx2200 build review',
    },
    {
      href: 'official-net48-zx2200-parameters-repair-audit.json',
      label: 'official net48 zx2200 parameters repair audit',
    },
    {
      href: 'official-net48-zx2200-parameters-repair-review.md',
      label: 'official net48 zx2200 parameters repair review',
    },
    {
      href: 'official-net48-zx2200-zxvendor-build-audit.json',
      label: 'official net48 zx2200 zxvendor build audit',
    },
    {
      href: 'official-net48-zx2200-zxvendor-build-review.md',
      label: 'official net48 zx2200 zxvendor build review',
    },
    {
      href: 'official-net48-zxvendor-input-audit.json',
      label: 'official net48 zxvendor input audit',
    },
    {
      href: 'official-net48-zxvendor-input-review.md',
      label: 'official net48 zxvendor input review',
    },
    {
      href: 'original-action-catalog-closure-audit.json',
      label: 'original action catalog closure audit',
    },
    {
      href: 'original-action-catalog-closure-progress.json',
      label: 'original action catalog closure progress',
    },
    {
      href: 'original-action-catalog-closure-review.md',
      label: 'original action catalog closure review',
    },
    {
      href: 'original-action-catalog-native-init-audit.json',
      label: 'original action catalog native init audit',
    },
    {
      href: 'original-action-catalog-native-init-progress.json',
      label: 'original action catalog native init progress',
    },
    {
      href: 'original-action-catalog-native-init-review.md',
      label: 'original action catalog native init review',
    },
    {
      href: 'original-s2-abort-thread-il-review.md',
      label: 'original s2 abort thread il review',
    },
    {
      href: 'original-s2-abort-thread-il.json',
      label: 'original s2 abort thread il',
    },
    {
      href: 'original-s2-close-cylinder-il-review.md',
      label: 'original s2 close cylinder il review',
    },
    {
      href: 'original-s2-close-cylinder-il.json',
      label: 'original s2 close cylinder il',
    },
    {
      href: 'original-s2-incoming-signal-il-review.md',
      label: 'original s2 incoming signal il review',
    },
    {
      href: 'original-s2-incoming-signal-il.json',
      label: 'original s2 incoming signal il',
    },
    {
      href: 'original-s2-reset-il-review.md',
      label: 'original s2 reset il review',
    },
    {
      href: 'original-s2-reset-il.json',
      label: 'original s2 reset il',
    },
    {
      href: 'original-s2-selfcheck-il-review.md',
      label: 'original s2 selfcheck il review',
    },
    {
      href: 'original-s2-selfcheck-il.json',
      label: 'original s2 selfcheck il',
    },
    {
      href: 'original-s2-send-away-il-review.md',
      label: 'original s2 send away il review',
    },
    {
      href: 'original-s2-send-away-il.json',
      label: 'original s2 send away il',
    },
    {
      href: 'original-s2-start-il-review.md',
      label: 'original s2 start il review',
    },
    {
      href: 'original-s2-start-il.json',
      label: 'original s2 start il',
    },
    {
      href: 'original-s2-start-worker-il-review.md',
      label: 'original s2 start worker il review',
    },
    {
      href: 'original-s2-start-worker-il.json',
      label: 'original s2 start worker il',
    },
    {
      href: 'original-semantic-graph-audit.json',
      label: 'original semantic graph audit',
    },
    {
      href: 'original-semantic-graph-progress.json',
      label: 'original semantic graph progress',
    },
    {
      href: 'original-semantic-graph-review.md',
      label: 'original semantic graph review',
    },
    {
      href: 'original-semantic-graph-test.json',
      label: 'original semantic graph test',
    },
    {
      href: 'original-source-artifact-reference-closure-progress.json',
      label: 'original source artifact reference closure progress',
    },
    {
      href: 'original-source-artifact-reference-closure-repair-audit.json',
      label: 'original source artifact reference closure repair audit',
    },
    {
      href: 'original-source-artifact-reference-closure-repair-progress.json',
      label: 'original source artifact reference closure repair progress',
    },
    {
      href: 'original-source-artifact-reference-closure-repair-review.md',
      label: 'original source artifact reference closure repair review',
    },
    {
      href: 'original-source-artifact-reference-closure-review.md',
      label: 'original source artifact reference closure review',
    },
    {
      href: 'original-source-artifact-reference-declaration-audit.json',
      label: 'original source artifact reference declaration audit',
    },
    {
      href: 'original-source-artifact-reference-declaration-review.md',
      label: 'original source artifact reference declaration review',
    },
    {
      href: 'original-system2-domain-native-audit.json',
      label: 'original system2 domain native audit',
    },
    {
      href: 'original-system2-domain-native-progress.json',
      label: 'original system2 domain native progress',
    },
    {
      href: 'original-system2-domain-native-review.md',
      label: 'original system2 domain native review',
    },
    {
      href: 'outer-task-restart-pending-evidence.json',
      label: 'outer task restart pending evidence',
    },
    {
      href: 'outer-transport-task-audit.json',
      label: 'outer transport task audit',
    },
    {
      href: 'outer-transport-task-current-progress.json',
      label: 'outer transport task current progress',
    },
    {
      href: 'outer-transport-task-current-review.md',
      label: 'outer transport task current review',
    },
    {
      href: 'outer-transport-task-integration-verification.json',
      label: 'outer transport task integration verification',
    },
    {
      href: 'outer-transport-task-review.md',
      label: 'outer transport task review',
    },
    {
      href: 'outer-transport-task-test.json',
      label: 'outer transport task test',
    },
    {
      href: 'parameter-roundtrip-audit.json',
      label: 'parameter roundtrip audit',
    },
    {
      href: 'parameter-roundtrip-test.json',
      label: 'parameter roundtrip test',
    },
    {
      href: 'pattern-roundtrip-audit.json',
      label: 'pattern roundtrip audit',
    },
    {
      href: 'pattern-roundtrip-test.json',
      label: 'pattern roundtrip test',
    },
    {
      href: 'pause-downstream-next-checks.json',
      label: 'pause downstream next checks',
    },
    {
      href: 'permission-gating-audit.json',
      label: 'permission gating audit',
    },
    {
      href: 'permission-gating-review.md',
      label: 'permission gating review',
    },
    {
      href: 'permission-session-audit.json',
      label: 'permission session audit',
    },
    {
      href: 'permission-session-review.md',
      label: 'permission session review',
    },
    {
      href: 'permission-weaving-audit.json',
      label: 'permission weaving audit',
    },
    {
      href: 'permission-weaving-review.md',
      label: 'permission weaving review',
    },
    {
      href: 'persistence-dependency-boundary.json',
      label: 'persistence dependency boundary',
    },
    {
      href: 'persistence-dependency-boundary.md',
      label: 'persistence dependency boundary',
    },
    {
      href: 'persistence-failure-boundary-review.md',
      label: 'persistence failure boundary review',
    },
    {
      href: 'persistence-save-binary-evidence.json',
      label: 'persistence save binary evidence',
    },
    {
      href: 'persistence-save-contract-review.md',
      label: 'persistence save contract review',
    },
    {
      href: 'pickup-review-evidence.json',
      label: 'pickup review evidence',
    },
    {
      href: 'pickup-semantic-revalidation.md',
      label: 'pickup semantic revalidation',
    },
    {
      href: 'pickup-workflow.archify.json',
      label: 'pickup workflow.archify',
    },
    {
      href: 'pickup-workflow.browser-check.json',
      label: 'pickup workflow.browser check',
    },
    {
      href: 'pickup-workflow.delivery.json',
      label: 'pickup workflow.delivery',
    },
    {
      href: 'pickup-workflow.html',
      label: 'pickup workflow',
    },
    {
      href: 'pickup-workflow.visual-check.html',
      label: 'pickup workflow.visual check',
    },
    {
      href: 'pickup-workflow.visual-check.json',
      label: 'pickup workflow.visual check',
    },
    {
      href: 'plate-teaching-browser-check.json',
      label: 'plate teaching browser check',
    },
    {
      href: 'plate-teaching-evidence.json',
      label: 'plate teaching evidence',
    },
    {
      href: 'plate-teaching-source.html',
      label: 'plate teaching source',
    },
    {
      href: 'plate-teaching-test.json',
      label: 'plate teaching test',
    },
    {
      href: 'plate-teaching-workflow-review.md',
      label: 'plate teaching workflow review',
    },
    {
      href: 'portal-verification.json',
      label: 'portal verification',
    },
    {
      href: 'postbond-compensation-test.json',
      label: 'postbond compensation test',
    },
    {
      href: 'postbond-feedback-diagram-status.json',
      label: 'postbond feedback diagram status',
    },
    {
      href: 'postbond-feedback-evidence.json',
      label: 'postbond feedback evidence',
    },
    {
      href: 'postbond-feedback-source-review.md',
      label: 'postbond feedback source review',
    },
    {
      href: 'postbond-feedback-workflow.archify.json',
      label: 'postbond feedback workflow.archify',
    },
    {
      href: 'postbond-feedback-workflow.html',
      label: 'postbond feedback workflow',
    },
    {
      href: 'postbond-feedback-workflow.visual-check.html',
      label: 'postbond feedback workflow.visual check',
    },
    {
      href: 'postbond-feedback-workflow.visual-check.json',
      label: 'postbond feedback workflow.visual check',
    },
    {
      href: 'pr-test-module-review.md',
      label: 'pr test module review',
    },
    {
      href: 'pretreatment-audit.json',
      label: 'pretreatment audit',
    },
    {
      href: 'pretreatment-test.json',
      label: 'pretreatment test',
    },
    {
      href: 'process-gate-composition-current-progress.json',
      label: 'process gate composition current progress',
    },
    {
      href: 'process-gate-composition-current-review.md',
      label: 'process gate composition current review',
    },
    {
      href: 'process-gate-composition-test.json',
      label: 'process gate composition test',
    },
    {
      href: 'process-start-gate-current-progress.json',
      label: 'process start gate current progress',
    },
    {
      href: 'process-start-gate-current-review.md',
      label: 'process start gate current review',
    },
    {
      href: 'process-start-gate-test.json',
      label: 'process start gate test',
    },
    {
      href: 'process-step-injection-audit.json',
      label: 'process step injection audit',
    },
    {
      href: 'process-step-injection-review.md',
      label: 'process step injection review',
    },
    {
      href: 'product-config-native-source-audit.json',
      label: 'product config native source audit',
    },
    {
      href: 'product-config-native-source-current-progress.json',
      label: 'product config native source current progress',
    },
    {
      href: 'product-config-native-source-current-review.md',
      label: 'product config native source current review',
    },
    {
      href: 'product-config-native-source-progress.json',
      label: 'product config native source progress',
    },
    {
      href: 'product-config-native-source-review.md',
      label: 'product config native source review',
    },
    {
      href: 'product-config-native-source-test.json',
      label: 'product config native source test',
    },
    {
      href: 'product-opposite-lifecycle-audit.json',
      label: 'product opposite lifecycle audit',
    },
    {
      href: 'product-opposite-lifecycle-current-progress.json',
      label: 'product opposite lifecycle current progress',
    },
    {
      href: 'product-opposite-lifecycle-current-review.md',
      label: 'product opposite lifecycle current review',
    },
    {
      href: 'product-opposite-lifecycle-test.json',
      label: 'product opposite lifecycle test',
    },
    {
      href: 'production-domain-readiness-review.md',
      label: 'production domain readiness review',
    },
    {
      href: 'production-edit-gating-review.md',
      label: 'production edit gating review',
    },
    {
      href: 'production-readiness-delegates-review.md',
      label: 'production readiness delegates review',
    },
    {
      href: 'production-start-callchain-review.md',
      label: 'production start callchain review',
    },
    {
      href: 'production-start-launch-current-progress.json',
      label: 'production start launch current progress',
    },
    {
      href: 'production-start-launch-current-review.md',
      label: 'production start launch current review',
    },
    {
      href: 'production-start-launch-evidence.json',
      label: 'production start launch evidence',
    },
    {
      href: 'production-start-launch-review.md',
      label: 'production start launch review',
    },
    {
      href: 'production-start-readiness-review.md',
      label: 'production start readiness review',
    },
    {
      href: 'production-task-start-gates-review.md',
      label: 'production task start gates review',
    },
    {
      href: 'programming-confirm-bodies.json',
      label: 'programming confirm bodies',
    },
    {
      href: 'programming-confirm-bodies.md',
      label: 'programming confirm bodies',
    },
    {
      href: 'programming-confirm-browser-check.json',
      label: 'programming confirm browser check',
    },
    {
      href: 'programming-confirm-review.json',
      label: 'programming confirm review',
    },
    {
      href: 'programming-confirm-review.md',
      label: 'programming confirm review',
    },
    {
      href: 'programming-confirm-save-targets.json',
      label: 'programming confirm save targets',
    },
    {
      href: 'programming-confirm-save-targets.md',
      label: 'programming confirm save targets',
    },
    {
      href: 'programming-dialog-save-closure-review.md',
      label: 'programming dialog save closure review',
    },
    {
      href: 'programming-dialog-save-closure.json',
      label: 'programming dialog save closure',
    },
    {
      href: 'programming-display-pages.json',
      label: 'programming display pages',
    },
    {
      href: 'programming-display-pages.md',
      label: 'programming display pages',
    },
    {
      href: 'programming-external-dialog-il-review.md',
      label: 'programming external dialog il review',
    },
    {
      href: 'programming-external-dialog-il.json',
      label: 'programming external dialog il',
    },
    {
      href: 'programming-page-inventory.json',
      label: 'programming page inventory',
    },
    {
      href: 'programming-page-inventory.md',
      label: 'programming page inventory',
    },
    {
      href: 'programming-page-save-review.md',
      label: 'programming page save review',
    },
    {
      href: 'project-assets-review.md',
      label: 'project assets review',
    },
    {
      href: 'project-assets.json',
      label: 'project assets',
    },
    {
      href: 'project-dependency-baseline.json',
      label: 'project dependency baseline',
    },
    {
      href: 'project-dependency-baseline.md',
      label: 'project dependency baseline',
    },
    {
      href: 'project-plan-status.md',
      label: 'project plan status',
    },
    {
      href: 'project-resources-audit.json',
      label: 'project resources audit',
    },
    {
      href: 'project-resources-progress.json',
      label: 'project resources progress',
    },
    {
      href: 'project-resources-review.md',
      label: 'project resources review',
    },
    {
      href: 'project-resources-test.json',
      label: 'project resources test',
    },
    {
      href: 'properties-module-review.md',
      label: 'properties module review',
    },
    {
      href: 'properties-resource-audit.json',
      label: 'properties resource audit',
    },
    {
      href: 'readiness-helpers-audit.json',
      label: 'readiness helpers audit',
    },
    {
      href: 'readiness-helpers-current-progress.json',
      label: 'readiness helpers current progress',
    },
    {
      href: 'readiness-helpers-current-review.md',
      label: 'readiness helpers current review',
    },
    {
      href: 'readiness-helpers-evidence.json',
      label: 'readiness helpers evidence',
    },
    {
      href: 'readiness-helpers-next-evidence.json',
      label: 'readiness helpers next evidence',
    },
    {
      href: 'readiness-helpers-review.md',
      label: 'readiness helpers review',
    },
    {
      href: 'readiness-helpers-test.json',
      label: 'readiness helpers test',
    },
    {
      href: 'readiness-helpers-verification.json',
      label: 'readiness helpers verification',
    },
    {
      href: 'recipe-deletion-backup-source-review.md',
      label: 'recipe deletion backup source review',
    },
    {
      href: 'recipe-domain-reconstruction-audit.json',
      label: 'recipe domain reconstruction audit',
    },
    {
      href: 'recipe-domain-reconstruction-review.md',
      label: 'recipe domain reconstruction review',
    },
    {
      href: 'recipe-initialization-source-review.md',
      label: 'recipe initialization source review',
    },
    {
      href: 'recipe-initialization-validation.json',
      label: 'recipe initialization validation',
    },
    {
      href: 'recipe-initialization-workflow.archify.json',
      label: 'recipe initialization workflow.archify',
    },
    {
      href: 'recipe-lifecycle-analysis.md',
      label: 'recipe lifecycle analysis',
    },
    {
      href: 'recipe-lifecycle-workflow.archify.json',
      label: 'recipe lifecycle workflow.archify',
    },
    {
      href: 'recipe-lifecycle-workflow.html',
      label: 'recipe lifecycle workflow',
    },
    {
      href: 'recipe-readiness-gate-current-progress.json',
      label: 'recipe readiness gate current progress',
    },
    {
      href: 'recipe-readiness-gate-current-review.md',
      label: 'recipe readiness gate current review',
    },
    {
      href: 'recipe-readiness-start-gate-evidence.json',
      label: 'recipe readiness start gate evidence',
    },
    {
      href: 'recipe-readiness-start-gate-review.md',
      label: 'recipe readiness start gate review',
    },
    {
      href: 'recipe-switch-failure-evidence.json',
      label: 'recipe switch failure evidence',
    },
    {
      href: 'recipe-switch-failure-review.md',
      label: 'recipe switch failure review',
    },
    {
      href: 'recipe-switch-sequence-status.json',
      label: 'recipe switch sequence status',
    },
    {
      href: 'recipe-switch-sequence.archify.json',
      label: 'recipe switch sequence.archify',
    },
    {
      href: 'recipe-switch-sequence.html',
      label: 'recipe switch sequence',
    },
    {
      href: 'recipe-switch-sequence.visual-check.html',
      label: 'recipe switch sequence.visual check',
    },
    {
      href: 'recipe-switch-sequence.visual-check.json',
      label: 'recipe switch sequence.visual check',
    },
    {
      href: 'relative-bond-order-audit.json',
      label: 'relative bond order audit',
    },
    {
      href: 'relative-bond-order-review.md',
      label: 'relative bond order review',
    },
    {
      href: 'remaining-node-early-boundary-audit.json',
      label: 'remaining node early boundary audit',
    },
    {
      href: 'remaining-node-early-boundary-review.md',
      label: 'remaining node early boundary review',
    },
    {
      href: 'repository-delete-audit.json',
      label: 'repository delete audit',
    },
    {
      href: 'repository-delete-test.json',
      label: 'repository delete test',
    },
    {
      href: 'resource-images-review.md',
      label: 'resource images review',
    },
    {
      href: 'resource-images-test.json',
      label: 'resource images test',
    },
    {
      href: 'resx-references-review.md',
      label: 'resx references review',
    },
    {
      href: 'resx-references.json',
      label: 'resx references',
    },
    {
      href: 'runtime-dataflow-analysis.md',
      label: 'runtime dataflow analysis',
    },
    {
      href: 'runtime-dataflow.archify.json',
      label: 'runtime dataflow.archify',
    },
    {
      href: 'runtime-dataflow.html',
      label: 'runtime dataflow',
    },
    {
      href: 's1-action-behavior-review.md',
      label: 's1 action behavior review',
    },
    {
      href: 's1-task-integration-audit.json',
      label: 's1 task integration audit',
    },
    {
      href: 's1-task-integration-current-progress.json',
      label: 's1 task integration current progress',
    },
    {
      href: 's1-task-integration-current-review.md',
      label: 's1 task integration current review',
    },
    {
      href: 's1-task-integration-review.md',
      label: 's1 task integration review',
    },
    {
      href: 's1-task-integration-test.json',
      label: 's1 task integration test',
    },
    {
      href: 's2-context-update-current-progress.json',
      label: 's2 context update current progress',
    },
    {
      href: 's2-context-update-current-review.md',
      label: 's2 context update current review',
    },
    {
      href: 's2-context-update-test.json',
      label: 's2 context update test',
    },
    {
      href: 's2-door-pause-audit.json',
      label: 's2 door pause audit',
    },
    {
      href: 's2-door-pause-current-progress.json',
      label: 's2 door pause current progress',
    },
    {
      href: 's2-door-pause-current-review.md',
      label: 's2 door pause current review',
    },
    {
      href: 's2-door-pause-integration-verification.json',
      label: 's2 door pause integration verification',
    },
    {
      href: 's2-door-pause-review.md',
      label: 's2 door pause review',
    },
    {
      href: 's2-door-pause-test.json',
      label: 's2 door pause test',
    },
    {
      href: 's2-flip-slide-start-audit.json',
      label: 's2 flip slide start audit',
    },
    {
      href: 's2-flip-slide-start-review.md',
      label: 's2 flip slide start review',
    },
    {
      href: 's2-node-selection-current-progress.json',
      label: 's2 node selection current progress',
    },
    {
      href: 's2-node-selection-current-review.md',
      label: 's2 node selection current review',
    },
    {
      href: 's2-node-selection-test.json',
      label: 's2 node selection test',
    },
    {
      href: 's2-predispense-allocation-current-progress.json',
      label: 's2 predispense allocation current progress',
    },
    {
      href: 's2-predispense-allocation-current-review.md',
      label: 's2 predispense allocation current review',
    },
    {
      href: 's2-predispense-allocation-test.json',
      label: 's2 predispense allocation test',
    },
    {
      href: 's2-predispense-retry.delivery.json',
      label: 's2 predispense retry.delivery',
    },
    {
      href: 's2-predispense-retry.evidence.json',
      label: 's2 predispense retry.evidence',
    },
    {
      href: 's2-predispense-retry.sequence.archify.json',
      label: 's2 predispense retry.sequence.archify',
    },
    {
      href: 's2-predispense-retry.sequence.html',
      label: 's2 predispense retry.sequence',
    },
    {
      href: 's2-predispense-retry.sequence.visual-check.html',
      label: 's2 predispense retry.sequence.visual check',
    },
    {
      href: 's2-predispense-retry.sequence.visual-check.json',
      label: 's2 predispense retry.sequence.visual check',
    },
    {
      href: 's2-reset-normal-audit.json',
      label: 's2 reset normal audit',
    },
    {
      href: 's2-reset-normal-review.md',
      label: 's2 reset normal review',
    },
    {
      href: 's2-self-check-audit.json',
      label: 's2 self check audit',
    },
    {
      href: 's2-self-check-current-progress.json',
      label: 's2 self check current progress',
    },
    {
      href: 's2-self-check-current-review.md',
      label: 's2 self check current review',
    },
    {
      href: 's2-self-check-review.md',
      label: 's2 self check review',
    },
    {
      href: 's2-task-integration-audit.json',
      label: 's2 task integration audit',
    },
    {
      href: 's2-task-integration-current-progress.json',
      label: 's2 task integration current progress',
    },
    {
      href: 's2-task-integration-current-review.md',
      label: 's2 task integration current review',
    },
    {
      href: 's2-task-integration-review.md',
      label: 's2 task integration review',
    },
    {
      href: 's2-task-integration-test.json',
      label: 's2 task integration test',
    },
    {
      href: 'safe-door-pause-audit.json',
      label: 'safe door pause audit',
    },
    {
      href: 'safe-door-pause-current-progress.json',
      label: 'safe door pause current progress',
    },
    {
      href: 'safe-door-pause-current-review.md',
      label: 'safe door pause current review',
    },
    {
      href: 'safe-door-pause-integration-verification.json',
      label: 'safe door pause integration verification',
    },
    {
      href: 'safe-door-pause-review.md',
      label: 'safe door pause review',
    },
    {
      href: 'safe-door-pause-test.json',
      label: 'safe door pause test',
    },
    {
      href: 'safe-motion-browser-check.json',
      label: 'safe motion browser check',
    },
    {
      href: 'safe-motion-current-progress.json',
      label: 'safe motion current progress',
    },
    {
      href: 'safe-motion-current-review.md',
      label: 'safe motion current review',
    },
    {
      href: 'safe-motion-evidence.json',
      label: 'safe motion evidence',
    },
    {
      href: 'safe-motion-source.html',
      label: 'safe motion source',
    },
    {
      href: 'safe-motion-test.json',
      label: 'safe motion test',
    },
    {
      href: 'safe-motion-workflow-review.md',
      label: 'safe motion workflow review',
    },
    {
      href: 'safe-motion.delivery.json',
      label: 'safe motion.delivery',
    },
    {
      href: 'safe-motion.graph-evidence.json',
      label: 'safe motion.graph evidence',
    },
    {
      href: 'safe-motion.html',
      label: 'safe motion',
    },
    {
      href: 'safe-motion.visual-check.html',
      label: 'safe motion.visual check',
    },
    {
      href: 'safe-motion.visual-check.json',
      label: 'safe motion.visual check',
    },
    {
      href: 'safe-motion.visual-review.json',
      label: 'safe motion.visual review',
    },
    {
      href: 'safe-motion.workflow.archify.json',
      label: 'safe motion.workflow.archify',
    },
    {
      href: 'safety-door-pause-current-progress.json',
      label: 'safety door pause current progress',
    },
    {
      href: 'safety-door-pause-current-review.md',
      label: 'safety door pause current review',
    },
    {
      href: 'semantic-revalidations.json',
      label: 'semantic revalidations',
    },
    {
      href: 'semantic-reviews.json',
      label: 'semantic reviews',
    },
    {
      href: 'semantic-source-reader-audit.json',
      label: 'semantic source reader audit',
    },
    {
      href: 'semantic-source-reader-evidence.json',
      label: 'semantic source reader evidence',
    },
    {
      href: 'semantic-source-reader-progress.json',
      label: 'semantic source reader progress',
    },
    {
      href: 'semantic-source-reader-review.md',
      label: 'semantic source reader review',
    },
    {
      href: 'semantic-source-reader-test.json',
      label: 'semantic source reader test',
    },
    {
      href: 'showcase-v1.html',
      label: 'showcase v1',
    },
    {
      href: 'showcase-v1.receipt.json',
      label: 'showcase v1.receipt',
    },
    {
      href: 'signal-handshake-review.md',
      label: 'signal handshake review',
    },
    {
      href: 'signal-inventory.json',
      label: 'signal inventory',
    },
    {
      href: 'single-step-door-audit.json',
      label: 'single step door audit',
    },
    {
      href: 'single-step-door-integration-verification.json',
      label: 'single step door integration verification',
    },
    {
      href: 'single-step-door-review.md',
      label: 'single step door review',
    },
    {
      href: 'single-step-door-test.json',
      label: 'single step door test',
    },
    {
      href: 'singleton-load-audit.json',
      label: 'singleton load audit',
    },
    {
      href: 'singleton-load-current-progress.json',
      label: 'singleton load current progress',
    },
    {
      href: 'singleton-load-current-review.md',
      label: 'singleton load current review',
    },
    {
      href: 'singleton-load-probe-audit.json',
      label: 'singleton load probe audit',
    },
    {
      href: 'singleton-load-probe-review.md',
      label: 'singleton load probe review',
    },
    {
      href: 'singleton-load-review.md',
      label: 'singleton load review',
    },
    {
      href: 'singleton-load-test.json',
      label: 'singleton load test',
    },
    {
      href: 'software-build-validation.md',
      label: 'software build validation',
    },
    {
      href: 'source-coverage-audit.json',
      label: 'source coverage audit',
    },
    {
      href: 'source-coverage-audit.md',
      label: 'source coverage audit',
    },
    {
      href: 'source-encoding-fidelity-audit.json',
      label: 'source encoding fidelity audit',
    },
    {
      href: 'source-encoding-fidelity-progress.json',
      label: 'source encoding fidelity progress',
    },
    {
      href: 'source-encoding-fidelity-review.md',
      label: 'source encoding fidelity review',
    },
    {
      href: 'source-encoding-fidelity-test.json',
      label: 'source encoding fidelity test',
    },
    {
      href: 'source-evidence.json',
      label: 'source evidence',
    },
    {
      href: 'source-explorer-handoff.md',
      label: 'source explorer handoff',
    },
    {
      href: 'source-module-inventory.json',
      label: 'source module inventory',
    },
    {
      href: 'source-module-inventory.md',
      label: 'source module inventory',
    },
    {
      href: 'standalone-camera-calibration-source-review.md',
      label: 'standalone camera calibration source review',
    },
    {
      href: 'startup-call-review.md',
      label: 'startup call review',
    },
    {
      href: 'startup-call-sites.json',
      label: 'startup call sites',
    },
    {
      href: 'startup-config-audit.json',
      label: 'startup config audit',
    },
    {
      href: 'startup-config-review.md',
      label: 'startup config review',
    },
    {
      href: 'startup-config-test.json',
      label: 'startup config test',
    },
    {
      href: 'startup-entry-audit.json',
      label: 'startup entry audit',
    },
    {
      href: 'startup-entry-review.md',
      label: 'startup entry review',
    },
    {
      href: 'startup-entry-test.json',
      label: 'startup entry test',
    },
    {
      href: 'startup-semantic-revalidation.md',
      label: 'startup semantic revalidation',
    },
    {
      href: 'startup-workflow.archify.json',
      label: 'startup workflow.archify',
    },
    {
      href: 'startup-workflow.delivery.json',
      label: 'startup workflow.delivery',
    },
    {
      href: 'startup-workflow.html',
      label: 'startup workflow',
    },
    {
      href: 'startup-workflow.validation.json',
      label: 'startup workflow.validation',
    },
    {
      href: 'startup-workflow.visual-check.html',
      label: 'startup workflow.visual check',
    },
    {
      href: 'startup-workflow.visual-check.json',
      label: 'startup workflow.visual check',
    },
    {
      href: 'state-queue-failure-current-progress.json',
      label: 'state queue failure current progress',
    },
    {
      href: 'state-queue-failure-current-review.md',
      label: 'state queue failure current review',
    },
    {
      href: 'state-queue-failure-evidence.json',
      label: 'state queue failure evidence',
    },
    {
      href: 'state-queue-failure-review.md',
      label: 'state queue failure review',
    },
    {
      href: 'statistics-data-module-review.md',
      label: 'statistics data module review',
    },
    {
      href: 'stop-cleanup-review.md',
      label: 'stop cleanup review',
    },
    {
      href: 'stop-cleanup-workflow.archify.json',
      label: 'stop cleanup workflow.archify',
    },
    {
      href: 'stop-cleanup-workflow.delivery.json',
      label: 'stop cleanup workflow.delivery',
    },
    {
      href: 'stop-cleanup-workflow.html',
      label: 'stop cleanup workflow',
    },
    {
      href: 'stop-cleanup-workflow.validation.json',
      label: 'stop cleanup workflow.validation',
    },
    {
      href: 'stop-cleanup-workflow.visual-check.html',
      label: 'stop cleanup workflow.visual check',
    },
    {
      href: 'stop-cleanup-workflow.visual-check.json',
      label: 'stop cleanup workflow.visual check',
    },
    {
      href: 'stop-shutdown-lifecycle-review.md',
      label: 'stop shutdown lifecycle review',
    },
    {
      href: 'substrate-navigation-test.json',
      label: 'substrate navigation test',
    },
    {
      href: 'task-closure-audit.json',
      label: 'task closure audit',
    },
    {
      href: 'task-closure-current-progress.json',
      label: 'task closure current progress',
    },
    {
      href: 'task-closure-current-review.md',
      label: 'task closure current review',
    },
    {
      href: 'task-closure-review.md',
      label: 'task closure review',
    },
    {
      href: 'task-closure-test.json',
      label: 'task closure test',
    },
    {
      href: 'task-exception-audit.json',
      label: 'task exception audit',
    },
    {
      href: 'task-lifecycle-probe-audit.json',
      label: 'task lifecycle probe audit',
    },
    {
      href: 'task-lifecycle-probe-review.md',
      label: 'task lifecycle probe review',
    },
    {
      href: 'task-start-concurrency-current-progress.json',
      label: 'task start concurrency current progress',
    },
    {
      href: 'task-start-concurrency-current-review.md',
      label: 'task start concurrency current review',
    },
    {
      href: 'task-start-concurrency-evidence.json',
      label: 'task start concurrency evidence',
    },
    {
      href: 'task-start-concurrency-review.md',
      label: 'task start concurrency review',
    },
    {
      href: 'teach-navigation-windows-test.json',
      label: 'teach navigation windows test',
    },
    {
      href: 'teach-test-module-review.md',
      label: 'teach test module review',
    },
    {
      href: 'teach-test-navigation-audit.json',
      label: 'teach test navigation audit',
    },
    {
      href: 'teach-test-navigation-review.md',
      label: 'teach test navigation review',
    },
    {
      href: 'tool-teaching-browser-check.json',
      label: 'tool teaching browser check',
    },
    {
      href: 'tool-teaching-evidence.json',
      label: 'tool teaching evidence',
    },
    {
      href: 'tool-teaching-source.html',
      label: 'tool teaching source',
    },
    {
      href: 'tool-teaching-state-review.md',
      label: 'tool teaching state review',
    },
    {
      href: 'tool-teaching-test.json',
      label: 'tool teaching test',
    },
    {
      href: 'transform-select-audit.json',
      label: 'transform select audit',
    },
    {
      href: 'transform-select-test.json',
      label: 'transform select test',
    },
    {
      href: 'transport-auto-loader-integration-audit.json',
      label: 'transport auto loader integration audit',
    },
    {
      href: 'transport-auto-loader-integration-current-progress.json',
      label: 'transport auto loader integration current progress',
    },
    {
      href: 'transport-auto-loader-integration-current-review.md',
      label: 'transport auto loader integration current review',
    },
    {
      href: 'transport-auto-loader-integration-evidence.json',
      label: 'transport auto loader integration evidence',
    },
    {
      href: 'transport-auto-loader-integration-review.md',
      label: 'transport auto loader integration review',
    },
    {
      href: 'transport-auto-loader-integration-test.json',
      label: 'transport auto loader integration test',
    },
    {
      href: 'transport-auto-loader-integration-verification.json',
      label: 'transport auto loader integration verification',
    },
    {
      href: 'transport-auto-loader-next-evidence.json',
      label: 'transport auto loader next evidence',
    },
    {
      href: 'transport-auto-unloader-integration-audit.json',
      label: 'transport auto unloader integration audit',
    },
    {
      href: 'transport-auto-unloader-integration-current-progress.json',
      label: 'transport auto unloader integration current progress',
    },
    {
      href: 'transport-auto-unloader-integration-current-review.md',
      label: 'transport auto unloader integration current review',
    },
    {
      href: 'transport-auto-unloader-integration-evidence.json',
      label: 'transport auto unloader integration evidence',
    },
    {
      href: 'transport-auto-unloader-integration-review.md',
      label: 'transport auto unloader integration review',
    },
    {
      href: 'transport-auto-unloader-integration-test.json',
      label: 'transport auto unloader integration test',
    },
    {
      href: 'transport-auto-unloader-integration-verification.json',
      label: 'transport auto unloader integration verification',
    },
    {
      href: 'transport-auto-unloader-next-evidence.json',
      label: 'transport auto unloader next evidence',
    },
    {
      href: 'transport-auto-unloader-sdk-evidence.json',
      label: 'transport auto unloader sdk evidence',
    },
    {
      href: 'transport-bin-integration-audit.json',
      label: 'transport bin integration audit',
    },
    {
      href: 'transport-bin-integration-current-progress.json',
      label: 'transport bin integration current progress',
    },
    {
      href: 'transport-bin-integration-current-review.md',
      label: 'transport bin integration current review',
    },
    {
      href: 'transport-bin-integration-evidence.json',
      label: 'transport bin integration evidence',
    },
    {
      href: 'transport-bin-integration-review.md',
      label: 'transport bin integration review',
    },
    {
      href: 'transport-bin-integration-test.json',
      label: 'transport bin integration test',
    },
    {
      href: 'transport-bin-integration-verification.json',
      label: 'transport bin integration verification',
    },
    {
      href: 'transport-bin-next-evidence.json',
      label: 'transport bin next evidence',
    },
    {
      href: 'transport-bin-sdk-evidence.json',
      label: 'transport bin sdk evidence',
    },
    {
      href: 'transport-bond-integration-audit.json',
      label: 'transport bond integration audit',
    },
    {
      href: 'transport-bond-integration-current-progress.json',
      label: 'transport bond integration current progress',
    },
    {
      href: 'transport-bond-integration-current-review.md',
      label: 'transport bond integration current review',
    },
    {
      href: 'transport-bond-integration-evidence.json',
      label: 'transport bond integration evidence',
    },
    {
      href: 'transport-bond-integration-review.md',
      label: 'transport bond integration review',
    },
    {
      href: 'transport-bond-integration-test.json',
      label: 'transport bond integration test',
    },
    {
      href: 'transport-bond-integration-verification.json',
      label: 'transport bond integration verification',
    },
    {
      href: 'transport-carrier-map-baseline-test.json',
      label: 'transport carrier map baseline test',
    },
    {
      href: 'transport-carrier-map-branch1292-audit.json',
      label: 'transport carrier map branch1292 audit',
    },
    {
      href: 'transport-carrier-map-branch1292-test.json',
      label: 'transport carrier map branch1292 test',
    },
    {
      href: 'transport-carrier-map-integration-audit.json',
      label: 'transport carrier map integration audit',
    },
    {
      href: 'transport-carrier-map-integration-branch-audit.json',
      label: 'transport carrier map integration branch audit',
    },
    {
      href: 'transport-carrier-map-integration-branch-review.md',
      label: 'transport carrier map integration branch review',
    },
    {
      href: 'transport-carrier-map-integration-current-progress.json',
      label: 'transport carrier map integration current progress',
    },
    {
      href: 'transport-carrier-map-integration-current-review.md',
      label: 'transport carrier map integration current review',
    },
    {
      href: 'transport-carrier-map-integration-evidence.json',
      label: 'transport carrier map integration evidence',
    },
    {
      href: 'transport-carrier-map-integration-progress.json',
      label: 'transport carrier map integration progress',
    },
    {
      href: 'transport-carrier-map-integration-review.md',
      label: 'transport carrier map integration review',
    },
    {
      href: 'transport-carrier-map-integration-test.json',
      label: 'transport carrier map integration test',
    },
    {
      href: 'transport-carrier-map-integration-verification.json',
      label: 'transport carrier map integration verification',
    },
    {
      href: 'transport-carrier-map-log-sdk-current-progress.json',
      label: 'transport carrier map log sdk current progress',
    },
    {
      href: 'transport-carrier-map-log-sdk-current-review.md',
      label: 'transport carrier map log sdk current review',
    },
    {
      href: 'transport-carrier-map-log-sdk-evidence.json',
      label: 'transport carrier map log sdk evidence',
    },
    {
      href: 'transport-carrier-map-next-evidence.json',
      label: 'transport carrier map next evidence',
    },
    {
      href: 'transport-config-guard-current-progress.json',
      label: 'transport config guard current progress',
    },
    {
      href: 'transport-config-guard-current-review.md',
      label: 'transport config guard current review',
    },
    {
      href: 'transport-config-guard-test.json',
      label: 'transport config guard test',
    },
    {
      href: 'transport-controller-next-evidence.json',
      label: 'transport controller next evidence',
    },
    {
      href: 'transport-coordinate-product-integration-audit.json',
      label: 'transport coordinate product integration audit',
    },
    {
      href: 'transport-coordinate-product-integration-current-progress.json',
      label: 'transport coordinate product integration current progress',
    },
    {
      href: 'transport-coordinate-product-integration-current-review.md',
      label: 'transport coordinate product integration current review',
    },
    {
      href: 'transport-coordinate-product-integration-evidence.json',
      label: 'transport coordinate product integration evidence',
    },
    {
      href: 'transport-coordinate-product-integration-progress.json',
      label: 'transport coordinate product integration progress',
    },
    {
      href: 'transport-coordinate-product-integration-review.md',
      label: 'transport coordinate product integration review',
    },
    {
      href: 'transport-coordinate-product-integration-test.json',
      label: 'transport coordinate product integration test',
    },
    {
      href: 'transport-coordinate-product-integration-verification.json',
      label: 'transport coordinate product integration verification',
    },
    {
      href: 'transport-coordinate-product-sdk-evidence.json',
      label: 'transport coordinate product sdk evidence',
    },
    {
      href: 'transport-dispense-bond-integration-audit.json',
      label: 'transport dispense bond integration audit',
    },
    {
      href: 'transport-dispense-bond-integration-current-progress.json',
      label: 'transport dispense bond integration current progress',
    },
    {
      href: 'transport-dispense-bond-integration-current-review.md',
      label: 'transport dispense bond integration current review',
    },
    {
      href: 'transport-dispense-bond-integration-evidence.json',
      label: 'transport dispense bond integration evidence',
    },
    {
      href: 'transport-dispense-bond-integration-review.md',
      label: 'transport dispense bond integration review',
    },
    {
      href: 'transport-dispense-bond-integration-test.json',
      label: 'transport dispense bond integration test',
    },
    {
      href: 'transport-dispense-bond-integration-verification.json',
      label: 'transport dispense bond integration verification',
    },
    {
      href: 'transport-dispense-bond-next-evidence.json',
      label: 'transport dispense bond next evidence',
    },
    {
      href: 'transport-dispense-relative-sdk-evidence.json',
      label: 'transport dispense relative sdk evidence',
    },
    {
      href: 'transport-dispense12-integration-audit.json',
      label: 'transport dispense12 integration audit',
    },
    {
      href: 'transport-dispense12-integration-current-progress.json',
      label: 'transport dispense12 integration current progress',
    },
    {
      href: 'transport-dispense12-integration-current-review.md',
      label: 'transport dispense12 integration current review',
    },
    {
      href: 'transport-dispense12-integration-evidence.json',
      label: 'transport dispense12 integration evidence',
    },
    {
      href: 'transport-dispense12-integration-review.md',
      label: 'transport dispense12 integration review',
    },
    {
      href: 'transport-dispense12-integration-test.json',
      label: 'transport dispense12 integration test',
    },
    {
      href: 'transport-dispense12-integration-verification.json',
      label: 'transport dispense12 integration verification',
    },
    {
      href: 'transport-dispense12-next-evidence.json',
      label: 'transport dispense12 next evidence',
    },
    {
      href: 'transport-full-framework-sdk-audit.json',
      label: 'transport full framework sdk audit',
    },
    {
      href: 'transport-full-framework-sdk-current-progress.json',
      label: 'transport full framework sdk current progress',
    },
    {
      href: 'transport-full-framework-sdk-current-review.md',
      label: 'transport full framework sdk current review',
    },
    {
      href: 'transport-full-framework-sdk-progress.json',
      label: 'transport full framework sdk progress',
    },
    {
      href: 'transport-full-framework-sdk-review.md',
      label: 'transport full framework sdk review',
    },
    {
      href: 'transport-full-framework-sdk-test.json',
      label: 'transport full framework sdk test',
    },
    {
      href: 'transport-inspection-current-chain-progress.json',
      label: 'transport inspection current chain progress',
    },
    {
      href: 'transport-inspection-current-chain-review.md',
      label: 'transport inspection current chain review',
    },
    {
      href: 'transport-inspection-readiness-integration-audit.json',
      label: 'transport inspection readiness integration audit',
    },
    {
      href: 'transport-inspection-readiness-integration-current-progress.json',
      label: 'transport inspection readiness integration current progress',
    },
    {
      href: 'transport-inspection-readiness-integration-current-review.md',
      label: 'transport inspection readiness integration current review',
    },
    {
      href: 'transport-inspection-readiness-integration-evidence.json',
      label: 'transport inspection readiness integration evidence',
    },
    {
      href: 'transport-inspection-readiness-integration-progress.json',
      label: 'transport inspection readiness integration progress',
    },
    {
      href: 'transport-inspection-readiness-integration-review.md',
      label: 'transport inspection readiness integration review',
    },
    {
      href: 'transport-inspection-readiness-integration-test.json',
      label: 'transport inspection readiness integration test',
    },
    {
      href: 'transport-inspection-readiness-integration-verification.json',
      label: 'transport inspection readiness integration verification',
    },
    {
      href: 'transport-inspection-readiness-next-evidence.json',
      label: 'transport inspection readiness next evidence',
    },
    {
      href: 'transport-inspection-readiness-startup-current-progress.json',
      label: 'transport inspection readiness startup current progress',
    },
    {
      href: 'transport-inspection-readiness-startup-current-review.md',
      label: 'transport inspection readiness startup current review',
    },
    {
      href: 'transport-inspection-readiness-startup-preparation-audit.json',
      label: 'transport inspection readiness startup preparation audit',
    },
    {
      href: 'transport-inspection-readiness-startup-preparation-test.json',
      label: 'transport inspection readiness startup preparation test',
    },
    {
      href: 'transport-inspection-repository-integration-audit.json',
      label: 'transport inspection repository integration audit',
    },
    {
      href: 'transport-inspection-repository-integration-checkpoint.json',
      label: 'transport inspection repository integration checkpoint',
    },
    {
      href: 'transport-inspection-repository-integration-current-progress.json',
      label: 'transport inspection repository integration current progress',
    },
    {
      href: 'transport-inspection-repository-integration-current-review.md',
      label: 'transport inspection repository integration current review',
    },
    {
      href: 'transport-inspection-repository-integration-evidence.json',
      label: 'transport inspection repository integration evidence',
    },
    {
      href: 'transport-inspection-repository-integration-progress.json',
      label: 'transport inspection repository integration progress',
    },
    {
      href: 'transport-inspection-repository-integration-review.md',
      label: 'transport inspection repository integration review',
    },
    {
      href: 'transport-inspection-repository-integration-test.json',
      label: 'transport inspection repository integration test',
    },
    {
      href: 'transport-inspection-repository-integration-verification.json',
      label: 'transport inspection repository integration verification',
    },
    {
      href: 'transport-inspection-repository-next-evidence.json',
      label: 'transport inspection repository next evidence',
    },
    {
      href: 'transport-inspection-repository-startup-preparation-audit.json',
      label: 'transport inspection repository startup preparation audit',
    },
    {
      href: 'transport-inspection-repository-startup-preparation-test.json',
      label: 'transport inspection repository startup preparation test',
    },
    {
      href: 'transport-inspection-startup-preparation-current-rebind-review.md',
      label: 'transport inspection startup preparation current rebind review',
    },
    {
      href: 'transport-inspection-startup-preparation-current-rebind.json',
      label: 'transport inspection startup preparation current rebind',
    },
    {
      href: 'transport-loader-bin-integration-audit.json',
      label: 'transport loader bin integration audit',
    },
    {
      href: 'transport-loader-bin-integration-current-progress.json',
      label: 'transport loader bin integration current progress',
    },
    {
      href: 'transport-loader-bin-integration-current-review.md',
      label: 'transport loader bin integration current review',
    },
    {
      href: 'transport-loader-bin-integration-evidence.json',
      label: 'transport loader bin integration evidence',
    },
    {
      href: 'transport-loader-bin-integration-review.md',
      label: 'transport loader bin integration review',
    },
    {
      href: 'transport-loader-bin-integration-test.json',
      label: 'transport loader bin integration test',
    },
    {
      href: 'transport-loader-bin-integration-verification.json',
      label: 'transport loader bin integration verification',
    },
    {
      href: 'transport-loader-bin-next-evidence.json',
      label: 'transport loader bin next evidence',
    },
    {
      href: 'transport-loader-bin-sdk-evidence.json',
      label: 'transport loader bin sdk evidence',
    },
    {
      href: 'transport-loading-belt-integration-audit.json',
      label: 'transport loading belt integration audit',
    },
    {
      href: 'transport-loading-belt-integration-current-progress.json',
      label: 'transport loading belt integration current progress',
    },
    {
      href: 'transport-loading-belt-integration-current-review.md',
      label: 'transport loading belt integration current review',
    },
    {
      href: 'transport-loading-belt-integration-evidence.json',
      label: 'transport loading belt integration evidence',
    },
    {
      href: 'transport-loading-belt-integration-review.md',
      label: 'transport loading belt integration review',
    },
    {
      href: 'transport-loading-belt-integration-test.json',
      label: 'transport loading belt integration test',
    },
    {
      href: 'transport-loading-belt-integration-verification.json',
      label: 'transport loading belt integration verification',
    },
    {
      href: 'transport-loading-belt-next-evidence.json',
      label: 'transport loading belt next evidence',
    },
    {
      href: 'transport-loading-output-sdk-evidence.json',
      label: 'transport loading output sdk evidence',
    },
    {
      href: 'transport-pause-audit.json',
      label: 'transport pause audit',
    },
    {
      href: 'transport-pause-current-progress.json',
      label: 'transport pause current progress',
    },
    {
      href: 'transport-pause-current-review.md',
      label: 'transport pause current review',
    },
    {
      href: 'transport-pause-integration-verification.json',
      label: 'transport pause integration verification',
    },
    {
      href: 'transport-pause-review.md',
      label: 'transport pause review',
    },
    {
      href: 'transport-pause-test.json',
      label: 'transport pause test',
    },
    {
      href: 'transport-producer-audit.json',
      label: 'transport producer audit',
    },
    {
      href: 'transport-producer-current-progress.json',
      label: 'transport producer current progress',
    },
    {
      href: 'transport-producer-current-review.md',
      label: 'transport producer current review',
    },
    {
      href: 'transport-producer-evidence.json',
      label: 'transport producer evidence',
    },
    {
      href: 'transport-producer-next-evidence.json',
      label: 'transport producer next evidence',
    },
    {
      href: 'transport-producer-review.md',
      label: 'transport producer review',
    },
    {
      href: 'transport-producer-test.json',
      label: 'transport producer test',
    },
    {
      href: 'transport-producer-verification.json',
      label: 'transport producer verification',
    },
    {
      href: 'transport-product-config-declarations-next-evidence.json',
      label: 'transport product config declarations next evidence',
    },
    {
      href: 'transport-product-declarations-focused-test.json',
      label: 'transport product declarations focused test',
    },
    {
      href: 'transport-product-declarations-integration-audit.json',
      label: 'transport product declarations integration audit',
    },
    {
      href: 'transport-product-declarations-integration-current-progress.json',
      label: 'transport product declarations integration current progress',
    },
    {
      href: 'transport-product-declarations-integration-current-review.md',
      label: 'transport product declarations integration current review',
    },
    {
      href: 'transport-product-declarations-integration-evidence.json',
      label: 'transport product declarations integration evidence',
    },
    {
      href: 'transport-product-declarations-integration-progress.json',
      label: 'transport product declarations integration progress',
    },
    {
      href: 'transport-product-declarations-integration-review.md',
      label: 'transport product declarations integration review',
    },
    {
      href: 'transport-product-declarations-integration-test.json',
      label: 'transport product declarations integration test',
    },
    {
      href: 'transport-product-declarations-integration-verification.json',
      label: 'transport product declarations integration verification',
    },
    {
      href: 'transport-production-call-review.md',
      label: 'transport production call review',
    },
    {
      href: 'transport-production-evidence.json',
      label: 'transport production evidence',
    },
    {
      href: 'transport-sdk-predicates-evidence.json',
      label: 'transport sdk predicates evidence',
    },
    {
      href: 'transport-sdk-preparations-current-rebind-review.md',
      label: 'transport sdk preparations current rebind review',
    },
    {
      href: 'transport-sdk-preparations-current-rebind.json',
      label: 'transport sdk preparations current rebind',
    },
    {
      href: 'transport-semantic-revalidation.md',
      label: 'transport semantic revalidation',
    },
    {
      href: 'transport-system-module-review.md',
      label: 'transport system module review',
    },
    {
      href: 'transport-teaching-aggregation-current.json',
      label: 'transport teaching aggregation current',
    },
    {
      href: 'transport-teaching-current-rebind.json',
      label: 'transport teaching current rebind',
    },
    {
      href: 'transport-teaching-integration-audit.json',
      label: 'transport teaching integration audit',
    },
    {
      href: 'transport-teaching-integration-current-progress.json',
      label: 'transport teaching integration current progress',
    },
    {
      href: 'transport-teaching-integration-current-review.md',
      label: 'transport teaching integration current review',
    },
    {
      href: 'transport-teaching-integration-evidence.json',
      label: 'transport teaching integration evidence',
    },
    {
      href: 'transport-teaching-integration-progress.json',
      label: 'transport teaching integration progress',
    },
    {
      href: 'transport-teaching-integration-review.md',
      label: 'transport teaching integration review',
    },
    {
      href: 'transport-teaching-integration-test.json',
      label: 'transport teaching integration test',
    },
    {
      href: 'transport-teaching-integration-verification.json',
      label: 'transport teaching integration verification',
    },
    {
      href: 'transport-teaching-lifecycle-audit.json',
      label: 'transport teaching lifecycle audit',
    },
    {
      href: 'transport-teaching-lifecycle-preparation-progress.json',
      label: 'transport teaching lifecycle preparation progress',
    },
    {
      href: 'transport-teaching-lifecycle-test.json',
      label: 'transport teaching lifecycle test',
    },
    {
      href: 'transport-teaching-next-evidence.json',
      label: 'transport teaching next evidence',
    },
    {
      href: 'transport-teaching-startup-preparation-audit.json',
      label: 'transport teaching startup preparation audit',
    },
    {
      href: 'transport-teaching-startup-preparation-test.json',
      label: 'transport teaching startup preparation test',
    },
    {
      href: 'transport-unclamp-stop-audit.json',
      label: 'transport unclamp stop audit',
    },
    {
      href: 'transport-unclamp-stop-current-progress.json',
      label: 'transport unclamp stop current progress',
    },
    {
      href: 'transport-unclamp-stop-current-review.md',
      label: 'transport unclamp stop current review',
    },
    {
      href: 'transport-unclamp-stop-integration-verification.json',
      label: 'transport unclamp stop integration verification',
    },
    {
      href: 'transport-unclamp-stop-review.md',
      label: 'transport unclamp stop review',
    },
    {
      href: 'transport-unclamp-stop-test.json',
      label: 'transport unclamp stop test',
    },
    {
      href: 'transport-unit-lifecycle-next-evidence.json',
      label: 'transport unit lifecycle next evidence',
    },
    {
      href: 'transport-unit-module-review.md',
      label: 'transport unit module review',
    },
    {
      href: 'transport-unit-services-integration-audit.json',
      label: 'transport unit services integration audit',
    },
    {
      href: 'transport-unit-services-integration-current-progress.json',
      label: 'transport unit services integration current progress',
    },
    {
      href: 'transport-unit-services-integration-current-review.md',
      label: 'transport unit services integration current review',
    },
    {
      href: 'transport-unit-services-integration-evidence.json',
      label: 'transport unit services integration evidence',
    },
    {
      href: 'transport-unit-services-integration-progress.json',
      label: 'transport unit services integration progress',
    },
    {
      href: 'transport-unit-services-integration-review.md',
      label: 'transport unit services integration review',
    },
    {
      href: 'transport-unit-services-integration-test.json',
      label: 'transport unit services integration test',
    },
    {
      href: 'transport-unit-services-integration-verification.json',
      label: 'transport unit services integration verification',
    },
    {
      href: 'transport-unit-services-next-evidence.json',
      label: 'transport unit services next evidence',
    },
    {
      href: 'transport-unit-services-sdk-evidence.json',
      label: 'transport unit services sdk evidence',
    },
    {
      href: 'transport-waiting-integration-audit.json',
      label: 'transport waiting integration audit',
    },
    {
      href: 'transport-waiting-integration-current-progress.json',
      label: 'transport waiting integration current progress',
    },
    {
      href: 'transport-waiting-integration-current-review.md',
      label: 'transport waiting integration current review',
    },
    {
      href: 'transport-waiting-integration-evidence.json',
      label: 'transport waiting integration evidence',
    },
    {
      href: 'transport-waiting-integration-review.md',
      label: 'transport waiting integration review',
    },
    {
      href: 'transport-waiting-integration-test.json',
      label: 'transport waiting integration test',
    },
    {
      href: 'transport-waiting-integration-verification.json',
      label: 'transport waiting integration verification',
    },
    {
      href: 'transport-waiting-next-evidence.json',
      label: 'transport waiting next evidence',
    },
    {
      href: 'transport-whole-action-sdk-audit.json',
      label: 'transport whole action sdk audit',
    },
    {
      href: 'transport-whole-action-sdk-current-progress.json',
      label: 'transport whole action sdk current progress',
    },
    {
      href: 'transport-whole-action-sdk-current-rebind-review.md',
      label: 'transport whole action sdk current rebind review',
    },
    {
      href: 'transport-whole-action-sdk-current-rebind.json',
      label: 'transport whole action sdk current rebind',
    },
    {
      href: 'transport-whole-action-sdk-current-review.md',
      label: 'transport whole action sdk current review',
    },
    {
      href: 'transport-whole-action-sdk-progress.json',
      label: 'transport whole action sdk progress',
    },
    {
      href: 'transport-whole-action-sdk-review.md',
      label: 'transport whole action sdk review',
    },
    {
      href: 'transport-whole-action-sdk-test.json',
      label: 'transport whole action sdk test',
    },
    {
      href: 'transport-whole-config-sdk-audit.json',
      label: 'transport whole config sdk audit',
    },
    {
      href: 'transport-whole-config-sdk-current-progress.json',
      label: 'transport whole config sdk current progress',
    },
    {
      href: 'transport-whole-config-sdk-current-review.md',
      label: 'transport whole config sdk current review',
    },
    {
      href: 'transport-whole-config-sdk-progress.json',
      label: 'transport whole config sdk progress',
    },
    {
      href: 'transport-whole-config-sdk-review.md',
      label: 'transport whole config sdk review',
    },
    {
      href: 'transport-whole-config-sdk-test.json',
      label: 'transport whole config sdk test',
    },
    {
      href: 'transport-whole-entity-sdk-audit.json',
      label: 'transport whole entity sdk audit',
    },
    {
      href: 'transport-whole-entity-sdk-current-progress.json',
      label: 'transport whole entity sdk current progress',
    },
    {
      href: 'transport-whole-entity-sdk-current-review.md',
      label: 'transport whole entity sdk current review',
    },
    {
      href: 'transport-whole-entity-sdk-progress.json',
      label: 'transport whole entity sdk progress',
    },
    {
      href: 'transport-whole-entity-sdk-review.md',
      label: 'transport whole entity sdk review',
    },
    {
      href: 'transport-whole-entity-sdk-test.json',
      label: 'transport whole entity sdk test',
    },
    {
      href: 'transport-workflow.archify.json',
      label: 'transport workflow.archify',
    },
    {
      href: 'transport-workflow.delivery.json',
      label: 'transport workflow.delivery',
    },
    {
      href: 'transport-workflow.html',
      label: 'transport workflow',
    },
    {
      href: 'transport-workflow.validation.json',
      label: 'transport workflow.validation',
    },
    {
      href: 'transport-workflow.visual-check.html',
      label: 'transport workflow.visual check',
    },
    {
      href: 'transport-workflow.visual-check.json',
      label: 'transport workflow.visual check',
    },
    {
      href: 'ui-start-mode-audit.json',
      label: 'ui start mode audit',
    },
    {
      href: 'ui-start-mode-current-progress.json',
      label: 'ui start mode current progress',
    },
    {
      href: 'ui-start-mode-current-review.md',
      label: 'ui start mode current review',
    },
    {
      href: 'ui-start-mode-evidence.json',
      label: 'ui start mode evidence',
    },
    {
      href: 'ui-start-mode-next-evidence.json',
      label: 'ui start mode next evidence',
    },
    {
      href: 'ui-start-mode-review.md',
      label: 'ui start mode review',
    },
    {
      href: 'ui-start-mode-test.json',
      label: 'ui start mode test',
    },
    {
      href: 'ui-start-mode-verification.json',
      label: 'ui start mode verification',
    },
    {
      href: 'uplook-code-two-point-review.md',
      label: 'uplook code two point review',
    },
    {
      href: 'uplook-wafer-calibration-source-review.md',
      label: 'uplook wafer calibration source review',
    },
    {
      href: 'verification-runbook.md',
      label: 'verification runbook',
    },
    {
      href: 'verification.md',
      label: 'verification',
    },
    {
      href: 'virtual-dispatch-provenance-audit.json',
      label: 'virtual dispatch provenance audit',
    },
    {
      href: 'virtual-dispatch-provenance-progress.json',
      label: 'virtual dispatch provenance progress',
    },
    {
      href: 'virtual-dispatch-provenance-review.md',
      label: 'virtual dispatch provenance review',
    },
    {
      href: 'virtual-dispatch-provenance-test.json',
      label: 'virtual dispatch provenance test',
    },
    {
      href: 'vision-alarm-hardware-review.md',
      label: 'vision alarm hardware review',
    },
    {
      href: 'vision-defect-retry-current-progress.json',
      label: 'vision defect retry current progress',
    },
    {
      href: 'vision-defect-retry-current-review.md',
      label: 'vision defect retry current review',
    },
    {
      href: 'vision-defect-retry-test.json',
      label: 'vision defect retry test',
    },
    {
      href: 'vision-motion-analysis.md',
      label: 'vision motion analysis',
    },
    {
      href: 'vision-motion-workflow.archify.json',
      label: 'vision motion workflow.archify',
    },
    {
      href: 'vision-motion-workflow.html',
      label: 'vision motion workflow',
    },
    {
      href: 'vision-recipe-module-review.md',
      label: 'vision recipe module review',
    },
    {
      href: 'vision-request-routing-review.md',
      label: 'vision request routing review',
    },
    {
      href: 'vision-runtime-module-review.md',
      label: 'vision runtime module review',
    },
    {
      href: 'vision-teaching-browser-check.json',
      label: 'vision teaching browser check',
    },
    {
      href: 'vision-teaching-evidence.json',
      label: 'vision teaching evidence',
    },
    {
      href: 'vision-teaching-source.html',
      label: 'vision teaching source',
    },
    {
      href: 'vision-teaching-test.json',
      label: 'vision teaching test',
    },
    {
      href: 'vision-teaching-workflow-review.md',
      label: 'vision teaching workflow review',
    },
    {
      href: 'wafer-action-gates-audit.json',
      label: 'wafer action gates audit',
    },
    {
      href: 'wafer-action-gates-current-progress.json',
      label: 'wafer action gates current progress',
    },
    {
      href: 'wafer-action-gates-current-review.md',
      label: 'wafer action gates current review',
    },
    {
      href: 'wafer-action-gates-integration-verification.json',
      label: 'wafer action gates integration verification',
    },
    {
      href: 'wafer-action-gates-next-evidence.json',
      label: 'wafer action gates next evidence',
    },
    {
      href: 'wafer-action-gates-review.md',
      label: 'wafer action gates review',
    },
    {
      href: 'wafer-action-gates-test.json',
      label: 'wafer action gates test',
    },
    {
      href: 'wafer-blob-position-audit.json',
      label: 'wafer blob position audit',
    },
    {
      href: 'wafer-blob-position-current-progress.json',
      label: 'wafer blob position current progress',
    },
    {
      href: 'wafer-blob-position-current-review.md',
      label: 'wafer blob position current review',
    },
    {
      href: 'wafer-blob-position-integration-verification.json',
      label: 'wafer blob position integration verification',
    },
    {
      href: 'wafer-blob-position-next-evidence.json',
      label: 'wafer blob position next evidence',
    },
    {
      href: 'wafer-blob-position-review.md',
      label: 'wafer blob position review',
    },
    {
      href: 'wafer-blob-position-test.json',
      label: 'wafer blob position test',
    },
    {
      href: 'wafer-bond-handshake-review.md',
      label: 'wafer bond handshake review',
    },
    {
      href: 'wafer-camera-clearance-audit.json',
      label: 'wafer camera clearance audit',
    },
    {
      href: 'wafer-camera-clearance-current-progress.json',
      label: 'wafer camera clearance current progress',
    },
    {
      href: 'wafer-camera-clearance-current-review.md',
      label: 'wafer camera clearance current review',
    },
    {
      href: 'wafer-camera-clearance-integration-verification.json',
      label: 'wafer camera clearance integration verification',
    },
    {
      href: 'wafer-camera-clearance-next-evidence.json',
      label: 'wafer camera clearance next evidence',
    },
    {
      href: 'wafer-camera-clearance-review.md',
      label: 'wafer camera clearance review',
    },
    {
      href: 'wafer-camera-clearance-test.json',
      label: 'wafer camera clearance test',
    },
    {
      href: 'wafer-change-retry-current-progress.json',
      label: 'wafer change retry current progress',
    },
    {
      href: 'wafer-change-retry-current-review.md',
      label: 'wafer change retry current review',
    },
    {
      href: 'wafer-change-retry-evidence.json',
      label: 'wafer change retry evidence',
    },
    {
      href: 'wafer-change-retry-review.md',
      label: 'wafer change retry review',
    },
    {
      href: 'wafer-consumer-next-evidence.json',
      label: 'wafer consumer next evidence',
    },
    {
      href: 'wafer-consumer-pause-audit.json',
      label: 'wafer consumer pause audit',
    },
    {
      href: 'wafer-consumer-pause-current-progress.json',
      label: 'wafer consumer pause current progress',
    },
    {
      href: 'wafer-consumer-pause-current-review.md',
      label: 'wafer consumer pause current review',
    },
    {
      href: 'wafer-consumer-pause-integration-verification.json',
      label: 'wafer consumer pause integration verification',
    },
    {
      href: 'wafer-consumer-pause-review.md',
      label: 'wafer consumer pause review',
    },
    {
      href: 'wafer-consumer-pause-test.json',
      label: 'wafer consumer pause test',
    },
    {
      href: 'wafer-eject-ready-audit.json',
      label: 'wafer eject ready audit',
    },
    {
      href: 'wafer-eject-ready-current-progress.json',
      label: 'wafer eject ready current progress',
    },
    {
      href: 'wafer-eject-ready-current-review.md',
      label: 'wafer eject ready current review',
    },
    {
      href: 'wafer-eject-ready-integration-verification.json',
      label: 'wafer eject ready integration verification',
    },
    {
      href: 'wafer-eject-ready-next-evidence.json',
      label: 'wafer eject ready next evidence',
    },
    {
      href: 'wafer-eject-ready-review.md',
      label: 'wafer eject ready review',
    },
    {
      href: 'wafer-eject-ready-test.json',
      label: 'wafer eject ready test',
    },
    {
      href: 'wafer-geometry-audit.json',
      label: 'wafer geometry audit',
    },
    {
      href: 'wafer-geometry-current-progress.json',
      label: 'wafer geometry current progress',
    },
    {
      href: 'wafer-geometry-current-review.md',
      label: 'wafer geometry current review',
    },
    {
      href: 'wafer-geometry-integration-verification.json',
      label: 'wafer geometry integration verification',
    },
    {
      href: 'wafer-geometry-review.md',
      label: 'wafer geometry review',
    },
    {
      href: 'wafer-geometry-test.json',
      label: 'wafer geometry test',
    },
    {
      href: 'wafer-lower-search-pending-evidence.json',
      label: 'wafer lower search pending evidence',
    },
    {
      href: 'wafer-map-runtime-review.md',
      label: 'wafer map runtime review',
    },
    {
      href: 'wafer-mark-center-audit.json',
      label: 'wafer mark center audit',
    },
    {
      href: 'wafer-mark-center-current-progress.json',
      label: 'wafer mark center current progress',
    },
    {
      href: 'wafer-mark-center-current-review.md',
      label: 'wafer mark center current review',
    },
    {
      href: 'wafer-mark-center-evidence.json',
      label: 'wafer mark center evidence',
    },
    {
      href: 'wafer-mark-center-integration-verification.json',
      label: 'wafer mark center integration verification',
    },
    {
      href: 'wafer-mark-center-next-evidence.json',
      label: 'wafer mark center next evidence',
    },
    {
      href: 'wafer-mark-center-review.md',
      label: 'wafer mark center review',
    },
    {
      href: 'wafer-mark-center-test.json',
      label: 'wafer mark center test',
    },
    {
      href: 'wafer-next-position-audit.json',
      label: 'wafer next position audit',
    },
    {
      href: 'wafer-next-position-current-progress.json',
      label: 'wafer next position current progress',
    },
    {
      href: 'wafer-next-position-current-review.md',
      label: 'wafer next position current review',
    },
    {
      href: 'wafer-next-position-evidence.json',
      label: 'wafer next position evidence',
    },
    {
      href: 'wafer-next-position-integration-verification.json',
      label: 'wafer next position integration verification',
    },
    {
      href: 'wafer-next-position-next-evidence.json',
      label: 'wafer next position next evidence',
    },
    {
      href: 'wafer-next-position-review.md',
      label: 'wafer next position review',
    },
    {
      href: 'wafer-next-position-test.json',
      label: 'wafer next position test',
    },
    {
      href: 'wafer-pick-ejection-handshake-review.md',
      label: 'wafer pick ejection handshake review',
    },
    {
      href: 'wafer-pick-handshake-sequence.archify.json',
      label: 'wafer pick handshake sequence.archify',
    },
    {
      href: 'wafer-pick-handshake-sequence.html',
      label: 'wafer pick handshake sequence',
    },
    {
      href: 'wafer-pick-handshake-sequence.review.json',
      label: 'wafer pick handshake sequence.review',
    },
    {
      href: 'wafer-pick-handshake-sequence.visual-check.html',
      label: 'wafer pick handshake sequence.visual check',
    },
    {
      href: 'wafer-pick-handshake-sequence.visual-check.json',
      label: 'wafer pick handshake sequence.visual check',
    },
    {
      href: 'wafer-pick-handshake-sequence.visual-review.json',
      label: 'wafer pick handshake sequence.visual review',
    },
    {
      href: 'wafer-position-accuracy-audit.json',
      label: 'wafer position accuracy audit',
    },
    {
      href: 'wafer-position-accuracy-current-progress.json',
      label: 'wafer position accuracy current progress',
    },
    {
      href: 'wafer-position-accuracy-current-review.md',
      label: 'wafer position accuracy current review',
    },
    {
      href: 'wafer-position-accuracy-integration-verification.json',
      label: 'wafer position accuracy integration verification',
    },
    {
      href: 'wafer-position-accuracy-next-evidence.json',
      label: 'wafer position accuracy next evidence',
    },
    {
      href: 'wafer-position-accuracy-review.md',
      label: 'wafer position accuracy review',
    },
    {
      href: 'wafer-position-accuracy-test.json',
      label: 'wafer position accuracy test',
    },
    {
      href: 'wafer-range-init-audit.json',
      label: 'wafer range init audit',
    },
    {
      href: 'wafer-range-init-current-progress.json',
      label: 'wafer range init current progress',
    },
    {
      href: 'wafer-range-init-current-review.md',
      label: 'wafer range init current review',
    },
    {
      href: 'wafer-range-init-evidence.json',
      label: 'wafer range init evidence',
    },
    {
      href: 'wafer-range-init-integration-verification.json',
      label: 'wafer range init integration verification',
    },
    {
      href: 'wafer-range-init-next-evidence.json',
      label: 'wafer range init next evidence',
    },
    {
      href: 'wafer-range-init-review.md',
      label: 'wafer range init review',
    },
    {
      href: 'wafer-range-init-test.json',
      label: 'wafer range init test',
    },
    {
      href: 'wafer-rebuild-module-review.md',
      label: 'wafer rebuild module review',
    },
    {
      href: 'wafer-safety-guards-audit.json',
      label: 'wafer safety guards audit',
    },
    {
      href: 'wafer-safety-guards-current-progress.json',
      label: 'wafer safety guards current progress',
    },
    {
      href: 'wafer-safety-guards-current-review.md',
      label: 'wafer safety guards current review',
    },
    {
      href: 'wafer-safety-guards-integration-verification.json',
      label: 'wafer safety guards integration verification',
    },
    {
      href: 'wafer-safety-guards-next-evidence.json',
      label: 'wafer safety guards next evidence',
    },
    {
      href: 'wafer-safety-guards-review.md',
      label: 'wafer safety guards review',
    },
    {
      href: 'wafer-safety-guards-test.json',
      label: 'wafer safety guards test',
    },
    {
      href: 'wafer-search-gates-audit.json',
      label: 'wafer search gates audit',
    },
    {
      href: 'wafer-search-gates-current-progress.json',
      label: 'wafer search gates current progress',
    },
    {
      href: 'wafer-search-gates-current-review.md',
      label: 'wafer search gates current review',
    },
    {
      href: 'wafer-search-gates-integration-verification.json',
      label: 'wafer search gates integration verification',
    },
    {
      href: 'wafer-search-gates-review.md',
      label: 'wafer search gates review',
    },
    {
      href: 'wafer-search-gates-test.json',
      label: 'wafer search gates test',
    },
    {
      href: 'wafer-selection-current-progress.json',
      label: 'wafer selection current progress',
    },
    {
      href: 'wafer-selection-current-review.md',
      label: 'wafer selection current review',
    },
    {
      href: 'wafer-selection-evidence.json',
      label: 'wafer selection evidence',
    },
    {
      href: 'wafer-selection-review.md',
      label: 'wafer selection review',
    },
    {
      href: 'wafer-start-init-current-progress.json',
      label: 'wafer start init current progress',
    },
    {
      href: 'wafer-start-init-current-review.md',
      label: 'wafer start init current review',
    },
    {
      href: 'wafer-start-init-evidence.json',
      label: 'wafer start init evidence',
    },
    {
      href: 'wafer-start-init-review.md',
      label: 'wafer start init review',
    },
    {
      href: 'wafer-stop-chain-audit.json',
      label: 'wafer stop chain audit',
    },
    {
      href: 'wafer-stop-chain-current-progress.json',
      label: 'wafer stop chain current progress',
    },
    {
      href: 'wafer-stop-chain-current-review.md',
      label: 'wafer stop chain current review',
    },
    {
      href: 'wafer-stop-chain-integration-verification.json',
      label: 'wafer stop chain integration verification',
    },
    {
      href: 'wafer-stop-chain-review.md',
      label: 'wafer stop chain review',
    },
    {
      href: 'wafer-stop-chain-test.json',
      label: 'wafer stop chain test',
    },
    {
      href: 'wafer-supply-portal-check.json',
      label: 'wafer supply portal check',
    },
    {
      href: 'wafer-supply-review-evidence.json',
      label: 'wafer supply review evidence',
    },
    {
      href: 'wafer-supply-semantic-revalidation.md',
      label: 'wafer supply semantic revalidation',
    },
    {
      href: 'wafer-supply-workflow.archify.json',
      label: 'wafer supply workflow.archify',
    },
    {
      href: 'wafer-supply-workflow.browser-check.json',
      label: 'wafer supply workflow.browser check',
    },
    {
      href: 'wafer-supply-workflow.delivery.json',
      label: 'wafer supply workflow.delivery',
    },
    {
      href: 'wafer-supply-workflow.html',
      label: 'wafer supply workflow',
    },
    {
      href: 'wafer-supply-workflow.visual-check.html',
      label: 'wafer supply workflow.visual check',
    },
    {
      href: 'wafer-supply-workflow.visual-check.json',
      label: 'wafer supply workflow.visual check',
    },
    {
      href: 'wafer-supply-workflow.visual-review.json',
      label: 'wafer supply workflow.visual review',
    },
    {
      href: 'wafer-vision-acquisition-audit.json',
      label: 'wafer vision acquisition audit',
    },
    {
      href: 'wafer-vision-acquisition-current-progress.json',
      label: 'wafer vision acquisition current progress',
    },
    {
      href: 'wafer-vision-acquisition-current-review.md',
      label: 'wafer vision acquisition current review',
    },
    {
      href: 'wafer-vision-acquisition-integration-verification.json',
      label: 'wafer vision acquisition integration verification',
    },
    {
      href: 'wafer-vision-acquisition-review.md',
      label: 'wafer vision acquisition review',
    },
    {
      href: 'wafer-vision-acquisition-test.json',
      label: 'wafer vision acquisition test',
    },
    {
      href: 'wafer-vision-control-audit.json',
      label: 'wafer vision control audit',
    },
    {
      href: 'wafer-vision-control-current-progress.json',
      label: 'wafer vision control current progress',
    },
    {
      href: 'wafer-vision-control-current-review.md',
      label: 'wafer vision control current review',
    },
    {
      href: 'wafer-vision-control-integration-verification.json',
      label: 'wafer vision control integration verification',
    },
    {
      href: 'wafer-vision-control-next-evidence.json',
      label: 'wafer vision control next evidence',
    },
    {
      href: 'wafer-vision-control-review.md',
      label: 'wafer vision control review',
    },
    {
      href: 'wafer-vision-control-test.json',
      label: 'wafer vision control test',
    },
    {
      href: 'wafer-vision-geometry-next-evidence.json',
      label: 'wafer vision geometry next evidence',
    },
    {
      href: 'whole-node-source-closure-366-candidate-progress.json',
      label: 'whole node source closure 366 candidate progress',
    },
    {
      href: 'whole-node-source-closure-366-candidate-review.md',
      label: 'whole node source closure 366 candidate review',
    },
    {
      href: 'whole-node-source-closure-366-epoxy-repo-combo-progress.json',
      label: 'whole node source closure 366 epoxy repo combo progress',
    },
    {
      href: 'whole-node-source-closure-366-epoxy-repo-combo-review.md',
      label: 'whole node source closure 366 epoxy repo combo review',
    },
    {
      href: 'whole-node-source-closure-366-program-probes-progress.json',
      label: 'whole node source closure 366 program probes progress',
    },
    {
      href: 'whole-node-source-closure-366-program-probes-review.md',
      label: 'whole node source closure 366 program probes review',
    },
    {
      href: 'whole-node-source-closure-367-combo-progress.json',
      label: 'whole node source closure 367 combo progress',
    },
    {
      href: 'whole-node-source-closure-367-combo-review.md',
      label: 'whole node source closure 367 combo review',
    },
    {
      href: 'whole-node-source-closure-367-domain-groups-progress.json',
      label: 'whole node source closure 367 domain groups progress',
    },
    {
      href: 'whole-node-source-closure-367-domain-groups-review.md',
      label: 'whole node source closure 367 domain groups review',
    },
    {
      href: 'whole-node-source-closure-367-frontier-probes-progress.json',
      label: 'whole node source closure 367 frontier probes progress',
    },
    {
      href: 'whole-node-source-closure-367-frontier-probes-review.md',
      label: 'whole node source closure 367 frontier probes review',
    },
    {
      href: 'whole-node-source-closure-367-frontier-singles-progress.json',
      label: 'whole node source closure 367 frontier singles progress',
    },
    {
      href: 'whole-node-source-closure-367-frontier-singles-review.md',
      label: 'whole node source closure 367 frontier singles review',
    },
    {
      href: 'whole-node-source-closure-367-product-singles-progress.json',
      label: 'whole node source closure 367 product singles progress',
    },
    {
      href: 'whole-node-source-closure-367-product-singles-review.md',
      label: 'whole node source closure 367 product singles review',
    },
    {
      href: 'whole-node-source-closure-368-combo-progress.json',
      label: 'whole node source closure 368 combo progress',
    },
    {
      href: 'whole-node-source-closure-368-combo-review.md',
      label: 'whole node source closure 368 combo review',
    },
    {
      href: 'whole-node-source-closure-368-low-coupling-singles-progress.json',
      label: 'whole node source closure 368 low coupling singles progress',
    },
    {
      href: 'whole-node-source-closure-368-low-coupling-singles-review.md',
      label: 'whole node source closure 368 low coupling singles review',
    },
    {
      href: 'whole-node-source-closure-370-controller-singles-progress.json',
      label: 'whole node source closure 370 controller singles progress',
    },
    {
      href: 'whole-node-source-closure-370-controller-singles-review.md',
      label: 'whole node source closure 370 controller singles review',
    },
    {
      href: 'whole-node-source-closure-370-module-task-singles-progress.json',
      label: 'whole node source closure 370 module task singles progress',
    },
    {
      href: 'whole-node-source-closure-370-module-task-singles-review.md',
      label: 'whole node source closure 370 module task singles review',
    },
    {
      href: 'whole-node-source-closure-370-source-singles-progress.json',
      label: 'whole node source closure 370 source singles progress',
    },
    {
      href: 'whole-node-source-closure-370-source-singles-review.md',
      label: 'whole node source closure 370 source singles review',
    },
    {
      href: 'whole-node-source-closure-387-bond-partial-combos-progress.json',
      label: 'whole node source closure 387 bond partial combos progress',
    },
    {
      href: 'whole-node-source-closure-387-bond-partial-combos-review.md',
      label: 'whole node source closure 387 bond partial combos review',
    },
    {
      href: 'whole-node-source-closure-387-bond-symbol-probes-progress.json',
      label: 'whole node source closure 387 bond symbol probes progress',
    },
    {
      href: 'whole-node-source-closure-387-bond-symbol-probes-review.md',
      label: 'whole node source closure 387 bond symbol probes review',
    },
    {
      href: 'whole-node-source-closure-387-flip-program-dependency-probes-progress.json',
      label: 'whole node source closure 387 flip program dependency probes progress',
    },
    {
      href: 'whole-node-source-closure-387-flip-program-dependency-probes-review.md',
      label: 'whole node source closure 387 flip program dependency probes review',
    },
    {
      href: 'whole-node-source-closure-387-missing-model-probes-progress.json',
      label: 'whole node source closure 387 missing model probes progress',
    },
    {
      href: 'whole-node-source-closure-387-missing-model-probes-review.md',
      label: 'whole node source closure 387 missing model probes review',
    },
    {
      href: 'whole-node-source-closure-387-module-enum-probes-progress.json',
      label: 'whole node source closure 387 module enum probes progress',
    },
    {
      href: 'whole-node-source-closure-387-module-enum-probes-review.md',
      label: 'whole node source closure 387 module enum probes review',
    },
    {
      href: 'whole-node-source-closure-387-next-missing-progress.json',
      label: 'whole node source closure 387 next missing progress',
    },
    {
      href: 'whole-node-source-closure-387-next-missing-review.md',
      label: 'whole node source closure 387 next missing review',
    },
    {
      href: 'whole-node-source-closure-387-reference-probe-progress.json',
      label: 'whole node source closure 387 reference probe progress',
    },
    {
      href: 'whole-node-source-closure-387-reference-probe-review.md',
      label: 'whole node source closure 387 reference probe review',
    },
    {
      href: 'whole-node-source-closure-387-single-files-progress.json',
      label: 'whole node source closure 387 single files progress',
    },
    {
      href: 'whole-node-source-closure-387-single-files-review.md',
      label: 'whole node source closure 387 single files review',
    },
    {
      href: 'whole-node-source-closure-387-source-group-probe-progress.json',
      label: 'whole node source closure 387 source group probe progress',
    },
    {
      href: 'whole-node-source-closure-387-source-group-probe-review.md',
      label: 'whole node source closure 387 source group probe review',
    },
    {
      href: 'whole-node-source-closure-387-wafer-combo-probes-progress.json',
      label: 'whole node source closure 387 wafer combo probes progress',
    },
    {
      href: 'whole-node-source-closure-387-wafer-combo-probes-review.md',
      label: 'whole node source closure 387 wafer combo probes review',
    },
    {
      href: 'whole-node-source-closure-389-wafer-module-probes-progress.json',
      label: 'whole node source closure 389 wafer module probes progress',
    },
    {
      href: 'whole-node-source-closure-389-wafer-module-probes-review.md',
      label: 'whole node source closure 389 wafer module probes review',
    },
    {
      href: 'whole-node-source-closure-392-flip-dependency-probes-progress.json',
      label: 'whole node source closure 392 flip dependency probes progress',
    },
    {
      href: 'whole-node-source-closure-392-flip-dependency-probes-review.md',
      label: 'whole node source closure 392 flip dependency probes review',
    },
    {
      href: 'whole-node-source-closure-393-wafer-controller-probes-progress.json',
      label: 'whole node source closure 393 wafer controller probes progress',
    },
    {
      href: 'whole-node-source-closure-393-wafer-controller-probes-review.md',
      label: 'whole node source closure 393 wafer controller probes review',
    },
    {
      href: 'whole-node-source-closure-398-config-probes-progress.json',
      label: 'whole node source closure 398 config probes progress',
    },
    {
      href: 'whole-node-source-closure-398-config-probes-review.md',
      label: 'whole node source closure 398 config probes review',
    },
    {
      href: 'whole-node-source-closure-398-missing-task-probes-progress.json',
      label: 'whole node source closure 398 missing task probes progress',
    },
    {
      href: 'whole-node-source-closure-398-missing-task-probes-review.md',
      label: 'whole node source closure 398 missing task probes review',
    },
    {
      href: 'whole-node-source-closure-398-symbol-source-probes-progress.json',
      label: 'whole node source closure 398 symbol source probes progress',
    },
    {
      href: 'whole-node-source-closure-398-symbol-source-probes-review.md',
      label: 'whole node source closure 398 symbol source probes review',
    },
    {
      href: 'whole-node-source-closure-402-dispense-support-probes-progress.json',
      label: 'whole node source closure 402 dispense support probes progress',
    },
    {
      href: 'whole-node-source-closure-402-dispense-support-probes-review.md',
      label: 'whole node source closure 402 dispense support probes review',
    },
    {
      href: 'whole-node-source-closure-402-support-near-combos-progress.json',
      label: 'whole node source closure 402 support near combos progress',
    },
    {
      href: 'whole-node-source-closure-402-support-near-combos-review.md',
      label: 'whole node source closure 402 support near combos review',
    },
    {
      href: 'whole-node-source-closure-404-clean-nozzle-combos-progress.json',
      label: 'whole node source closure 404 clean nozzle combos progress',
    },
    {
      href: 'whole-node-source-closure-404-clean-nozzle-combos-review.md',
      label: 'whole node source closure 404 clean nozzle combos review',
    },
    {
      href: 'whole-node-source-closure-404-program-missing-probes-progress.json',
      label: 'whole node source closure 404 program missing probes progress',
    },
    {
      href: 'whole-node-source-closure-404-program-missing-probes-review.md',
      label: 'whole node source closure 404 program missing probes review',
    },
    {
      href: 'whole-node-source-closure-405-program-followup-progress.json',
      label: 'whole node source closure 405 program followup progress',
    },
    {
      href: 'whole-node-source-closure-405-program-followup-review.md',
      label: 'whole node source closure 405 program followup review',
    },
    {
      href: 'whole-node-source-closure-408-program-tail-combos-progress.json',
      label: 'whole node source closure 408 program tail combos progress',
    },
    {
      href: 'whole-node-source-closure-408-program-tail-combos-review.md',
      label: 'whole node source closure 408 program tail combos review',
    },
    {
      href: 'whole-node-source-closure-408-program-tail-probes-progress.json',
      label: 'whole node source closure 408 program tail probes progress',
    },
    {
      href: 'whole-node-source-closure-408-program-tail-probes-review.md',
      label: 'whole node source closure 408 program tail probes review',
    },
    {
      href: 'whole-node-source-closure-408-support-probes-progress.json',
      label: 'whole node source closure 408 support probes progress',
    },
    {
      href: 'whole-node-source-closure-408-support-probes-review.md',
      label: 'whole node source closure 408 support probes review',
    },
    {
      href: 'whole-node-source-closure-410-s2-program-combos-progress.json',
      label: 'whole node source closure 410 s2 program combos progress',
    },
    {
      href: 'whole-node-source-closure-410-s2-program-combos-review.md',
      label: 'whole node source closure 410 s2 program combos review',
    },
    {
      href: 'whole-node-source-closure-410-searchchip-near-combos-progress.json',
      label: 'whole node source closure 410 searchchip near combos progress',
    },
    {
      href: 'whole-node-source-closure-410-searchchip-near-combos-review.md',
      label: 'whole node source closure 410 searchchip near combos review',
    },
    {
      href: 'whole-node-source-closure-410-searchchip-probes-progress.json',
      label: 'whole node source closure 410 searchchip probes progress',
    },
    {
      href: 'whole-node-source-closure-410-searchchip-probes-review.md',
      label: 'whole node source closure 410 searchchip probes review',
    },
    {
      href: 'whole-node-source-closure-413-cross-controller-probes-progress.json',
      label: 'whole node source closure 413 cross controller probes progress',
    },
    {
      href: 'whole-node-source-closure-413-cross-controller-probes-review.md',
      label: 'whole node source closure 413 cross controller probes review',
    },
    {
      href: 'whole-node-source-closure-413-next-probes-progress.json',
      label: 'whole node source closure 413 next probes progress',
    },
    {
      href: 'whole-node-source-closure-413-next-probes-review.md',
      label: 'whole node source closure 413 next probes review',
    },
    {
      href: 'whole-node-source-closure-413-next-single-probes-progress.json',
      label: 'whole node source closure 413 next single probes progress',
    },
    {
      href: 'whole-node-source-closure-413-next-single-probes-review.md',
      label: 'whole node source closure 413 next single probes review',
    },
    {
      href: 'whole-node-source-closure-413-single-symbol-probes-progress.json',
      label: 'whole node source closure 413 single symbol probes progress',
    },
    {
      href: 'whole-node-source-closure-413-single-symbol-probes-review.md',
      label: 'whole node source closure 413 single symbol probes review',
    },
    {
      href: 'whole-node-source-closure-422-consumable-probes-progress.json',
      label: 'whole node source closure 422 consumable probes progress',
    },
    {
      href: 'whole-node-source-closure-422-consumable-probes-review.md',
      label: 'whole node source closure 422 consumable probes review',
    },
    {
      href: 'whole-node-source-closure-423-module-probes-progress.json',
      label: 'whole node source closure 423 module probes progress',
    },
    {
      href: 'whole-node-source-closure-423-module-probes-review.md',
      label: 'whole node source closure 423 module probes review',
    },
    {
      href: 'whole-node-source-closure-427-misc-probes-progress.json',
      label: 'whole node source closure 427 misc probes progress',
    },
    {
      href: 'whole-node-source-closure-427-misc-probes-review.md',
      label: 'whole node source closure 427 misc probes review',
    },
    {
      href: 'whole-node-source-closure-444-bond-program-probes-progress.json',
      label: 'whole node source closure 444 bond program probes progress',
    },
    {
      href: 'whole-node-source-closure-444-bond-program-probes-review.md',
      label: 'whole node source closure 444 bond program probes review',
    },
    {
      href: 'whole-node-source-closure-444-force-probes-progress.json',
      label: 'whole node source closure 444 force probes progress',
    },
    {
      href: 'whole-node-source-closure-444-force-probes-review.md',
      label: 'whole node source closure 444 force probes review',
    },
    {
      href: 'whole-node-source-closure-456-statistics-probes-progress.json',
      label: 'whole node source closure 456 statistics probes progress',
    },
    {
      href: 'whole-node-source-closure-456-statistics-probes-review.md',
      label: 'whole node source closure 456 statistics probes review',
    },
    {
      href: 'whole-node-source-closure-458-followup-probes-progress.json',
      label: 'whole node source closure 458 followup probes progress',
    },
    {
      href: 'whole-node-source-closure-458-followup-probes-review.md',
      label: 'whole node source closure 458 followup probes review',
    },
    {
      href: 'whole-node-source-closure-460-domain-probes-progress.json',
      label: 'whole node source closure 460 domain probes progress',
    },
    {
      href: 'whole-node-source-closure-460-domain-probes-review.md',
      label: 'whole node source closure 460 domain probes review',
    },
    {
      href: 'whole-node-source-closure-465-leaf-probes-progress.json',
      label: 'whole node source closure 465 leaf probes progress',
    },
    {
      href: 'whole-node-source-closure-465-leaf-probes-review.md',
      label: 'whole node source closure 465 leaf probes review',
    },
    {
      href: 'whole-node-source-closure-465-program-probes-progress.json',
      label: 'whole node source closure 465 program probes progress',
    },
    {
      href: 'whole-node-source-closure-465-program-probes-review.md',
      label: 'whole node source closure 465 program probes review',
    },
    {
      href: 'whole-node-source-closure-469-combo-probes-progress.json',
      label: 'whole node source closure 469 combo probes progress',
    },
    {
      href: 'whole-node-source-closure-469-combo-probes-review.md',
      label: 'whole node source closure 469 combo probes review',
    },
    {
      href: 'whole-node-source-closure-473-root-probes-progress.json',
      label: 'whole node source closure 473 root probes progress',
    },
    {
      href: 'whole-node-source-closure-473-root-probes-review.md',
      label: 'whole node source closure 473 root probes review',
    },
    {
      href: 'whole-node-source-closure-496-service-probes-progress.json',
      label: 'whole node source closure 496 service probes progress',
    },
    {
      href: 'whole-node-source-closure-496-service-probes-review.md',
      label: 'whole node source closure 496 service probes review',
    },
    {
      href: 'whole-node-source-closure-502-focused-progress.json',
      label: 'whole node source closure 502 focused progress',
    },
    {
      href: 'whole-node-source-closure-502-focused-review.md',
      label: 'whole node source closure 502 focused review',
    },
    {
      href: 'whole-node-source-closure-502-namespace-probes-progress.json',
      label: 'whole node source closure 502 namespace probes progress',
    },
    {
      href: 'whole-node-source-closure-502-namespace-probes-review.md',
      label: 'whole node source closure 502 namespace probes review',
    },
    {
      href: 'whole-node-source-closure-502-probes-progress.json',
      label: 'whole node source closure 502 probes progress',
    },
    {
      href: 'whole-node-source-closure-502-probes-review.md',
      label: 'whole node source closure 502 probes review',
    },
    {
      href: 'whole-node-source-closure-bond-seed-candidate-progress.json',
      label: 'whole node source closure bond seed candidate progress',
    },
    {
      href: 'whole-node-source-closure-bond-seed-candidate-review.md',
      label: 'whole node source closure bond seed candidate review',
    },
    {
      href: 'whole-node-source-closure-bond-seed-probes-progress.json',
      label: 'whole node source closure bond seed probes progress',
    },
    {
      href: 'whole-node-source-closure-bond-seed-probes-review.md',
      label: 'whole node source closure bond seed probes review',
    },
    {
      href: 'whole-node-source-closure-candidate-progress.json',
      label: 'whole node source closure candidate progress',
    },
    {
      href: 'whole-node-source-closure-candidate-review.md',
      label: 'whole node source closure candidate review',
    },
    {
      href: 'whole-node-source-closure-device-params-candidate-progress.json',
      label: 'whole node source closure device params candidate progress',
    },
    {
      href: 'whole-node-source-closure-device-params-candidate-review.md',
      label: 'whole node source closure device params candidate review',
    },
    {
      href: 'whole-node-source-closure-device-params-probes-progress.json',
      label: 'whole node source closure device params probes progress',
    },
    {
      href: 'whole-node-source-closure-device-params-probes-review.md',
      label: 'whole node source closure device params probes review',
    },
    {
      href: 'whole-node-source-closure-groups-progress.json',
      label: 'whole node source closure groups progress',
    },
    {
      href: 'whole-node-source-closure-groups-review.md',
      label: 'whole node source closure groups review',
    },
    {
      href: 'whole-node-source-closure-micro-candidate-progress.json',
      label: 'whole node source closure micro candidate progress',
    },
    {
      href: 'whole-node-source-closure-micro-candidate-review.md',
      label: 'whole node source closure micro candidate review',
    },
    {
      href: 'whole-node-source-closure-microgroups-progress.json',
      label: 'whole node source closure microgroups progress',
    },
    {
      href: 'whole-node-source-closure-microgroups-review.md',
      label: 'whole node source closure microgroups review',
    },
    {
      href: 'whole-node-source-closure-next-candidate-progress.json',
      label: 'whole node source closure next candidate progress',
    },
    {
      href: 'whole-node-source-closure-next-candidate-review.md',
      label: 'whole node source closure next candidate review',
    },
    {
      href: 'whole-node-source-closure-next-probes-progress.json',
      label: 'whole node source closure next probes progress',
    },
    {
      href: 'whole-node-source-closure-next-probes-review.md',
      label: 'whole node source closure next probes review',
    },
    {
      href: 'whole-node-source-closure-nozzle-seed-candidate-progress.json',
      label: 'whole node source closure nozzle seed candidate progress',
    },
    {
      href: 'whole-node-source-closure-nozzle-seed-candidate-review.md',
      label: 'whole node source closure nozzle seed candidate review',
    },
    {
      href: 'whole-node-source-closure-nozzle-seed-probes-progress.json',
      label: 'whole node source closure nozzle seed probes progress',
    },
    {
      href: 'whole-node-source-closure-nozzle-seed-probes-review.md',
      label: 'whole node source closure nozzle seed probes review',
    },
    {
      href: 'whole-node-source-closure-refined-groups-progress.json',
      label: 'whole node source closure refined groups progress',
    },
    {
      href: 'whole-node-source-closure-refined-groups-review.md',
      label: 'whole node source closure refined groups review',
    },
    {
      href: 'whole-node-source-closure-system-domain-candidate-progress.json',
      label: 'whole node source closure system domain candidate progress',
    },
    {
      href: 'whole-node-source-closure-system-domain-candidate-review.md',
      label: 'whole node source closure system domain candidate review',
    },
    {
      href: 'whole-node-source-closure-system-domain-probes-progress.json',
      label: 'whole node source closure system domain probes progress',
    },
    {
      href: 'whole-node-source-closure-system-domain-probes-review.md',
      label: 'whole node source closure system domain probes review',
    },
    {
      href: 'whole-node-source-closure-wafer-single-probes-progress.json',
      label: 'whole node source closure wafer single probes progress',
    },
    {
      href: 'whole-node-source-closure-wafer-single-probes-review.md',
      label: 'whole node source closure wafer single probes review',
    },
    {
      href: 'whole-node-source-compile-progress.json',
      label: 'whole node source compile progress',
    },
    {
      href: 'whole-node-source-compile-v119-progress.json',
      label: 'whole node source compile v119 progress',
    },
    {
      href: 'whole-node-source-compile-v119-review.md',
      label: 'whole node source compile v119 review',
    },
    {
      href: 'whole-node-source-compile-v12-progress.json',
      label: 'whole node source compile v12 progress',
    },
    {
      href: 'whole-node-source-compile-v12-review.md',
      label: 'whole node source compile v12 review',
    },
    {
      href: 'whole-node-source-compile-v120-progress.json',
      label: 'whole node source compile v120 progress',
    },
    {
      href: 'whole-node-source-compile-v120-review.md',
      label: 'whole node source compile v120 review',
    },
    {
      href: 'whole-node-source-compile-v120-small-candidate-progress.json',
      label: 'whole node source compile v120 small candidate progress',
    },
    {
      href: 'whole-node-source-compile-v120-small-candidate-review.md',
      label: 'whole node source compile v120 small candidate review',
    },
    {
      href: 'whole-node-source-compile-v21-progress.json',
      label: 'whole node source compile v21 progress',
    },
    {
      href: 'whole-node-source-compile-v21-review.md',
      label: 'whole node source compile v21 review',
    },
    {
      href: 'whole-node-source-compile-v23-progress.json',
      label: 'whole node source compile v23 progress',
    },
    {
      href: 'whole-node-source-compile-v23-review.md',
      label: 'whole node source compile v23 review',
    },
    {
      href: 'whole-node-source-compile-v26-progress.json',
      label: 'whole node source compile v26 progress',
    },
    {
      href: 'whole-node-source-compile-v26-review.md',
      label: 'whole node source compile v26 review',
    },
    {
      href: 'whole-node-source-compile-v32-progress.json',
      label: 'whole node source compile v32 progress',
    },
    {
      href: 'whole-node-source-compile-v32-review.md',
      label: 'whole node source compile v32 review',
    },
    {
      href: 'whole-node-source-compile-v42-progress.json',
      label: 'whole node source compile v42 progress',
    },
    {
      href: 'whole-node-source-compile-v42-review.md',
      label: 'whole node source compile v42 review',
    },
    {
      href: 'whole-node-source-compile-v45-progress.json',
      label: 'whole node source compile v45 progress',
    },
    {
      href: 'whole-node-source-compile-v45-review.md',
      label: 'whole node source compile v45 review',
    },
    {
      href: 'whole-node-source-compile-v78-progress.json',
      label: 'whole node source compile v78 progress',
    },
    {
      href: 'whole-node-source-compile-v78-review.md',
      label: 'whole node source compile v78 review',
    },
    {
      href: 'whole-node-source-compile-v94-progress.json',
      label: 'whole node source compile v94 progress',
    },
    {
      href: 'whole-node-source-compile-v94-review.md',
      label: 'whole node source compile v94 review',
    },
    {
      href: 'workflow-catalog.json',
      label: 'workflow catalog',
    },
    {
      href: 'zx2200-architecture-analysis.md',
      label: 'zx2200 architecture analysis',
    },
    {
      href: 'zx2200-architecture.archify.json',
      label: 'zx2200 architecture.archify',
    },
    {
      href: 'zx2200-architecture.html',
      label: 'zx2200 architecture',
    },
    {
      href: 'zx2200-final-integrated-report.md',
      label: 'zx2200 final integrated report',
    },
  ],
  flowchartCatalog: {
    schemaVersion: 1,
    title: 'ZX2200 已处理流程图总览',
    generatedOn: '2026-10-08',
    scope:
      'docs/archify 中的 Archify 图纸规格、交付 HTML 与补充图页；视觉证据指 *.visual-check.html 自动化产物。',
    counts: {
      total: 65,
      archifySpecs: 62,
      deliveredHtml: 65,
      visualEvidence: 27,
      htmlMissing: 0,
      supplementalHtmlOnly: 3,
      mainChapters: 8,
    },
    groups: {
      main: '01 主流程章节',
      workflow: '02 工作流专题',
      sequence: '03 时序图',
      dataflow: '04 数据流图',
      architecture: '05 架构图',
      supplemental: '06 HTML 补充页',
    },
    entries: [
      {
        id: 'startup-workflow',
        title: '01 · 启动、回零与生产放行',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'main',
        groupLabel: '01 主流程章节',
        chapter: 1,
        qualityProfile: 'showcase',
        nodeCount: 12,
        relationCount: 10,
        spec: 'docs/archify/startup-workflow.archify.json',
        html: 'docs/archify/startup-workflow.html',
        visualCheck: 'docs/archify/startup-workflow.visual-check.html',
        evidence: null,
        specSha256: '8d6dddc806575d1d6878ee681e06fbbc5bf618cec855053155ca25350dfaa4ba',
        htmlSha256: '46e20fc387c43a05485f9873a82964cd192ad7b576f02a82567aeff99d99e3f3',
        visualCheckSha256: '8e5330cc91dc08acfeb9500d54404085832172f2a013cc46dfeec073bfd0f2e4',
        evidenceSha256: null,
        portalStatus: 'pass',
        status: 'delivered-visual-evidence',
      },
      {
        id: 'transport-workflow',
        title: '02 · 载具输送与上下料',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'main',
        groupLabel: '01 主流程章节',
        chapter: 2,
        qualityProfile: 'showcase',
        nodeCount: 11,
        relationCount: 12,
        spec: 'docs/archify/transport-workflow.archify.json',
        html: 'docs/archify/transport-workflow.html',
        visualCheck: 'docs/archify/transport-workflow.visual-check.html',
        evidence: null,
        specSha256: '91fc75766ff6e6d9b7aa4bd5888f10c523e27c23ecdd7ce0e31de563282542e7',
        htmlSha256: 'a9933186f8638e3bb3919c4b786b209f1001710ca45e2649ace7398965e6a8ae',
        visualCheckSha256: '598a753c413045c0bd141ce3457e3a8a331b20e51d72dc1e855996e0ec6a4420',
        evidenceSha256: null,
        portalStatus: 'pass',
        status: 'delivered-visual-evidence',
      },
      {
        id: 'dispense-workflow',
        title: '03 · S1 配方、点胶与分段交接',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'main',
        groupLabel: '01 主流程章节',
        chapter: 3,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 12,
        spec: 'docs/archify/dispense-workflow.archify.json',
        html: 'docs/archify/dispense-workflow.html',
        visualCheck: 'docs/archify/dispense-workflow.visual-check.html',
        evidence: null,
        specSha256: '4d4f85cc8e2653c808dd765665a03960f0d1518f9c9174f011b03e8e3ad951d2',
        htmlSha256: '7e8083f9bc7e8a5bb9a6ee29bafd3bdab12285b9c57855c83acd6d40627822f9',
        visualCheckSha256: '91c318565a6373b04c7aa89d5feb2a60a12e0758d99305eef7d15545c61c2779',
        evidenceSha256: null,
        portalStatus: 'pass',
        status: 'delivered-visual-evidence',
      },
      {
        id: 'wafer-supply-workflow',
        title: '04 · 晶圆供料、换料与翻转',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'main',
        groupLabel: '01 主流程章节',
        chapter: 4,
        qualityProfile: 'showcase',
        nodeCount: 12,
        relationCount: 15,
        spec: 'docs/archify/wafer-supply-workflow.archify.json',
        html: 'docs/archify/wafer-supply-workflow.html',
        visualCheck: 'docs/archify/wafer-supply-workflow.visual-check.html',
        evidence: null,
        specSha256: 'b82a7bc21c71010eb008c3177e401af31b16a63e10e612bdfa07d86258817897',
        htmlSha256: '0cbd1e88862a7ffeb23b88f83ffe47dc2bf18f832439d8098237383aed1d6d5f',
        visualCheckSha256: '1e52dce9000e88d6b8badfcdf6261a28d2f1319368d1233743d1b2c437b26c20',
        evidenceSha256: null,
        portalStatus: 'pass',
        status: 'delivered-visual-evidence',
      },
      {
        id: 'bonding-workflow',
        title: '05 · S2 配方调度与载具完成',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'main',
        groupLabel: '01 主流程章节',
        chapter: 5,
        qualityProfile: 'showcase',
        nodeCount: 12,
        relationCount: 15,
        spec: 'docs/archify/bonding-workflow.archify.json',
        html: 'docs/archify/bonding-workflow.html',
        visualCheck: 'docs/archify/bonding-workflow.visual-check.html',
        evidence: null,
        specSha256: '8bccd108e58f612e029760bdbdd03a744f32642b3a83e5d2754724b961d59c90',
        htmlSha256: '870a72a901f172eba6c4c56f878553b76ea651b3f7294e29b5367130bb8a1bcc',
        visualCheckSha256: '7ddc0034621e21fb5a05c95ba01618d1009e9180e7439ca3e92544d12723ede9',
        evidenceSha256: null,
        portalStatus: 'pass',
        status: 'delivered-visual-evidence',
      },
      {
        id: 'pickup-workflow',
        title: '06 · 取晶动作与漏晶恢复',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'main',
        groupLabel: '01 主流程章节',
        chapter: 6,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 13,
        spec: 'docs/archify/pickup-workflow.archify.json',
        html: 'docs/archify/pickup-workflow.html',
        visualCheck: 'docs/archify/pickup-workflow.visual-check.html',
        evidence: null,
        specSha256: '3794c6d91bb4d7defbedc6304a9c0070b9767da528f0999878a53657149fd90d',
        htmlSha256: 'c3adcf32362506835cb526410041a0b24f25c2df824b354d8febc75c510424e3',
        visualCheckSha256: 'd847eea32a94596ebc02be0fdb1d4752d4c0f20a834b9cf0e4acac3b782e0249',
        evidenceSha256: null,
        portalStatus: 'pass',
        status: 'delivered-visual-evidence',
      },
      {
        id: 'bond-action-workflow',
        title: '07 · 固晶动作与回带恢复',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'main',
        groupLabel: '01 主流程章节',
        chapter: 7,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 11,
        spec: 'docs/archify/bond-action-workflow.archify.json',
        html: 'docs/archify/bond-action-workflow.html',
        visualCheck: 'docs/archify/bond-action-workflow.visual-check.html',
        evidence: null,
        specSha256: '7dc94b75a1ab56f2f79ae4bc866ff1d6e8921a19201aeb1a0d707f3879503a83',
        htmlSha256: '58c4b72faafd98c18088eb7a0179a9a1adbc459b6d0185950f772a7915a4e657',
        visualCheckSha256: '5eb5705eef036ac35e09eaf0b296762531d47b9651f04806672e3b778289fca0',
        evidenceSha256: null,
        portalStatus: 'pass',
        status: 'delivered-visual-evidence',
      },
      {
        id: 'failure-recovery-workflow',
        title: '08 · 暂停、重试、停止与线程边界',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'main',
        groupLabel: '01 主流程章节',
        chapter: 8,
        qualityProfile: 'showcase',
        nodeCount: 12,
        relationCount: 13,
        spec: 'docs/archify/failure-recovery-workflow.archify.json',
        html: 'docs/archify/failure-recovery-workflow.html',
        visualCheck: 'docs/archify/failure-recovery-workflow.visual-check.html',
        evidence: null,
        specSha256: '4218852f9be55010207f974e168950e252b7b5f0b0e760379e5071fd11fcb826',
        htmlSha256: 'b7a9ca3af8d6a4ad4148e589013dae46c650ef8e3c9a6133fe5a77bb22304290',
        visualCheckSha256: 'cbef59131c3e4f41d67db7cb19f7ed45e08c55fc5f61bf5d37744a649ebe2b5f',
        evidenceSha256: null,
        portalStatus: 'pass',
        status: 'delivered-visual-evidence',
      },
      {
        id: 'epoxy-template',
        title: '胶量模板 · 声明的模块连接',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 9,
        spec: 'docs/archify/epoxy-template.workflow.archify.json',
        html: 'docs/archify/epoxy-template.workflow.html',
        visualCheck: 'docs/archify/epoxy-template.workflow.visual-check.html',
        evidence: null,
        specSha256: 'b863e997616b210c88b198b1b5679bf02575fc18db20c292ea3cd34c616b19d1',
        htmlSha256: '592f8ffe3fb62c7b942e7b8321fa8c6e8554d2a3cd5b7a0f13f02b181f8004b8',
        visualCheckSha256: 'b569d81e8f58e8e37ddec13b61f70d9dc301cbf4109d07337f15b807cdc71933',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'safe-motion',
        title: 'ZX2200 · 安全移动2D/3D/4D',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 11,
        spec: 'docs/archify/safe-motion.workflow.archify.json',
        html: 'docs/archify/safe-motion.html',
        visualCheck: 'docs/archify/safe-motion.visual-check.html',
        evidence: null,
        specSha256: '3ffb56a7815c7d8264686e23d2dc067eb62d0e7698c218e6c7a848c30778450a',
        htmlSha256: 'b30a62a46beea918d92a2d1f11e5484b85857e4fc3be68768fbe7011ac345367',
        visualCheckSha256: '0aebcd27ffebace9c45768f4eb5811fd154f25897bd655334dcf5c18dafeb836',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'mapping-restore-workflow',
        title: 'ZX2200 · 码值 Mapping 恢复',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 9,
        spec: 'docs/archify/mapping-restore-workflow.archify.json',
        html: 'docs/archify/mapping-restore-workflow.html',
        visualCheck: 'docs/archify/mapping-restore-workflow.visual-check.html',
        evidence: null,
        specSha256: 'c06070dfa5ddbaa3fd1459bc8f1cc2a1c29198dbff9b5083666e5f9be246facf',
        htmlSha256: 'e6065b149f7044281e505d850f63398c58b174cd6af4f3b6b094268dffb25de8',
        visualCheckSha256: 'f4f393426e7f291eee976eb52642e874b452693da4877410a03d36af42164fb9',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'stop-cleanup-workflow',
        title: 'ZX2200 · 普通停止的真实清理顺序',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 7,
        relationCount: 7,
        spec: 'docs/archify/stop-cleanup-workflow.archify.json',
        html: 'docs/archify/stop-cleanup-workflow.html',
        visualCheck: 'docs/archify/stop-cleanup-workflow.visual-check.html',
        evidence: null,
        specSha256: '0218d0ac682415a9e2a90348266a0e1933e5bef1903cf0b79a09bc704ec31bad',
        htmlSha256: 'c2b87f7b978404ef209d828514eebb86831b541f04208896f324e97b30c982b1',
        visualCheckSha256: 'c00b459d8a9c47aeac119ad1311387538cd65b38da4162210382e52acc5ca5e6',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'manual-epoxy-trial',
        title: 'ZX2200 · 手动试胶执行与退出',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 11,
        relationCount: 9,
        spec: 'docs/archify/manual-epoxy-trial.workflow.archify.json',
        html: 'docs/archify/manual-epoxy-trial.html',
        visualCheck: 'docs/archify/manual-epoxy-trial.visual-check.html',
        evidence: null,
        specSha256: 'afe1a9b64d8e2d00effa9850af40dccb6dc9565904a18344cabd4e694cea0ab8',
        htmlSha256: '4f0537c6dac784f561744282f08171edaba4dabc2b0ab6f64a26c3a3f2b6d146',
        visualCheckSha256: '4440a23dfae2abbd19e0998eef55d41403cae5af1c0000da02591df12fb57d5f',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'nozzle-exchange',
        title: 'ZX2200 · 自动换吸嘴执行链',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 11,
        relationCount: 11,
        spec: 'docs/archify/nozzle-exchange.workflow.archify.json',
        html: 'docs/archify/nozzle-exchange.html',
        visualCheck: 'docs/archify/nozzle-exchange.visual-check.html',
        evidence: null,
        specSha256: 'e5ce541705a12caf009b39b9bffeb29c8d08509c7cc70c0fd9e53b803985d3b3',
        htmlSha256: 'e11e91fca207989785e911c9d8a9c628015daecfa635c53462c898091aa60355',
        visualCheckSha256: 'e985378297cc16281ee02eabb0084d33866cfca497a5b1def36cc354612e3f3e',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'calibration-task-workflow',
        title: 'ZX2200 标定任务执行与结果保存',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 9,
        relationCount: 11,
        spec: 'docs/archify/calibration-task-workflow.archify.json',
        html: 'docs/archify/calibration-task-workflow.html',
        visualCheck: null,
        evidence: null,
        specSha256: '535ef98de9c9257c0d22f21774f82047200a3cb847cbb8f8ba6ef43af42f9460',
        htmlSha256: '2026b0f19cc85455c3a0a419d1c8d9deb61924a13e700f646f9318f410e37888',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'calibration-execution-workflow',
        title: 'ZX2200 标定执行流程',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 10,
        spec: 'docs/archify/calibration-execution-workflow.archify.json',
        html: 'docs/archify/calibration-execution-workflow.html',
        visualCheck: 'docs/archify/calibration-execution-workflow.visual-check.html',
        evidence: null,
        specSha256: '0f61d4f16b12d24d318d3395b0ce2e3bc3ca00e3e4d13dc43a44ce4d6216a181',
        htmlSha256: '5bceb759b03c943c524b9ab72a01b1ca902e6ea9ecd3217ed1cf51bf447227b0',
        visualCheckSha256: 'eeed451e85e9f1a221fd86801192afc2443d460f4a8603147fdb4e7618d075dd',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'transport-pause-stop-workflow',
        title: 'ZX2200 固晶输送暂停、Stop 与状态提交',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 9,
        relationCount: 10,
        spec: 'docs/archify/transport-pause-stop-workflow.archify.json',
        html: 'docs/archify/transport-pause-stop-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/transport-pause-review.md',
        specSha256: '019e92bb56b40429a621d56153a0129b66c04ed76adbeb3bac585dc49c6b19be',
        htmlSha256: '5322a4a21befa70da50823e180e8c2882f3ecc1d3aac9525803129a4e0867461',
        visualCheckSha256: null,
        evidenceSha256: 'a15e1d56cc465f7f6c2230228122a919ad20793b26331384d583d8fbb144443a',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'postbond-feedback-workflow',
        title: 'ZX2200 焊后反馈与补偿失败路径',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 11,
        relationCount: 11,
        spec: 'docs/archify/postbond-feedback-workflow.archify.json',
        html: 'docs/archify/postbond-feedback-workflow.html',
        visualCheck: 'docs/archify/postbond-feedback-workflow.visual-check.html',
        evidence: null,
        specSha256: 'e40b7c278641afb5d5d8eb3f96c00c429143ccb764b60b9298be4e0a36c8f833',
        htmlSha256: '629626d6795145cddfd1c646d28ae8e45e81c32e7e5d89317846e56d470685f8',
        visualCheckSha256: '7778b63f6d66b447595cd7a6dd321cc87e23b044a8fbe5d00dfa95cb39514047',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'bond-camera-calibration-workflow',
        title: 'ZX2200 焊头到相机偏移标定',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 11,
        relationCount: 12,
        spec: 'docs/archify/bond-camera-calibration-workflow.archify.json',
        html: 'docs/archify/bond-camera-calibration-workflow.html',
        visualCheck: 'docs/archify/bond-camera-calibration-workflow.visual-check.html',
        evidence: null,
        specSha256: 'f6261c85131a37a0e9c11736d6ce963b63bf41a0d318bf774bfda19c99d031e5',
        htmlSha256: '14507a0e3a77628ac33c5346f416a83cb89d3c0b2495655140a04a4a0190c292',
        visualCheckSha256: '158d8a3c555aff9a1398d58add32c2d48d1ab23538990b1e637cb982bb6dfb8e',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'background-lifecycle-workflow',
        title: 'ZX2200 后台监控与退出',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 9,
        spec: 'docs/archify/background-lifecycle-workflow.archify.json',
        html: 'docs/archify/background-lifecycle-workflow.html',
        visualCheck: 'docs/archify/background-lifecycle-workflow.visual-check.html',
        evidence: null,
        specSha256: 'b5bc1c3418eb13ef3aa464ae0c7fc85d5d7938fb86330835bb0691ac6b42d666',
        htmlSha256: '3132ba2934fca1bc897fead6445071661e5a659f882a72255cf0e9ea057ad79a',
        visualCheckSha256: '27584fa882d758d47cad9877f60b0533900e64954c8a43de8d42451abe0b5a44',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'wafer-selection-consistency-workflow',
        title: 'ZX2200 换片名称选择与保存对象一致性',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 8,
        relationCount: 8,
        spec: 'docs/archify/wafer-selection-consistency-workflow.archify.json',
        html: 'docs/archify/wafer-selection-consistency-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/wafer-selection-review.md',
        specSha256: 'b0e26307df7a19e1a1b7fa431e6ad209024a15e71c0636ed32cd1594d57f5832',
        htmlSha256: 'ebdfd9a9170c29af4dd1312dbbcbb7db0aa474d48de0c98e64c968da8bda2e42',
        visualCheckSha256: null,
        evidenceSha256: '5a72035e493ee43313a114fdce436f0ccea9bc5ec129a404e0d62307e49bfdae',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'emergency-stop-close-workflow',
        title: 'ZX2200 急停、Stop 与任务关闭边界',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 8,
        relationCount: 7,
        spec: 'docs/archify/emergency-stop-close-workflow.archify.json',
        html: 'docs/archify/emergency-stop-close-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/emergency-abort-review.md',
        specSha256: 'f0085796b823c65eb2cae74eca7142f7272d3d64701dc4ec17b809ac2d5cda8a',
        htmlSha256: '79fe01e94220d2181d9d82b7423c2520ab41112923196ca7524d2f9d51f9b842',
        visualCheckSha256: null,
        evidenceSha256: 'ca8c9e244a62c4341f850a1b5a0eb15c6028d6efe2076fe4cd06d42615b8511e',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'dispense-config-consumption-workflow',
        title: 'ZX2200 胶型配置与生产消费',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 11,
        relationCount: 11,
        spec: 'docs/archify/dispense-config-consumption-workflow.archify.json',
        html: 'docs/archify/dispense-config-consumption-workflow.html',
        visualCheck: 'docs/archify/dispense-config-consumption-workflow.visual-check.html',
        evidence: null,
        specSha256: '89cda6fbfae9ef867add0dd27b96b2740b9fdaa7f2b82b62a3e48f9b0e24dbca',
        htmlSha256: '996f4cc84d3f4d6e63510684e61756f968117bb477b8e13061888ed8a65629be',
        visualCheckSha256: '6142f0830691d70441f83c0387131cc39552f2d2d0601a36c5d785e62a8d8b81',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'recipe-initialization-workflow',
        title: 'ZX2200 配方重载：初始化与视觉边界',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 10,
        spec: 'docs/archify/recipe-initialization-workflow.archify.json',
        html: 'docs/archify/recipe-initialization-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/recipe-initialization-source-review.md',
        specSha256: '9a04ecd35766f98658a34c04806faca6b15a0cee7256f98defcb569c3762a65b',
        htmlSha256: 'bb83259626fa3e624af74414cfc23dbb4d004c25abd6db8e471268b8db9e80e4',
        visualCheckSha256: null,
        evidenceSha256: 'ce089b4dd903bde9e08350b3c2281cfe56446bb9eb0152129f773a6ad7f36565',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'recipe-lifecycle-workflow',
        title: 'ZX2200 配置与配方生命周期',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 9,
        relationCount: 9,
        spec: 'docs/archify/recipe-lifecycle-workflow.archify.json',
        html: 'docs/archify/recipe-lifecycle-workflow.html',
        visualCheck: null,
        evidence: null,
        specSha256: '1da9c7092e60484cdea19775c0b4cf90d6d33585a9397a77eecd0bc530960d99',
        htmlSha256: 'd0e8f03e7ea0f39cc07861cf1f34275da7ee878716b264fcc6c5445e905fa3ff',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'permission-gating-workflow',
        title: 'ZX2200 权限与编辑事件门控',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 9,
        relationCount: 9,
        spec: 'docs/archify/permission-gating-workflow.archify.json',
        html: 'docs/archify/permission-gating-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/permission-gating-review.md',
        specSha256: 'cd05faa6a6864f1d020d8acaa7ac444973384aef87c24a46ae85cc109adc5f3a',
        htmlSha256: '935e1055708ca803f42b0f61f0e4f9d4cf2e4130b0389561f76f3be9eefc6e6b',
        visualCheckSha256: null,
        evidenceSha256: '1fa479bb9fd90a77f63ec18627dcf5936895e069c178f37ae41a2d17dff8b847',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'task-closure-gate-workflow',
        title: 'ZX2200 任务关闭门控与停止提示',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 8,
        relationCount: 7,
        spec: 'docs/archify/task-closure-gate-workflow.archify.json',
        html: 'docs/archify/task-closure-gate-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/task-closure-review.md',
        specSha256: 'be39d0a55081c774fe11ed2b07fd949d84b407e4db436964da7333f47eab9918',
        htmlSha256: '487d4e2de15e17ad30a12f9758fd96a3f80e82f5f6369e9e743d2431045ca24f',
        visualCheckSha256: null,
        evidenceSha256: 'e5654c43b6553a9e4b93d3e2a99e5da52417f3cfe115f994934d82280834c609',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'vision-motion-workflow',
        title: 'ZX2200 视觉、运动与补偿链路',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 9,
        relationCount: 10,
        spec: 'docs/archify/vision-motion-workflow.archify.json',
        html: 'docs/archify/vision-motion-workflow.html',
        visualCheck: null,
        evidence: null,
        specSha256: 'ba5bc849ac4ccf3869369950f4c611a9d2cbc070897a81c9025599a03b95c55b',
        htmlSha256: '3103808a9297841ce95cf795536276bf5cf084e7f5ca4bb43988bb06272be309',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'maintenance-calibration-workflow',
        title: 'ZX2200 手动维护、报警与标定',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 8,
        relationCount: 8,
        spec: 'docs/archify/maintenance-calibration-workflow.archify.json',
        html: 'docs/archify/maintenance-calibration-workflow.html',
        visualCheck: null,
        evidence: null,
        specSha256: '7e1b33d8da84935547bc8b26eee910beed3afa1a79c04c9801bb5a14daa808a0',
        htmlSha256: '210e9994afe8c49bcbd7ca80bc3690492a271cc611a4c17ba448a76ccd110ea0',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'wafer-search-gate-workflow',
        title: 'ZX2200 四种搜晶路径、结束出口与供晶许可',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 33,
        relationCount: 22,
        spec: 'docs/archify/wafer-search-gate-workflow.archify.json',
        html: 'docs/archify/wafer-search-gate-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/wafer-search-gates-review.md',
        specSha256: '36fb618b78352feb7cf90c0304dd308c2725a1b682e84f31e22a69269f6959c1',
        htmlSha256: 'eb6389354e969b8eb71ad5d5a8e909d73faf43c1c53beca4e9385698e7ec20a3',
        visualCheckSha256: null,
        evidenceSha256: '7ad7bc85e7f83f12d2f5fe9d9f289dfc97c1de476d5c7e3c5e5f99bdaff4ae37',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'exit-save-workflow',
        title: 'ZX2200 停止、数据保存与进程退出',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 8,
        relationCount: 9,
        spec: 'docs/archify/exit-save-workflow.archify.json',
        html: 'docs/archify/exit-save-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-mainform-close-save-review.md',
        specSha256: 'f91d2db21423bee8427bd952585b3fa012cb15589a934529154614e459ad2f7a',
        htmlSha256: '98b24065fb9684db3bdec2c89146c3acc42e59bd348a0de51cf7c55b9d21278f',
        visualCheckSha256: null,
        evidenceSha256: '47120a2709d35a4062e12a00d26ec99633e50ddf6d32c30bfe4993b853ca6167',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'relative-bond-order-workflow',
        title: 'ZX2200 相对贴片动作排序与视觉步骤重排',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 9,
        relationCount: 8,
        spec: 'docs/archify/relative-bond-order-workflow.archify.json',
        html: 'docs/archify/relative-bond-order-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/relative-bond-order-review.md',
        specSha256: '6fbf8097b698f52b3397b6a91a5f456a0639ad332815783606de36d7b18ccaec',
        htmlSha256: '7122a7c88dcf9581b50283254532d8f101d545076faf40726bdfeb5bd27bd0b7',
        visualCheckSha256: null,
        evidenceSha256: 'e5e73df398369bf78971e2c1c5e0a759256ec5852c4823862cc9d2caa8abcf06',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'recipe-live-reload-workflow',
        title: 'ZX2200 运行中配方重载与任务边界',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 8,
        relationCount: 8,
        spec: 'docs/archify/recipe-live-reload-workflow.archify.json',
        html: 'docs/archify/recipe-live-reload-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-recipe-live-reload-review.md',
        specSha256: 'dc7cba5f774552080e0290d98e9913598f4165844df488920a0c2ce63ae833bc',
        htmlSha256: '58733e7426ec787fdff616b7cb5933aa787c3a1775569ed8fc16722ba013aecd',
        visualCheckSha256: null,
        evidenceSha256: 'ee391c297f582a197fd9d86274b7451d5f7ea4b9d21036b7f82b48fbb36589b1',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'wafer-change-retry-workflow',
        title: 'ZX2200 自动换料：路径选择与三个重试入口',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 18,
        relationCount: 15,
        spec: 'docs/archify/wafer-change-retry-workflow.archify.json',
        html: 'docs/archify/wafer-change-retry-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/wafer-change-retry-review.md',
        specSha256: '70920f45eafcdd2f46130b40e827c3ac9b505a252f0afea95c7177fcb8bbfb72',
        htmlSha256: '09676321dbaaf0c997a7ecde3b56c26a63e60469f29635b004f735e726cf5070',
        visualCheckSha256: null,
        evidenceSha256: '7955bbbb0f6323dcbc48993fcce6bd8413b08b04c21f4263edd7b70d3d7ebe3c',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'automation-workflow',
        title: 'ZX2200 Automation Workflow',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 12,
        relationCount: 16,
        spec: 'docs/archify/automation-workflow.archify.json',
        html: 'docs/archify/automation-workflow.html',
        visualCheck: null,
        evidence: null,
        specSha256: 'e4dea3974ca162844b35225a94265c6d1f893460a284f2952e8c3489ec2da9b7',
        htmlSha256: 'de4c54c8cd634a12d9795807288e28497617759bf70f52b2668dd28ab6e64795',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'machine-start-readiness-workflow',
        title: 'ZX2200 Machine.Start 启动就绪与任务调用链',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 9,
        spec: 'docs/archify/machine-start-readiness-workflow.archify.json',
        html: 'docs/archify/machine-start-readiness-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/machine-start-readiness-review.md',
        specSha256: '8a60ff11bdf4d12c648189c1440ae1e2d19f50fb082ef9840ced5ab77da39cb3',
        htmlSha256: '525291c8e23678e286b5558aa7521340230f440aea5f0d19a2085001fc1e51c2',
        visualCheckSha256: null,
        evidenceSha256: '2c30b5a1328093e5aa013f1a12e530ed89f4622758ebb79f677b1773b824aff9',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's1-step-commit-gate-workflow',
        title: 'ZX2200 S1 步骤提前提交、Abort/Fail 与任务关闭查询',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 8,
        spec: 'docs/archify/s1-step-commit-gate-workflow.archify.json',
        html: 'docs/archify/s1-step-commit-gate-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-s1-step-commit-review.md',
        specSha256: '7a00e498cf7688c561214416d45102f6ba444961de465a51756412477aa38e45',
        htmlSha256: '4bf2594d89e4e8c3e3bcc46afa48ae8909572fd43f98f9c2c154d9b6d21c2d27',
        visualCheckSha256: null,
        evidenceSha256: '80a2f60b1c4e5f67411a719e3387af4f342cf56f34d3d1599e101792a9ee7e2e',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's1-return-gates-workflow',
        title: 'ZX2200 S1 点胶 Abort/Fail、外层早退与 finally 刷新',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 11,
        spec: 'docs/archify/s1-return-gates-workflow.archify.json',
        html: 'docs/archify/s1-return-gates-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-s1-return-gates-review.md',
        specSha256: '466ef34bdc5bbbe9058b7a94801dfe176a06b9ca8be76d39c1c8460c1e761e81',
        htmlSha256: '71d7d9b0a7bcf148b9af0503af0f0e750de73e44987fd077775fb1b4ce426cc0',
        visualCheckSha256: null,
        evidenceSha256: '7313236ba50f8dc16e6e27f18d3eabd8372a8b2aa1e40e904f12d3b325730ac7',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's1-segment-interaction-workflow',
        title: 'ZX2200 S1 分段交互、Pause/Stop 与完成事件边界',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 9,
        spec: 'docs/archify/s1-segment-interaction-workflow.archify.json',
        html: 'docs/archify/s1-segment-interaction-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-s1-segment-interaction-review.md',
        specSha256: '1dbadee5815bd01f0c985d8948864762b314f4e06f84d23baf06b53ae35edb94',
        htmlSha256: 'aad26e0e710feb4773a505d80cf55343977d38b1a74f838fd49c72ebd22faea2',
        visualCheckSha256: null,
        evidenceSha256: '31f9a94a56f591e9584881410ce316c9498d12599d1b91f6197deea2b7558d99',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's1-defect-outcome-workflow',
        title: 'ZX2200 S1 胶检结果、Retry 与异常传播',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 9,
        relationCount: 12,
        spec: 'docs/archify/s1-defect-outcome-workflow.archify.json',
        html: 'docs/archify/s1-defect-outcome-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-s1-defect-outcomes-review.md',
        specSha256: '46a1a46056c405f34e5be6f8f4b1d528ce41bed1f3cb974514db00c7b7f00781',
        htmlSha256: '349d5f12c951bf420dece8a5ec8856f4372860273067c16382df78f5ab3508c1',
        visualCheckSha256: null,
        evidenceSha256: '7cd14e33d1aea640740ef95885b4da6c2d592f7413d7d77a5454a7f93023afbc',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's1-rework-context-workflow',
        title: 'ZX2200 S1 胶检选择映射与 ReDispense 重做边界',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 12,
        relationCount: 13,
        spec: 'docs/archify/s1-rework-context-workflow.archify.json',
        html: 'docs/archify/s1-rework-context-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-s1-rework-context-review.md',
        specSha256: 'f5a7d2053ee210221d0c20195506828e0d0614714ef99393034e0faaef070875',
        htmlSha256: '1b499992a8d673fcead2d8c5a3556ddc3f6a6a8a862f3ea8072b963931cbea2a',
        visualCheckSha256: null,
        evidenceSha256: '36452bb130bd701db41413bcb28292a6367ff1c5f449568c82da5bd44e6edfa3',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's1-stop-rework-recovery-workflow',
        title: 'ZX2200 S1 停止、重启与返工恢复',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 11,
        relationCount: 10,
        spec: 'docs/archify/s1-stop-rework-recovery-workflow.archify.json',
        html: 'docs/archify/s1-stop-rework-recovery-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-s1-stop-recovery-review.md',
        specSha256: '4b574b7651eb48dc218d317fbae656caec25e14b5ad8c1850b208377f817dc44',
        htmlSha256: '511ae123c74687fe6627d1dd18028706b1b40677b79675a705745e20a1d0ef66',
        visualCheckSha256: null,
        evidenceSha256: '2a423bbd0a174d7ecf5346b8c1935d1c12238fef4f652cc2cffcf3b2146a1386',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's1-task-loop-pause-workflow',
        title: 'ZX2200 S1 Working 任务的暂停、继续与停止窗口',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 10,
        relationCount: 9,
        spec: 'docs/archify/s1-task-loop-pause-workflow.archify.json',
        html: 'docs/archify/s1-task-loop-pause-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-s1-working-pause-review.md',
        specSha256: '39932c00a49b76f098082a5967a24f1ebf28cf9cfcdb3b192ee2fe5e9965daa7',
        htmlSha256: '478de219c977dbba736db7483aed411c92aa86f275ba9415bfef966e8b494d92',
        visualCheckSha256: null,
        evidenceSha256: 'b6e684fbfccdd3e4515de604b842b2b4c917bb9dd9e11c3a31e0bec5265a167f',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'process-step-injection-workflow',
        title: 'ZX2200 S1/S2 步骤注入与完成状态保留',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 7,
        relationCount: 8,
        spec: 'docs/archify/process-step-injection-workflow.archify.json',
        html: 'docs/archify/process-step-injection-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/process-step-injection-review.md',
        specSha256: 'b0bb140e2babfd6fbc05f070177c85323526edc39132c25f58ede75d38a51331',
        htmlSha256: '4b89c2b5e98182c53bf08726671325f647d93452f035e37547850b95c9d1c54a',
        visualCheckSha256: null,
        evidenceSha256: '6f13d5b4fd15318e8953e0fcb12d5a2df454a457a5afab7566c42bbca3c0ff43',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's2-action-boundary-workflow',
        title: 'ZX2200 S2 动作入口、模式门控与步骤提交',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 18,
        relationCount: 12,
        spec: 'docs/archify/s2-action-boundary-workflow.archify.json',
        html: 'docs/archify/s2-action-boundary-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-s2-action-boundaries-review.md',
        specSha256: 'a730feecefbc6a64072ba878a9ef09911823e7cf6e467fffc1084300eedd3197',
        htmlSha256: '5bb5410304c4f6b1d2a608573a8416a97141b3b5f06987aaedb467e57ba790e4',
        visualCheckSha256: null,
        evidenceSha256: 'e0a86ba52a2d0e31e8d0444ffcae03784181934e6f789be1fb3fc845323c30df',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's2-reset-retry-workflow',
        title: 'ZX2200 S2 焊头清零与 Retry / Ignore / Abort',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 9,
        relationCount: 10,
        spec: 'docs/archify/s2-reset-retry-workflow.archify.json',
        html: 'docs/archify/s2-reset-retry-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/original-s2-reset-il-review.md',
        specSha256: '62b89a6adc05e5bff3766e9e323e784919a840103702864fc49e2bbb652a70ec',
        htmlSha256: '66215e2d3a21c757f28d7ec1be5651bdc2e29fc6ca5cde88f053da2c8691df1e',
        visualCheckSha256: null,
        evidenceSha256: '7828a6d68479a51db6de1673cb9cbb51427f1cb40e036c6fee7f63b7b0cb0ee9',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 's2-task-entry-boundary-workflow',
        title: 'ZX2200 S2 任务入口、准备顺序与 Enable 门控',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 14,
        relationCount: 16,
        spec: 'docs/archify/s2-task-entry-boundary-workflow.archify.json',
        html: 'docs/archify/s2-task-entry-boundary-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-s2-task-entry-review.md',
        specSha256: 'a15bca204acdd80324146c83e40eed2765e469cd9062cc4398c938e19f88c40d',
        htmlSha256: '270146bc1d853b01347354f0b44793a48d657fb394a8e6c8685dc28341113f98',
        visualCheckSha256: null,
        evidenceSha256: 'e134bf040760b23f40dc785a63db9cbc9379c432b848c4f5ee9d00a254d1a5fd',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'statistics-log-producer-workflow',
        title: 'ZX2200 StatisticsService 日志生产与持久化',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 7,
        relationCount: 6,
        spec: 'docs/archify/statistics-log-producer-workflow.archify.json',
        html: 'docs/archify/statistics-log-producer-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/native-statistics-producer-review.md',
        specSha256: 'dab300a4b01303dceb28e8ad24ca71b70f68778bcc2751a254583b3961f88915',
        htmlSha256: 'ef775c9c81cb588f56c5d4b1097e046077e4579fab82f3005074deb887195ec8',
        visualCheckSha256: null,
        evidenceSha256: 'b00df5d3c21487811c69891d4d9f069542ab6ee8f578512c903d063b748628ec',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'transport-start-gating-workflow',
        title: 'ZX2200 TransportTask.Start 任务分配与返回码门控',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 9,
        relationCount: 9,
        spec: 'docs/archify/transport-start-gating-workflow.archify.json',
        html: 'docs/archify/transport-start-gating-workflow.html',
        visualCheck: null,
        evidence: 'docs/archify/transport-producer-review.md',
        specSha256: '0343052fb6a6ac35746b8f5dd639b8ab2badcc0dc4b33f2ea01512e6b7dccfbb',
        htmlSha256: 'b479300840f81dcecf450f067bf2369bbcb1abad2d24cfc33c8e5904df7693d2',
        visualCheckSha256: null,
        evidenceSha256: 'f47d9d1621c13a308275bfad7a06f2c5f4eadb05782c723c3262c301bcab6d20',
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'wafer-pick-handshake-sequence',
        title: '供晶与取片：请求、顶针、异步通知',
        type: 'sequence',
        typeLabel: '时序图',
        group: 'sequence',
        groupLabel: '03 时序图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 5,
        relationCount: 8,
        spec: 'docs/archify/wafer-pick-handshake-sequence.archify.json',
        html: 'docs/archify/wafer-pick-handshake-sequence.html',
        visualCheck: 'docs/archify/wafer-pick-handshake-sequence.visual-check.html',
        evidence: null,
        specSha256: '953c5d3b58c2c045531151af67f76238a535134bf1dd5c259389f449f7ac3b35',
        htmlSha256: '5e8be66d1e586bf78a0d665490af00f9155eced8ab2c3066ada990a62dc23681',
        visualCheckSha256: '6c32974bed1888a3be7c04ecf5784952925045f23fbb5aaff62af58309949e55',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'bin-configuration-sequence',
        title: '料仓配置：加载与名称解析',
        type: 'sequence',
        typeLabel: '时序图',
        group: 'sequence',
        groupLabel: '03 时序图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 4,
        relationCount: 9,
        spec: 'docs/archify/bin-configuration-sequence.archify.json',
        html: 'docs/archify/bin-configuration-sequence.html',
        visualCheck: 'docs/archify/bin-configuration-sequence.visual-check.html',
        evidence: null,
        specSha256: '6c8b87fdd994128a72eb63dc0a981a3c08e44f6072a3262bb97951008331a03d',
        htmlSha256: '6ad2d9fa450504bfd5735364a68fee0e2ebfdd0783931f3e08a45db0b8218a27',
        visualCheckSha256: '53444df60dacf347a288203acf58fa14961d33c4077c507947fcdd2c6f818f2b',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'bin-failure-handshake-sequence',
        title: '料仓握手：正常交互与异常等待',
        type: 'sequence',
        typeLabel: '时序图',
        group: 'sequence',
        groupLabel: '03 时序图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 4,
        relationCount: 9,
        spec: 'docs/archify/bin-failure-handshake-sequence.archify.json',
        html: 'docs/archify/bin-failure-handshake-sequence.html',
        visualCheck: 'docs/archify/bin-failure-handshake-sequence.visual-check.html',
        evidence: null,
        specSha256: 'b5b178e29b3e3f8db5265026220e59cbfd2827aed0993c9d2aed5e4bfc2596af',
        htmlSha256: '3b71e78a586a750f0735d5ead5ced5f0ea49bc4bf4e974850eb702b8feb8c2a8',
        visualCheckSha256: '5520e779e8301de93172fe632f74f052cba93abfe20bd7c7d84c25a1d48044e6',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'recipe-switch-sequence',
        title: 'ZX2200 · 配方切换调用时序',
        type: 'sequence',
        typeLabel: '时序图',
        group: 'sequence',
        groupLabel: '03 时序图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 6,
        relationCount: 11,
        spec: 'docs/archify/recipe-switch-sequence.archify.json',
        html: 'docs/archify/recipe-switch-sequence.html',
        visualCheck: 'docs/archify/recipe-switch-sequence.visual-check.html',
        evidence: null,
        specSha256: '0c9802f0b06eccf87e668f724c11416014caaeee1cfb191b822c14135f3c1de5',
        htmlSha256: 'dba5f62a2dd86c6afc1dafb08123159765fea6bc4976d03bcbaeee865f0cf745',
        visualCheckSha256: '5e37be24aced98d15afe81bc76b3eed586128b9ea64b79041f91b5d6537fb006',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 's2-predispense-retry',
        title: 'ZX2200 · 预点胶与报警重试',
        type: 'sequence',
        typeLabel: '时序图',
        group: 'sequence',
        groupLabel: '03 时序图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 6,
        relationCount: 14,
        spec: 'docs/archify/s2-predispense-retry.sequence.archify.json',
        html: 'docs/archify/s2-predispense-retry.sequence.html',
        visualCheck: 'docs/archify/s2-predispense-retry.sequence.visual-check.html',
        evidence: null,
        specSha256: 'c129126570e2066673b7d133a0fed83e2e02605f9531d8bb987ca5269ab9332b',
        htmlSha256: '85351651e8969a2ab78dd96592016c7bd38455bb12a1043ccb51cfb03b48d9aa',
        visualCheckSha256: 'b994f3520b56ee3ac7afac5ba5e3a582328cfc38f755765c53728e0f81118e07',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'background-task-sequence',
        title: 'ZX2200 · 主界面后台刷新',
        type: 'sequence',
        typeLabel: '时序图',
        group: 'sequence',
        groupLabel: '03 时序图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 5,
        relationCount: 10,
        spec: 'docs/archify/background-task-sequence.archify.json',
        html: 'docs/archify/background-task-sequence.html',
        visualCheck: 'docs/archify/background-task-sequence.visual-check.html',
        evidence: null,
        specSha256: '20f3267fd08626edb71562840593b8ad692ba5545bf568e7fb1dd4bd161c6cce',
        htmlSha256: '1fda4a44befc987539da8793b8e6b9b3ac92bf19625fe443e13b1ef52d607271',
        visualCheckSha256: 'ccee9ba49ca3763a5a8a1d5ee24ebdedc0517e9b003f0eb962c484e78d304889',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'motion-arrival-sequence',
        title: 'ZX2200 轴到位等待 · 源码与程序集分层',
        type: 'sequence',
        typeLabel: '时序图',
        group: 'sequence',
        groupLabel: '03 时序图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 6,
        relationCount: 10,
        spec: 'docs/archify/motion-arrival-sequence.archify.json',
        html: 'docs/archify/motion-arrival-sequence.html',
        visualCheck: 'docs/archify/motion-arrival-sequence.visual-check.html',
        evidence: null,
        specSha256: '10178fe3c288929de0a098af85eaa754c65548c76fe62f0003c3280b5886dff5',
        htmlSha256: 'af143334a0b8de3022c192f38e0a87db143798ac252fb108e7788031d33bfc4d',
        visualCheckSha256: 'b57c06e2a5ac96e12dc3a7af0e64aced342407b805760f7b1f4d07109698fce7',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'automation-sequence',
        title: 'ZX2200 First Direct Pickup — Runtime Sequence',
        type: 'sequence',
        typeLabel: '时序图',
        group: 'sequence',
        groupLabel: '03 时序图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 5,
        relationCount: 14,
        spec: 'docs/archify/automation-sequence.archify.json',
        html: 'docs/archify/automation-sequence.html',
        visualCheck: null,
        evidence: null,
        specSha256: '625227f2b40f3d29194835b937afebb52a8ab1f221b7130d5a9f65940f0efaf0',
        htmlSha256: '42cb28e2d9803582cccb5b77c320085c35dcbb50ae99dd8485331a9c0920545a',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'async-persistence-dataflow',
        title: 'ZX2200 图片与数据库异步保存链路',
        type: 'dataflow',
        typeLabel: '数据流图',
        group: 'dataflow',
        groupLabel: '04 数据流图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 4,
        relationCount: 7,
        spec: 'docs/archify/async-persistence-dataflow.archify.json',
        html: 'docs/archify/async-persistence-dataflow.html',
        visualCheck: 'docs/archify/async-persistence-dataflow.visual-check.html',
        evidence: null,
        specSha256: 'ddbffb346dd21f65f22812ab04d891b69d8560d8cf53061971b9160594ca36da',
        htmlSha256: '85a750685b8940f56c9b8b0707f459b92444ca0110b2b5b801fb8ed08572bab8',
        visualCheckSha256: 'a3adce1ae610f233119a26d3d8503653574b40374538f1ca5987a5d750a14ace',
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence',
      },
      {
        id: 'runtime-dataflow',
        title: 'ZX2200 运行数据与持久化流',
        type: 'dataflow',
        typeLabel: '数据流图',
        group: 'dataflow',
        groupLabel: '04 数据流图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 4,
        relationCount: 6,
        spec: 'docs/archify/runtime-dataflow.archify.json',
        html: 'docs/archify/runtime-dataflow.html',
        visualCheck: null,
        evidence: null,
        specSha256: '02d266cea1e4e168953c8fbae8bc940dbb85e4dd560d67536314897c4cb63c79',
        htmlSha256: '184e2e97d73247a7fd890bd9a532c54a686195ea614e6f45382bb5ceda0c0dbf',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'framework-runtime-architecture',
        title: 'ZX2200 框架运行时与控制语义',
        type: 'architecture',
        typeLabel: '架构图',
        group: 'architecture',
        groupLabel: '05 架构图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 7,
        relationCount: 6,
        spec: 'docs/archify/framework-runtime-architecture.archify.json',
        html: 'docs/archify/framework-runtime-architecture.html',
        visualCheck: null,
        evidence: null,
        specSha256: 'e6fe342fa7b71bd2466f4a9be2ecd4829753e67130aefdbd13269df0e7fd5995',
        htmlSha256: 'dd29daf1b02925f4c6885da8f55bb3dac854b5963086b67b0693fdf79f151ff5',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'zx2200-architecture',
        title: 'ZX2200 软件架构与运行边界',
        type: 'architecture',
        typeLabel: '架构图',
        group: 'architecture',
        groupLabel: '05 架构图',
        chapter: null,
        qualityProfile: 'showcase',
        nodeCount: 11,
        relationCount: 10,
        spec: 'docs/archify/zx2200-architecture.archify.json',
        html: 'docs/archify/zx2200-architecture.html',
        visualCheck: null,
        evidence: null,
        specSha256: '7842a55bf8accaf5b59678a91e2dba9201760cfcc1bd4d1fa507a20c5080d3b5',
        htmlSha256: 'ab14edb3efbfa5a6d509574eb9228225a30eb6f3cd25fe227b14f44799a9c287',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-visual-evidence-missing',
      },
      {
        id: 'showcase-v1',
        title: 'ZX2200 · 架构与流程展示版 V1',
        type: 'supplemental',
        typeLabel: 'HTML 补充页',
        group: 'supplemental',
        groupLabel: '06 HTML 补充页',
        chapter: null,
        qualityProfile: null,
        nodeCount: null,
        relationCount: null,
        spec: null,
        html: 'docs/archify/showcase-v1.html',
        visualCheck: null,
        evidence: null,
        specSha256: null,
        htmlSha256: '9f3212889da5edf2efedf39dc9d4af9826d262fd2f46a0f40c3674f746351962',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'supplemental-html-only',
      },
      {
        id: 'mapping-recovery-acceptance',
        title: 'ZX2200 恢复链路验收清单',
        type: 'supplemental',
        typeLabel: 'HTML 补充页',
        group: 'supplemental',
        groupLabel: '06 HTML 补充页',
        chapter: null,
        qualityProfile: null,
        nodeCount: null,
        relationCount: null,
        spec: null,
        html: 'docs/archify/mapping-recovery-acceptance.html',
        visualCheck: null,
        evidence: null,
        specSha256: null,
        htmlSha256: '86ca8ded89e4e4240c5f165a69b57d36f72db7f321034fa5f596d0e445e0b6ff',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'supplemental-html-only',
      },
      {
        id: 'config-production-gates',
        title: 'ZX2200 配置与生产门控源码',
        type: 'supplemental',
        typeLabel: 'HTML 补充页',
        group: 'supplemental',
        groupLabel: '06 HTML 补充页',
        chapter: null,
        qualityProfile: null,
        nodeCount: null,
        relationCount: null,
        spec: null,
        html: 'docs/archify/config-production-gates.html',
        visualCheck: null,
        evidence: null,
        specSha256: null,
        htmlSha256: '0cf3811d80a4a7f99fa4ec1248a89ed49729c9662923f2f47e46dff6971fba6f',
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'supplemental-html-only',
      },
      {
        id: 'wafer-vision-outcome-workflow',
        type: 'workflow',
        typeLabel: '工作流',
        group: 'workflow',
        groupLabel: '02 工作流专题',
        chapter: null,
        qualityProfile: 'showcase',
        visualCheck: null,
        evidence: null,
        visualCheckSha256: null,
        evidenceSha256: null,
        portalStatus: null,
        status: 'delivered-source-reviewed',
        title: 'ZX2200 供晶视觉：门控、报警与精度回退边界',
        nodeCount: 24,
        relationCount: 18,
        html: 'docs/archify/wafer-vision-outcome-workflow.html',
        spec: 'docs/archify/wafer-vision-outcome-workflow.archify.json',
        htmlSha256: 'a6440262e7bee87520e49f8dc91631c8ac5a2c5ad07a7bf4b222f7b2d6ee6496',
        specSha256: 'a3275844946ae5a9991f5fc5974b4dc0fa60055ceeb87dae3e90aaa5a71e1038',
      },
    ],
    validation: {
      duplicateIds: false,
      missingSpecFiles: [],
      missingHtmlFiles: [],
      brokenVisualFiles: [],
      brokenEvidenceFiles: [],
    },
  },
  diagramNotes: {
    'startup-workflow': [
      {
        title: '控制顺序与调用边界',
        items: [
          'Main 创建窗口，Load 由事件触发；生产启动来自按钮 ItemClick。',
          '初始化与开机回零均有配置条件；无条件箭头不代表底层成功。',
        ],
      },
      {
        title: '就绪检查有副作用',
        items: [
          '清理文件与信号复位发生在检查前；还会请求安全位置。',
          'Prepare false 只使 Start 返回，不能推断之前没有动作。',
        ],
      },
      {
        title: '完成与未完成范围',
        items: [
          '本章复核外层控制流，非驱动、所有自检或设备运行验收。',
          '100ms 是每轮调用之后休眠；Stop 返回不代表任务均退出。',
        ],
      },
    ],
    'transport-workflow': [
      {
        title: '并发与配置边界',
        items: [
          '图线是物料/信号主链，不是一个串行任务。',
          '上下料选择共用 LoadConfiguration；Belt 不等于联机收板。',
          'None、DryCycle 和已有物料复用按源码分支处理。',
        ],
      },
      {
        title: '软件成功不等于机械确认',
        items: [
          'Ignore 可能仍迁移状态、清对象或递增层号。',
          '各处 Retry 位置与 Exception 处理不同，不能合并成统一恢复。',
          '本图末端是局部交接，任务通常继续等待下一片。',
        ],
      },
    ],
    'dispense-workflow': [
      {
        title: '选择与重做',
        items: [
          '按配置排序；点胶 / 检测映射为 if / else if。',
          '空结果也可能是动作名未匹配；Retry 重取未完成项。',
          '检测可重置早期消息；Fail 也可禁用焊点后返回 Success。',
        ],
      },
      {
        title: '不可省略的边界',
        items: [
          '等料预点胶失败直接退出；禁用 S1 则绕过动作。',
          '分段 Wait、定位 bool 未检查；异常不保证 Stop。',
          '仅未 Stop 才放行；底层动作与现场结果未全部验收。',
        ],
      },
    ],
    'wafer-supply-workflow': [
      {
        title: '跨任务信号交接',
        items: [
          '晶圆就绪由直取等待者或 FlipTask 消费；不是同步函数调用。',
          'S2 接续不等于整机完成；连续生产由下一需求再次触发。',
        ],
      },
      {
        title: '恢复和退出边界',
        items: [
          '换片 false 按分支重试；空跑忽略初始化结果，Stop 不保证中断。',
          '异常先提示再 Stop；日志入队阻塞或失败可截断停止清理。',
          '窗口先改内存后保存；取消或提交失败没有本地回滚。',
        ],
      },
    ],
    'bonding-workflow': [
      {
        title: '编排和执行分开理解',
        items: [
          'Init 先按配置编排；图中类别只是已选动作的分组。',
          '每条消息单独执行或跳过；蘸胶插入顺序由翻转与 DipMode 决定。',
        ],
      },
      {
        title: '收尾不等于全部成功',
        items: [
          'Enable=false、内层 WaitStart=false 也可进入收尾。',
          'Finish 重置消息；无匹配动作也可返回 null；物理下料另由流道执行。',
        ],
      },
      {
        title: '胶盘独立并发',
        items: [
          '伸出→允许蘸胶→等蘸胶完成→缩回→等再次允许。',
          '区域等待超时可续等；部分 return 没有统一 finally。',
        ],
      },
    ],
    'pickup-workflow': [
      {
        title: '重检、重取、下一颗不同',
        items: [
          '重检只测真空；重取跳过定位和取前检查；下一颗重新等待定位。',
          'Ignore继续不能证明实际有料；Usable计数在检测前增加。',
        ],
      },
      {
        title: '返回不等于通知完成',
        items: [
          '灯光和供料通知均为未await任务，Success不保证通知已完成。',
          'OffLine直接返回；DryCycle独立模拟；同步异常与异步异常分开理解。',
        ],
      },
      {
        title: '采集生命周期待验证',
        items: [
          '正常停止采集调用被注释；循环共用标志且无直接Stop检查。',
          '已登记静态风险，未运行复现；不将疑点写成已证实故障。',
        ],
      },
    ],
    'bond-action-workflow': [
      {
        title: '重贴与重新取贴',
        items: ['Retry回ReBond，不重算位置或通知胶盘。', 'Cancel重置指定消息，返回Retry交调度。'],
      },
      {
        title: 'Success不是质量判定',
        items: ['胶印忽略可禁用焊点后仍返回Success。', '离线/空跑、提前返回及异常见源码复核。'],
      },
    ],
    'failure-recovery-workflow': [
      {
        title: '两种Retry不可混同',
        items: [
          '动作Retry重选消息；Alarm Retry直接重做当前动作。',
          'Ignore标调度完成，不代表动作质量合格。',
        ],
      },
      {
        title: '状态不是退出确认',
        items: [
          'Pause/Continue不统一挂起或重建任务。',
          '普通Stop和Abort方法都不能证明所有线程退出。',
        ],
      },
    ],
    'epoxy-template': [
      {
        title: '证据范围',
        items: [
          '来源：胶量检测.prc / ProcedureInfo.xml。10节点展示13模块；四种匹配合并，15条原始连接保留在证据清单。',
        ],
      },
      {
        title: '不等同现场执行',
        items: [
          '分支取值、脚本实现与SDK未运行验证；模板末端不等同设备完成。实际配方可覆盖默认模板。',
        ],
      },
    ],
    'safe-motion': [
      {
        title: '分支差异',
        items: ['二维低位：安全Z→XY→原Z', '三四维目标Z决定Z收尾', '四维水平动作传递T'],
      },
      {
        title: '失败语义',
        items: [
          'Z返回Abort/Fail仍可能调用XY或XYT',
          '异常中断，外层单步false直接返回',
          'XYT下层没有本地T限位判断',
        ],
      },
    ],
    'mapping-restore-workflow': [
      {
        title: '源码入口',
        items: [
          'TuService.cs:1953–2079 · codemap-read',
          'TransportUnit.cs:65–143 · tu-construct-init',
        ],
      },
      {
        title: '恢复边界',
        items: [
          '基板 / 模块阵列分支决定遍历；均非阵列时不处理网格',
          'X 递归禁用；其他码值复制到模块全部焊点',
        ],
      },
      {
        title: '构造与解析异常边界',
        items: [
          'ModifyMatter异常 → 清状态配置并Save；再次抛错可中断构造',
          '文件配方不切配置；无完整格式校验；解析catch已注释',
        ],
      },
    ],
    'stop-cleanup-workflow': [
      {
        title: '源码依据与溯源',
        items: [
          'Machine.Operate.cs:347–378；逐步解释见同目录 stop-cleanup-review.md。',
          'SetState:52–68；ClearMessageBox:42–55；EjectController:340–344。',
          '完整路径、源码链接与 SHA-256 快照：stop-cleanup-review.md / carrier-change-evidence.json。',
        ],
      },
      {
        title: '急停是另一条调用链',
        items: [
          'EmergencyStop:383–402：逐轴 StopMove → Stop → 三个 Abort 调用。',
          'Wafer / Bond Abort 当前为空；Dispense Abort 仅 Dispose。',
          '不能把方法名或调用完成当作全部任务已退出。',
        ],
      },
      {
        title: '异常与完成边界',
        items: [
          '本方法无统一 finally；前序异常可能阻止后续清理。',
          '没有直接关闭热吹；外围监控和驱动结果尚未验证。',
          '退出软件的 CloseAllHardware 不是普通 Stop 的步骤。',
        ],
      },
    ],
    'manual-epoxy-trial': [
      {
        title: '前置副作用与出胶参数',
        items: [
          'Confirm 先修改对象，再依次委托两次 Save。',
          '普通试胶按 DryCycle 传出胶参数；板上入口传 true。',
        ],
      },
      {
        title: '退出不等于重试或设备验收',
        items: [
          '定位/测高失败也提前返回；预点胶 DoWork 返回未检查。',
          '普通入口异常记录后重抛；板上入口无本地 catch。',
        ],
      },
      {
        title: '源码范围与溯源',
        items: [
          'UcEpoxyApplication.cs：483–546、595–922、968–1081。',
          '详见同目录 manual-epoxy-trial-summary.md；硬件未验收。',
        ],
      },
    ],
    'nozzle-exchange': [
      {
        title: '取放步骤与设备',
        items: [
          '吸嘴架伸出与焊头定位并行，随后等待到位',
          '取：Z下压→吸附→上抬→Y退出；放：Y送入→Z脱离',
        ],
      },
      {
        title: '不能混同的成功条件',
        items: [
          '人工Retry通常仅重新检测；有限自动重取才重走机械动作',
          '示教放回包装忽略PutbackNozzle的false，另查回原结果',
        ],
      },
      {
        title: '证据范围',
        items: [
          '主图聚焦自动编排；各门控提前返回和示教包装详见源码页',
          '仅源码与隔离控制流；运动、保存、真机尚未验收',
        ],
      },
    ],
    'calibration-task-workflow': [
      {
        title: '源码结论',
        items: [
          'CalibrateTask 暴露 StartDispenseCalibTask、StartBondCalibTask、StartUpLookCalibTask、StartWaferNPointCalibTask 等入口。',
          '点胶使用 3×3 点阵，Bond 使用 6×5 点阵；均通过 PR 图像点与物理点计算坐标转换。',
        ],
      },
      {
        title: '边界',
        items: [
          '异常通常弹窗后返回 false；源码未展示统一事务回滚。',
          '部分只标定相机的方法直接生成像素比、转换结果，保存行为依赖调用方。',
          '各 Start* 方法的 PR、测高或计算异常会弹窗并返回 false；失败出口在源码中存在，但不强行画成统一回滚分支。',
        ],
      },
    ],
    'calibration-execution-workflow': [
      {
        title: '源码与范围',
        items: [
          '入口 UcMainSystem.cs:1338；主调度 CalibrateTask.cs:2275。完整行号见标定主流程文档。',
          '同标记取消只跳过该步；各子任务false退出。错误边仅示代表路径。',
        ],
      },
      {
        title: '完成不等于验收',
        items: [
          '分阶段保存，无整体回滚；回零和部分居中bool未检查。',
          '源码顺序已复核；SDK、设备质量及其余标定入口仍待验证。',
        ],
      },
    ],
    'transport-pause-stop-workflow': [
      {
        title: '状态提交边界',
        items: [
          'Wait 已成功返回后才变为 Pause 或 Stop，方法没有再次检查状态，仍可执行气缸、皮带、材料转移和 Save。',
          'UnClamp 的 Abort 调用 Machine.Stop 后以 void 返回，父方法仍可能继续轴接口、转移材料并保存。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'transport-pause-review.md 与 transport-unclamp-stop-review.md。',
          '传感器、轴、I/O、保存、报警、配置、外层任务和设备均为限定替身。',
        ],
      },
    ],
    'postbond-feedback-workflow': [
      {
        title: '入口与数据',
        items: [
          '新菜单 → FrmPostBondData；Load 订阅、关闭退订。旧曲线窗口绑定未确认。',
          'StatisticsDomain.cs:407–422；DefectCompensate.cs:29–84；UcMainSystem.cs:1964–1967。',
          '窗口清空操作清整个缓存，不删除数据库或撤回已排队记录。',
        ],
      },
      {
        title: '取样与模式',
        items: [
          'BondActionNode.cs:125–150：离线/空跑先返回，不走此计算调用。',
          'DefectCompensate.cs:187–228：模式和开关决定取样；X/Y 各筛选绝对值 <50。',
          '缺名/数量不足返回默认点，筛选为空抛异常。数值进入 Provider.cs:521–527。',
        ],
      },
      {
        title: '失败与验收边界',
        items: [
          'BondActionNode.cs:366–376 → BondTask.cs:260–275：正常错误处理返回 Exception 后停止并请求回位。',
          '日志、弹窗、WorkStop 或停止过程再抛异常可能跳过后续清理；BondTask.cs:100–384 无外围捕获。',
          '完整定位：postbond-feedback-source-review.md；31段原文：postbond-feedback-evidence.json。未运行设备或WinForms。',
        ],
      },
    ],
    'bond-camera-calibration-workflow': [
      {
        title: '触发与证据',
        items: [
          'FrmStartup.cs:98–110 → CalibrateTask.cs:1817–2270。',
          '不是每片生产必经步骤；取消不启动任务。',
        ],
      },
      {
        title: '重复与保存',
        items: [
          '旋转最多三轮；后段偏移检查当前只执行一轮。',
          '坐标保存早于最后复核；结果取消不执行本地回滚。',
        ],
      },
      {
        title: '失败与溯源',
        items: [
          '异常边覆盖内层整个方法；false不阻止外层结果显示。',
          '详见 bond-camera-calibration-review.md；未做设备验收。',
        ],
      },
    ],
    'background-lifecycle-workflow': [
      {
        title: '可追溯范围',
        items: [
          '依据 auth-background / auth-form-close / auth-exit 等源码快照。',
          '详见 authorization-background-source-review.md；未实机验收。',
        ],
      },
      {
        title: '不能据此保证',
        items: [
          '后台每轮无总catch；100ms不是固定扫描周期。',
          '保存队列无显式排空；进程退出码0不等于保存成功。',
        ],
      },
    ],
    'wafer-selection-consistency-workflow': [
      {
        title: '一致性风险',
        items: [
          '适配器创建失败时 tempTablet 已被替换但网格可能尚未刷新；刷新失败时网格可能已绑定新数组。',
          'Save 不重新验证选择名称，空值或缺失名称事件后仍可能保存旧临时对象。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'wafer-selection-review.md。',
          '真实控件事件派发、反序列化、配置文件、设备 SDK 和现场恢复仍未验收。',
        ],
      },
    ],
    'emergency-stop-close-workflow': [
      {
        title: '异常截断',
        items: [
          '未完成的 S1 Task 调用 Dispose 可能抛异常，后续 S2 与供晶 Abort 不再调用。',
          'Machine.Stop 任一清理步骤抛异常都会中断剩余 Stop 清理；轴异常也可能让 Stop 和三个 Abort 都不执行。',
        ],
      },
      {
        title: '关闭语义',
        items: [
          'S2 AbortThread 为空、供晶 Abort 只有注释，Running 任务可继续存活。',
          'IsAllowTaskClosed 只拒绝 Running；未完成但尚未 Running 的 Task 仍可能放行关闭。证据：emergency-abort-review.md、machine-stop-signal-review.md、task-closure-review.md。',
        ],
      },
    ],
    'dispense-config-consumption-workflow': [
      {
        title: '时序范围',
        items: [
          '维护保存不是生产取值的必要前置；生产读取仓库内存，不在getter重新读磁盘。',
          'S2选择动作时缓存引用；动作先等待/预点胶，再取胶型参数。S2换嘴发生在读取胶型之后。',
        ],
      },
      {
        title: 'S1 / S2差异',
        items: [
          'S1 getter即时按步骤名称查仓库；S2选择动作时更新缓存，getter返回引用。',
          'S2步骤未匹配时没有else清旧引用；缺失胶型、并发修改仍待验证。',
        ],
      },
      {
        title: '分支与证据',
        items: [
          'S2 Printting检查并切换吸嘴；DryCycle只在本层改变isDrip，不保证全链无动作。',
          '完整证据：dispense-pattern-editor-source-review.md；失败不等于设备已安全停止。',
          '未成功返回码：Abort / Fail / Alarm / Exception；各分支含义见源码专题。',
        ],
      },
    ],
    'recipe-initialization-workflow': [
      {
        title: '错误不等于被阻止',
        items: [
          'BaseAlg.InitVmProcedure 捕获异常仅记录日志；上层仍可写成功日志并置标记。',
          'PR 名称清单未去重，固定含 IPTCenterCircle；LoadDispensePr 函数体只有注释。',
          '视觉 try 内逃逸的异常进入外抛出口；名称收集与其他语句也可能抛出。',
        ],
      },
      {
        title: '源码范围',
        items: [
          'UcMainSystem.Production.cs:124–203；BaseAlg.cs:291–351。',
          'LoadDispensePr:85–128 为空操作；完整锚点见 recipe-initialization-source-review.md。',
        ],
      },
    ],
    'recipe-lifecycle-workflow': [
      {
        title: '源码边界',
        items: [
          'ProductConfiguration 默认指向 RecipeDirPath/ProductConfiguration.json。',
          'ProcessDomain 保存 ProcessProgram.json，S1/S2 步骤在运行前展开为动作消息。',
        ],
      },
      {
        title: '检查规则',
        items: [
          '步骤名称、序号、焊点、功能互斥和胶压范围参与 CheckIsReady。',
          'Machine.DataSave 会集中保存多类设备、配方和运行配置。',
        ],
      },
    ],
    'permission-gating-workflow': [
      {
        title: '源码边界',
        items: [
          'MethodAopAttribute 的权限分支只处理第二个参数为 BarButtonItem 的事件。',
          '编辑窗口的主要 Start / Close / Reset / Save 是 SimpleButton，当前源码不能由类标注推导出角色拒绝。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'permission-gating-review.md。',
          '未验证 Fody 是否织入、登录数据源、权限配置持久化、真实 UI Enabled 状态或现场操作员路径。',
        ],
      },
    ],
    'task-closure-gate-workflow': [
      {
        title: '状态矩阵',
        items: [
          'Created、WaitingForActivation、WaitingToRun、WaitingForChildrenToComplete、RanToCompletion、Canceled、Faulted 都返回 true。',
          '只有 Running 返回 false；未完成但尚未 Running 的 Task 不会阻断关闭。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'task-closure-review.md。',
          '任务体、真实 UI 控件、状态持久化、现场调度和设备停稳仍未验收。',
        ],
      },
    ],
    'vision-motion-workflow': [
      {
        title: '可证实的编排',
        items: [
          'VisionService 查找 PREntity、调用 DoWork、返回 MatchResult，并在失败时返回 null。',
          'UpLook / SubstrateCorrection 决定动作是否实际执行，再调用控制器移动。',
        ],
      },
      {
        title: '算法边界',
        items: [
          'PR 算法和运动控制器由引用 DLL / 硬件服务提供；本仓库只证明调用、结果和补偿应用。',
          'VisionService 的图片写入 BlockingCollection，由后台线程保存 BMP。',
        ],
      },
    ],
    'maintenance-calibration-workflow': [
      {
        title: '实际边界',
        items: [
          'UcGuideMove 的点动覆盖点胶、Bond、晶圆、顶针、上下料仓和翻转轴。',
          '视觉报警窗口可暂停/停止，并支持灯光调整和模板保存。',
        ],
      },
      {
        title: '恢复条件',
        items: [
          'Continue 会检查门状态并设置 Working；源码没有证明它会重建已退出的全部线程。',
          '标定结果保存到对应配置对象或模板仓库，非统一事务。',
        ],
      },
    ],
    'wafer-search-gate-workflow': [
      {
        title: '停止窗口',
        items: [
          '请求变为 Stop 后，Nine 在 AnalyseDies 入口拦截；Single、Mapping、非静态 Box 可能先进入搜索或视觉接口，再由 StopSearch 抛出。',
          '搜索或分析过程中才变为 Stop 时，成功路径没有统一的返回后状态复查，仍可能发送取料许可。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'wafer-search-gates-review.md。',
          '视觉、几何、轴/气缸、真实 Machine.Stop、配置/DLL、UI、持久化与设备动作仍未验收。',
        ],
      },
    ],
    'exit-save-workflow': [
      {
        title: '退出码的边界',
        items: [
          'DataSave 首项失败后仍可弹窗并继续 Environment.Exit(0)。',
          '退出码 0 不能证明 Settings、配方或晶圆文件均已落盘。',
        ],
      },
      {
        title: '源码证据',
        items: [
          'MainForm_FormClosing → ExitSoftware → DataSave。',
          '正常保存与首个晶圆文件占用两条路径来自 native-mainform-close-save-review.md。',
        ],
      },
    ],
    'relative-bond-order-workflow': [
      {
        title: '真实顺序',
        items: [
          'S2ActionNodeController.Init() 在动作排序、异形载具过滤和禁用动作移除后调用 SortRelativeBond()。',
          '相对贴片视觉步骤被移到对应 PickActionNode 之前。',
        ],
      },
      {
        title: '静态边界',
        items: [
          '没有启用步骤时仍会加入查找结果，后续读取 ProcessStepName 没有空值保护。',
          '没有 PickActionNode 时原视觉消息已删除，没有备用插入路径。',
        ],
      },
    ],
    'recipe-live-reload-workflow': [
      {
        title: '关键边界',
        items: [
          '重载帮助方法不会停止或替换五个正在等待的输送 Task。',
          '同一 RecipeID 也会替换六类单例，但任务缓存可能仍指向首次 A。',
        ],
      },
      {
        title: '源码证据',
        items: [
          'native-recipe-live-reload-review.md：两轮各 93 项检查。',
          '晶圆 Save 失败时前四个单例可能已提交，释放锁后重试才恢复一致。',
        ],
      },
    ],
    'wafer-change-retry-workflow': [
      {
        title: '重试边界',
        items: [
          '源码没有统一的总次数、退避或 Stop 检查；循环终点依赖子方法返回、异常、交互或内部检查。',
          '入口已是 Stop 仍可进入初始化，不能把外层状态当作自动取消凭据。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'wafer-change-retry-review.md。',
          '真实窗口、深拷贝、传感器、气缸、轴、真空、SDK 和完整停止安全性仍未验收。',
        ],
      },
    ],
    'automation-workflow': [
      {
        title: 'Recipe and hardware',
        items: [
          'Input: Settings JSON, PR templates, carrier + chips (E18).',
          'DispenseWorkTask: retry unfinished action; otherwise stop on failure (E08).',
          'BondTask: recipe-selected pick / correction / bond / inspect (E10–15).',
        ],
      },
      {
        title: 'Concurrent, continuous production',
        items: [
          'Arrows show carrier dependencies; workers overlap (E05).',
          'Per-carrier completion returns to waiting. Pause / Stop apply across workers.',
        ],
      },
      {
        title: 'Local source evidence',
        items: [
          'E01–E20: automation-workflow-summary.md lists files and lines.',
          'BondTask.cs:214–347 · DispenseWorkTask.cs:117–181.',
          'S1 is conditional; wafer supply may pass through FlipTask (E14).',
        ],
      },
    ],
    'machine-start-readiness-workflow': [
      {
        title: '失败传播边界',
        items: [
          'Transport.StartTask 捕获异常或预检失败后可调用 Machine.Stop 并返回；Machine.Start 没有读取成功值，仍会继续后续 Wafer.Start。',
          'Dispense、Bond、刮胶盘和翻转台的 bool 返回值当前调用方没有统一消费，也没有统一 try/finally。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'machine-start-readiness-review.md 与 production-start-callchain-review.md。',
          '本图表达源码调用顺序，不证明真实配置、自检、运动、VM、UI、SQL 或设备任务健康。',
        ],
      },
    ],
    's1-step-commit-gate-workflow': [
      {
        title: '状态分离',
        items: [
          '步骤字典先被置为 true，但当前第 13 条消息仍未完成；GetNext 仍可返回该节点，而 IsDoWork 已因步骤标记拒绝重做。',
          'Abort/Fail 都没有取得插补坐标、执行物理点胶或发送传料信号。',
        ],
      },
      {
        title: '等待与故障',
        items: [
          'WaitSingleStep 不直接读取 MachineState；已有等待要靠 IsSingleStepWork=false 才返回。',
          'finally 刷新委托为 null 或抛异常时，动作返回值被异常覆盖，Task 可 Faulted。',
        ],
      },
      {
        title: '关闭查询边界',
        items: [
          'IsAllowTaskClosed 只汇总任务是否仍活跃，不读取 Task.Exception、Wait 或业务完成状态。',
          'native-s1-step-commit-review.md；真实 UI、在线轴、SQL、完整构建和设备闭环仍未验收。',
        ],
      },
    ],
    's1-return-gates-workflow': [
      {
        title: '返回边界',
        items: [
          '实际 Abort/Fail 都在离线步骤先提交后发生；当前消息仍可能 pending，FinishCurrent 与 BondRelease 尚未执行。',
          'Retry 只在外层静态分支可见，本轮没有把未运行的 ReDispense→Retry 当作实际结果。',
        ],
      },
      {
        title: '异常边界',
        items: [
          'finally 中刷新委托没有 null 检查；自然 null 或明确 throw 会让原 Task Faulted，catch 不会吞掉该异常。',
          'Machine.Stop 能清除单步标志，但不代表所有等待都能被同样方式释放。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'native-s1-return-gates-review.md；与 S1 胶检结果专题分开登记。',
          '相机、轴、在线 IO、真实预点胶配置、完整工程构建和设备闭环仍未验收。',
        ],
      },
    ],
    's1-segment-interaction-workflow': [
      {
        title: 'Stop 与 Pause 的区别',
        items: [
          '进入已有 done.Wait 后，Pause 本身不会打断等待；随后 Stop 才让 Wait 返回 false。',
          '等待返回值在原 InteractiveAction 中被丢弃，Stop 用例仍观察到动作 Success，不能等同业务成功。',
        ],
      },
      {
        title: '异常边界',
        items: [
          '完成事件已消费后，finally 的 WorkStop 回调若抛异常，真实 Task 变为 Faulted，当前交互未完成。',
          '测试回调只用于同步和注入，不等同真实 UI、输送或硬件故障。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'native-s1-segment-interaction-review.md；22 条调度消息和原 Wait/Finish/Stop 逻辑已绑定。',
          '未执行物理输送、在线视觉/测高/点胶、S2、SQL、完整构建和设备运行。',
        ],
      },
    ],
    's1-defect-outcome-workflow': [
      {
        title: '结果边界',
        items: [
          'WithReferenceSearch=1 和非法模式 999 实际都绕过视觉处理并返回 Success；不代表胶检通过。',
          'PostBondEpoxyCheck 的 Retry 可单独返回，但完整生产 Task 的 ReDispense→Retry 循环本轮未运行。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'native-s1-defect-outcomes-review.md 与 native-s1-return-gates-review.md。',
          '相机、轴、VM、真实弹窗选择、SQL、在线设备和完整工程构建仍未验收。',
        ],
      },
    ],
    's1-rework-context-workflow': [
      {
        title: '结果边界',
        items: [
          'null / 空列表可映射为 Success、Fail、Abort 或 Retry；这不是实际视觉质量判定。',
          'Retry 的完整生产任务循环没有在本轮运行，不能把静态调用关系当作已验收的补胶成功。',
        ],
      },
      {
        title: '重做故障',
        items: [
          'ReDispense 在 foreach(Keys) 中修改 Dictionary，第一次写入后下一次枚举抛 InvalidOperationException。',
          '单独 SetActionNodeReWork 可部分提交消息后再因缺少动作配对抛 Sort Error；两条结果不能合成一条生产链。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'native-s1-rework-context-review.md；真实 PR、receiver 与原 CLR 行为均保留。',
          '相机 VM、真实报警 UI、物理补胶、在线硬件、SQL、完整构建和设备闭环仍未验收。',
        ],
      },
    ],
    's1-stop-rework-recovery-workflow': [
      {
        title: '状态边界',
        items: [
          'SetActionNodeReWork 只重置匹配消息，不回滚业务步骤字典；ProductFinish 也不清步骤完成值。',
          '重启可在没有新业务 DoWork 的情况下直接发送 S1→S2 放行信号。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'native-s1-stop-recovery-review.md。',
          '重置后的检测 Retry、完整在线点胶、UI/SQL、设备和原工程构建仍未验收。',
        ],
      },
    ],
    's1-task-loop-pause-workflow': [
      {
        title: '关键窗口',
        items: [
          'WaitStart 在 Pause 变 Stop 后没有二次检查 Stop，可能让一个动作在 Stop 状态下继续。',
          '任务回调异常会让 Task Faulted，源码没有在该路径自动调用 Machine.Stop。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'native-s1-working-pause-review.md 与 native-s1-task-loop-review.md。',
          '图中身份和测高使用离线夹具，不代表在线点胶、检测、轴运动或真实设备验收。',
        ],
      },
    ],
    'process-step-injection-workflow': [
      {
        title: '注入位置',
        items: [
          'TransportUnit 构造与两个 Mapping 读取入口同时注入 S1/S2。',
          'DispenseWorkTask 在动作循环前注入 S1；BondTask 在补偿、来料与安全位处理后注入 S2。',
        ],
      },
      {
        title: '边界',
        items: [
          '重复注入不会覆盖已有完成值，因此旧键可能跨载具或配方切换保留。',
          '源码已确认控制流；真实 Mapping、配方、任务和设备仍未验收。',
        ],
      },
    ],
    's2-action-boundary-workflow': [
      {
        title: '步骤提交边界',
        items: [
          'AfterBond 在刷新前提交 S2FinishedStep；刷新失败不会回滚该步骤。',
          'Pick 的 Success 不提交当前消息，公开 FinishCurrent 需要另行调用。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'native-s2-action-boundaries-review.md。',
          '本图未启动完整 BondTask，不证明真实轴、相机、贴片、Retry、UI、SQL 或设备成功。',
        ],
      },
    ],
    's2-reset-retry-workflow': [
      {
        title: '真实边界',
        items: [
          'BondTask.DoWork 没有本地异常处理器，清零返回 bool 在调用点未被判断。',
          'Retry 递归没有源码次数上限；Modbus 首次异常后只等待 50ms 再写一次。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'original-s2-reset-il-review.md 与 s2-reset-normal-review.md。',
          '当前图只表达源码控制流，不证明 Modbus、IO、轴、UI 或设备成功。',
        ],
      },
    ],
    's2-task-entry-boundary-workflow': [
      {
        title: '真实边界',
        items: [
          '5 种模式、6 种状态、2 种 Enable 与 ToolBank 组合中，Stop 入口可正常结束，其余在首步空 SDK 轴查找处故障。',
          'AbortThread 为空方法：调用返回成功，但暂停中的任务仍 Running，未取消或释放。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'native-s2-task-entry-review.md 与 native-s2-action-boundaries-review.md。',
          '未执行真实轴、换吸嘴、取片/贴片、视觉、Retry、UI、SQL、部署或设备验收。',
        ],
      },
    ],
    'statistics-log-producer-workflow': [
      {
        title: '并发与失败边界',
        items: [
          '队列满时 SDK Trace 已广播，但 Add 尚未返回，lastMessage 尚未更新。',
          '两个并发调用可以同时通过旧值门控并各自 Post，形成重复实体；Add 失败时新消息仍可能重复广播。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'native-statistics-producer-review.md。',
          '真实数据库消费者、SQL 写入、Fody 自动织入和生产 UI 异常路径未验收。',
        ],
      },
    ],
    'transport-start-gating-workflow': [
      {
        title: '返回码边界',
        items: [
          'Abort 在九条任务中都会调用 Stop；Exception 只有部分任务映射到 Stop。',
          '控制器返回后外层没有再次检查 Stop，Success 信号可能在 Stop 之后发布。',
        ],
      },
      {
        title: '证据范围',
        items: [
          'transport-producer-review.md 与 outer-transport-task-review.md。',
          '控制器、配置、视觉、持久化和设备均为限定替身，图不代表现场机械验收。',
        ],
      },
    ],
    'wafer-pick-handshake-sequence': [],
    'bin-configuration-sequence': [],
    'bin-failure-handshake-sequence': [
      {
        title: '源码范围',
        items: [
          '四信号：AllowMove 为 AutoReset；AllowPush 为 ManualReset',
          '上下料动作不同；两段是条件场景，不是一条必然连续实机记录',
          '源码与行号：bin-failure-handshake-recovery-review.md',
        ],
      },
      {
        title: '异常边界',
        items: [
          '料仓 catch 仅提示；没有显式 Stop 或补发信号',
          '生产者退出 + 未 Set + 设备仍 Working：等待无整体期限',
          'NoStart 保留允许推料信号，延时后重试',
        ],
      },
      {
        title: '恢复限制',
        items: [
          'Stop 供等待循环观察；没有 join 全部任务',
          'Continue 仅改变状态，不重建已退出任务',
          '重新 Start 先复位信号，再检查是否仍有 Running 任务',
        ],
      },
    ],
    'recipe-switch-sequence': [],
    's2-predispense-retry': [
      {
        title: '重试有条件',
        items: ['Retry回同一节点；Ignore结束节点；Abort停止。再次触发才重新分配，索引不回滚。'],
      },
      {
        title: '检测返回与停机副作用',
        items: ['检测返回值未判断，但终止按钮先调用Stop；检测抛异常另走上层错误路径。'],
      },
    ],
    'background-task-sequence': [],
    'motion-arrival-sequence': [],
    'automation-sequence': [
      {
        title: 'Selected execution path',
        items: [
          'Normal transport + first direct wafer-camera pickup; no flip.',
          'Concurrent tasks are synchronized by events, not timed RPCs.',
        ],
      },
      {
        title: 'Read with the source summary',
        items: [
          'E09–E15 map every interaction to local files and line ranges.',
          'Repeated action calls are condensed; retries remain in the workflow.',
        ],
      },
    ],
    'async-persistence-dataflow': [
      {
        title: '温补分派缺口',
        items: [
          '两处 TemperatureCompensationEntity 经 object 包装入队',
          '消费方法没有该类型及默认 Insert 分支',
        ],
      },
      {
        title: '失败与退出边界',
        items: ['两个消费循环无局部重试/异常处理', 'ExitSoftware 没有显式排空或 Join'],
      },
    ],
    'runtime-dataflow': [
      {
        title: '源码事实',
        items: [
          'StatisticsService 的实体队列容量为 500；后台线程按实体类型调用 DBService.Insert。',
          'VisionService 的图片队列由独立线程写 BMP，图片保存不作为动作成功的提交屏障。',
        ],
      },
      {
        title: '一致性边界',
        items: [
          'Machine.DataSave 依次保存多类 Singleton 配置，catch 只记录并弹窗，没有跨文件事务。',
          '部分统计 SQL 直接查询数据库；源码不证明存在消息队列或自动回滚。',
        ],
      },
    ],
    'framework-runtime-architecture': [
      {
        title: '可证实语义',
        items: [
          'Signal.Wait 先处理 Stop/Pause，再等待 EventWaitHandle；AutoReset 消费后回到 ReSet。',
          'WaitSingleStep 只在 IsSingleStepWork 为 true 时等待。',
          'WaitSingleStep 仅在单步模式开启时消费信号；该语义保留在源码说明中。',
        ],
      },
      {
        title: '边界与限制',
        items: [
          'RuntimeProvider.ThreadFlag 是全局 volatile 退出标志；各线程是否检查它取决于线程实现。',
          'MachineService.cs 当前为空类，不能推断它提供额外调度能力。',
        ],
      },
    ],
    'zx2200-architecture': [
      {
        title: '源码结论',
        items: [
          'ZX2200 是 WinForms 主应用，Machine 负责生命周期，多个生产域并发运行。',
          'ProcessDomain 生成动作消息；SignalPool 是进程内交接机制。',
        ],
      },
      {
        title: '边界',
        items: [
          '硬件 DLL、VisionMaster、Modbus 和外部驱动内部未在本仓库源码中展开。',
          '配置决定 S1、翻转、胶盘和输送分支是否参与。',
        ],
      },
    ],
    'showcase-v1': [],
    'mapping-recovery-acceptance': [],
    'config-production-gates': [],
  },
  diagramRecords: {
    'startup-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/startup-semantic-revalidation.md'],
      visualAvailable: true,
    },
    'transport-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/transport-semantic-revalidation.md'],
      visualAvailable: true,
    },
    'dispense-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/dispense-semantic-revalidation.md'],
      visualAvailable: true,
    },
    'wafer-supply-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/wafer-supply-semantic-revalidation.md'],
      visualAvailable: true,
    },
    'bonding-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/bonding-semantic-revalidation.md'],
      visualAvailable: true,
    },
    'pickup-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/pickup-semantic-revalidation.md'],
      visualAvailable: true,
    },
    'bond-action-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/bond-action-semantic-revalidation.md'],
      visualAvailable: true,
    },
    'failure-recovery-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/failure-recovery-semantic-revalidation.md'],
      visualAvailable: true,
    },
    'epoxy-template': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'safe-motion': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'mapping-restore-workflow': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'stop-cleanup-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/stop-cleanup-review.md'],
      visualAvailable: true,
    },
    'manual-epoxy-trial': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/manual-epoxy-trial-summary.md'],
      visualAvailable: true,
    },
    'nozzle-exchange': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'calibration-task-workflow': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'calibration-execution-workflow': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'transport-pause-stop-workflow': {
      htmlAvailable: true,
      reviewDocuments: [
        'docs/archify/transport-pause-review.md',
        'docs/archify/transport-unclamp-stop-review.md',
      ],
      visualAvailable: false,
    },
    'postbond-feedback-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/postbond-feedback-source-review.md'],
      visualAvailable: true,
    },
    'bond-camera-calibration-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/bond-camera-calibration-review.md'],
      visualAvailable: true,
    },
    'background-lifecycle-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/authorization-background-source-review.md'],
      visualAvailable: true,
    },
    'wafer-selection-consistency-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/wafer-selection-review.md'],
      visualAvailable: false,
    },
    'emergency-stop-close-workflow': {
      htmlAvailable: true,
      reviewDocuments: [
        'docs/archify/emergency-abort-review.md',
        'docs/archify/machine-stop-signal-review.md',
        'docs/archify/task-closure-review.md',
      ],
      visualAvailable: false,
    },
    'dispense-config-consumption-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/dispense-pattern-editor-source-review.md'],
      visualAvailable: true,
    },
    'recipe-initialization-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/recipe-initialization-source-review.md'],
      visualAvailable: false,
    },
    'recipe-lifecycle-workflow': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'permission-gating-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/permission-gating-review.md'],
      visualAvailable: false,
    },
    'task-closure-gate-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/task-closure-review.md'],
      visualAvailable: false,
    },
    'vision-motion-workflow': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'maintenance-calibration-workflow': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'wafer-search-gate-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/wafer-search-gates-review.md'],
      visualAvailable: false,
    },
    'exit-save-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/native-mainform-close-save-review.md'],
      visualAvailable: false,
    },
    'relative-bond-order-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/relative-bond-order-review.md'],
      visualAvailable: false,
    },
    'recipe-live-reload-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/native-recipe-live-reload-review.md'],
      visualAvailable: false,
    },
    'wafer-change-retry-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/wafer-change-retry-review.md'],
      visualAvailable: false,
    },
    'automation-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/automation-workflow-summary.md'],
      visualAvailable: false,
    },
    'machine-start-readiness-workflow': {
      htmlAvailable: true,
      reviewDocuments: [
        'docs/archify/machine-start-readiness-review.md',
        'docs/archify/production-start-callchain-review.md',
      ],
      visualAvailable: false,
    },
    's1-step-commit-gate-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/native-s1-step-commit-review.md'],
      visualAvailable: false,
    },
    's1-return-gates-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/native-s1-return-gates-review.md'],
      visualAvailable: false,
    },
    's1-segment-interaction-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/native-s1-segment-interaction-review.md'],
      visualAvailable: false,
    },
    's1-defect-outcome-workflow': {
      htmlAvailable: true,
      reviewDocuments: [
        'docs/archify/native-s1-defect-outcomes-review.md',
        'docs/archify/native-s1-return-gates-review.md',
      ],
      visualAvailable: false,
    },
    's1-rework-context-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/native-s1-rework-context-review.md'],
      visualAvailable: false,
    },
    's1-stop-rework-recovery-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/native-s1-stop-recovery-review.md'],
      visualAvailable: false,
    },
    's1-task-loop-pause-workflow': {
      htmlAvailable: true,
      reviewDocuments: [
        'docs/archify/native-s1-working-pause-review.md',
        'docs/archify/native-s1-task-loop-review.md',
      ],
      visualAvailable: false,
    },
    'process-step-injection-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/process-step-injection-review.md'],
      visualAvailable: false,
    },
    's2-action-boundary-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/native-s2-action-boundaries-review.md'],
      visualAvailable: false,
    },
    's2-reset-retry-workflow': {
      htmlAvailable: true,
      reviewDocuments: [
        'docs/archify/original-s2-reset-il-review.md',
        'docs/archify/s2-reset-normal-review.md',
      ],
      visualAvailable: false,
    },
    's2-task-entry-boundary-workflow': {
      htmlAvailable: true,
      reviewDocuments: [
        'docs/archify/native-s2-task-entry-review.md',
        'docs/archify/native-s2-action-boundaries-review.md',
      ],
      visualAvailable: false,
    },
    'statistics-log-producer-workflow': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/native-statistics-producer-review.md'],
      visualAvailable: false,
    },
    'transport-start-gating-workflow': {
      htmlAvailable: true,
      reviewDocuments: [
        'docs/archify/transport-producer-review.md',
        'docs/archify/outer-transport-task-review.md',
      ],
      visualAvailable: false,
    },
    'wafer-pick-handshake-sequence': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'bin-configuration-sequence': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'bin-failure-handshake-sequence': {
      htmlAvailable: true,
      reviewDocuments: ['docs/archify/bin-failure-handshake-recovery-review.md'],
      visualAvailable: true,
    },
    'recipe-switch-sequence': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    's2-predispense-retry': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'background-task-sequence': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'motion-arrival-sequence': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'automation-sequence': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'async-persistence-dataflow': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: true,
    },
    'runtime-dataflow': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'framework-runtime-architecture': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'zx2200-architecture': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'showcase-v1': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'mapping-recovery-acceptance': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'config-production-gates': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
    'wafer-vision-outcome-workflow': {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
  },
};
