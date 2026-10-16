import { flow, outcome, step } from './builders.ts';

export const s1WorkerFlows = [
  flow(
    's1-input-and-task',
    '启动与等待来料',
    'Start 创建长期运行任务；DoWork 先初始化消息，再进入等料循环。OffLineWork 跳过来料等待，Enable 决定是否执行载具注入与动作循环。',
    ['s1-worker-start', 's1-worker-entry', 's1-worker-product'],
    [
      step(
        'create',
        '创建线程与一次初始化',
        '任务为空或 Status 不等于 Running 时用 StartNew 创建；使用 CancellationToken.None。Start 随后返回 true，不等待生产结束。DoWork 的 Init 位于外层 while 之前，每轮不会重新排序。',
        ['s1-worker-start', 's1-worker-entry'],
      ),
      step(
        'input',
        '每轮调用安全位与等料',
        '每轮 WaitStart 后先调用 MoveToSafePos；非 OffLineWork 进入 GetInputSignal。该方法每次睡眠 10 毫秒，暂停时跳过本轮，随后调用预点胶，再检查停止、暂停和来料状态。',
        ['s1-worker-entry', 's1-input-loop', 'tr-signal-start'],
        [
          outcome(
            '预点胶非 Success 或停止',
            'GetInputSignal 返回 false，线程再调用 MoveToSafePos 后直接 return；这个退出分支自身没有调用 Stop。该来料循环也没有整体超时。',
            's1-input-loop',
            's1-worker-entry',
          ),
        ],
      ),
      step(
        'consume',
        '读取来料信号状态',
        'TransferToDispense1FinishedSignal.State 为 Set 时，直接写 State=ReSet 并返回 true；ReSet 时继续等待，其他值抛异常。这里没有调用 Wait 或 ReSetEvent，不能与事件对象的消费混为一谈。',
        ['s1-input-loop'],
        [
          outcome(
            '异常传播',
            'DoWork 没有在这个等料调用外包 catch；Init、GetInputSignal 或后续选动作抛出的异常不会统一进入动作返回码的 Stop 分支。',
            's1-worker-entry',
            's1-worker-select',
            's1-worker-results',
          ),
        ],
      ),
      step(
        'product',
        '启用时准备载具与步骤',
        '收到来料后先置 IsFirstDispense=true。Enable 为 true 才访问载具：IsProduct=false 时新建 System1 载具并置 true，随后 InjectSteps、CalculateDispenseCycle，进入动作循环。',
        ['s1-worker-product', 's1-inject'],
        [
          outcome(
            'Enable=false',
            '绕过载具注入和动作循环，仍走尾部安全位、非 Stop 放行和消息复位；因此放行并不证明本轮执行过点胶。',
            's1-worker-product',
            's1-worker-select',
            's1-worker-release',
          ),
        ],
      ),
    ],
  ),
  flow(
    's1-action-selection',
    '动作选择与返回分支',
    '线程每轮从头找第一条未完成消息。跳过执行、Retry、Success 与其他返回码分别影响消息标记和退出路径。',
    ['s1-next-message', 's1-worker-select', 's1-worker-results'],
    [
      step(
        'next',
        '取第一条未完成消息',
        'GetNextActionNode 先清当前消息，再按 WorkMessages 顺序找 Finished=false，按动作名在注册集合中 Find。消息全部完成返回 null；第一条未完成消息的动作名未匹配时同样返回 null，线程都直接退出内层循环。',
        ['s1-next-message', 's1-worker-select'],
      ),
      step(
        'gate',
        '决定执行还是跳过',
        'IsDoWork=false 直接跳到 FinishCurrentActionNode，标记消息完成。点胶与检测动作遇到禁用焊点、仅 S2 启用或当前步骤已完成均返回 false；当前焊点为空则抛异常。',
        ['s1-worker-select', 's1-point-gate', 's1-defect-gate', 's1-point-needs'],
      ),
      step(
        'execute',
        '调用动作与处理返回码',
        '非四种指定测高动作且非 OffLineWork 时先调用收回测高气缸，再 DoWork。Retry 继续循环，未标当前消息完成；Success 才走 Finish。其他返回码先调用安全位，再 Stop 并退出线程。',
        ['s1-worker-select', 's1-worker-results', 's1-reset-messages'],
        [
          outcome(
            'Retry 的下一项',
            'continue 后重新从头找未完成消息；返工若清除了更早的 Finished 标记，下一项可以变成更早的动作，不能笼统写成原地重试同一节点。',
            's1-worker-results',
            's1-next-message',
            's1-rework-messages',
          ),
        ],
      ),
      step(
        'release',
        '安全位、条件放行、消息复位',
        '离开内层循环后调用 MoveToSafePos；仅 IsStop=false 发 AllowDispenseTransferToBondSignal。之后才调用 Finish，把消息 Finished 全部改为 false 并清当前消息，未清焊点步骤字典。',
        ['s1-worker-release', 's1-reset-messages'],
        [
          outcome(
            '日志不是完成判据',
            '“点胶工作完成”日志在 IsStop 条件之外。停止导致内层 WaitStart 退出时，也可能到达日志和消息复位，却不发布放行信号。',
            's1-worker-select',
            's1-worker-release',
            'tr-signal-start',
          ),
        ],
      ),
    ],
  ),
];
