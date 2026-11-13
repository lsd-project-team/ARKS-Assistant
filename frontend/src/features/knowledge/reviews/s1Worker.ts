import { flow, outcome, step } from './builders.ts';

export const s1WorkerFlows = [
  flow(
    's1-input-and-task',
    '启动与等待来料',
    '启动时创建一个长期运行的生产任务；任务主体先初始化消息，再进入等料循环。离线生产会跳过来料等待，是否启用则决定要不要执行载具注入和动作循环。',
    ['s1-worker-start', 's1-worker-entry', 's1-worker-product'],
    [
      step(
        'create',
        '创建线程与一次初始化',
        '任务为空或状态不是运行中时新建任务，这次创建不带取消条件。启动随后返回成功，不等待生产结束。初始化放在外层循环之前，每轮不会重新排序。',
        ['s1-worker-start', 's1-worker-entry'],
      ),
      step(
        'input',
        '每轮调用安全位与等料',
        '每轮等待启动或停止指令后先回安全位；非离线生产进入等料检查。等料检查每次休眠 10 毫秒，暂停时跳过本轮，随后触发预点胶，再检查停止、暂停和来料状态。',
        ['s1-worker-entry', 's1-input-loop', 'tr-signal-start'],
        [
          outcome(
            '预点胶不成功或需要停止',
            '等料检查返回不通过时，线程先回安全位再直接退出；这个退出分支自身没有触发停机。来料循环也没有整体超时。',
            's1-input-loop',
            's1-worker-entry',
          ),
        ],
      ),
      step(
        'consume',
        '读取来料信号状态',
        '来料信号处于置位状态时，直接把它复位并返回收到来料；处于复位状态就继续等待，其他状态报告异常。这里没有发起等待，也没有走事件复位，不能和事件信号的消费混为一谈。',
        ['s1-input-loop'],
        [
          outcome(
            '异常传播',
            '等料检查外层没有异常保护；初始化、等料或后续选动作抛出的异常，不会统一进入动作结果的停机分支。',
            's1-worker-entry',
            's1-worker-select',
            's1-worker-results',
          ),
        ],
      ),
      step(
        'product',
        '启用时准备载具与步骤',
        '收到来料后先把首点标记置为有效。启用时才访问载具：还没有生产载具时，新建 S1 载具并记录下来，随后注入焊点步骤、计算点胶周期，进入动作循环。',
        ['s1-worker-product', 's1-inject'],
        [
          outcome(
            '未启用时',
            '未启用会绕过载具注入和动作循环，仍走尾部回安全位、条件放行和消息复位；因此放行并不证明这一轮执行过点胶。',
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
    '线程每轮都从头找第一条未完成的消息。跳过执行、重试、成功以及其他结果，分别影响消息标记和退出路径。',
    ['s1-next-message', 's1-worker-select', 's1-worker-results'],
    [
      step(
        'next',
        '取第一条未完成消息',
        '取下一动作时先清空当前消息，再按消息顺序找未完成项，并按动作名在已注册的动作里查找。消息全部完成时返回空；第一条未完成消息的动作名匹配不上时同样返回空，线程都直接退出内层循环。',
        ['s1-next-message', 's1-worker-select'],
      ),
      step(
        'gate',
        '决定执行还是跳过',
        '不需要执行时直接跳到标记完成，把消息记为已完成。点胶和检测动作遇到焊点被禁用、只在 S2 启用或当前步骤已完成，都返回不需要执行；当前焊点为空则报告异常。',
        ['s1-worker-select', 's1-point-gate', 's1-defect-gate', 's1-point-needs'],
      ),
      step(
        'execute',
        '调用动作与处理返回码',
        '不是四种指定测高动作、也不是离线生产时，先收回测高气缸，再执行动作。重试会继续循环，不把当前消息标为完成；成功才走标记完成。其他结果先回安全位，再停机并退出线程。',
        ['s1-worker-select', 's1-worker-results', 's1-reset-messages'],
        [
          outcome(
            '重试后的下一项',
            '继续下一轮后会重新从头找未完成消息；如果返工清掉了更早的完成标记，下一项可能变成更早的动作，不能笼统写成原地重试同一动作。',
            's1-worker-results',
            's1-next-message',
            's1-rework-messages',
          ),
        ],
      ),
      step(
        'release',
        '安全位、条件放行、消息复位',
        '离开内层循环后先回安全位；只有未收到停止时，才发出允许向下游输送的信号。之后才做结束收尾，把消息的完成标记全部清掉并清空当前消息，但不清焊点步骤记录。',
        ['s1-worker-release', 's1-reset-messages'],
        [
          outcome(
            '日志不是完成判据',
            '“点胶工作完成”这条日志不在停止条件之内。停止导致内层等待退出时，也可能走到日志和消息复位，却没有发出放行信号。',
            's1-worker-select',
            's1-worker-release',
            'tr-signal-start',
          ),
        ],
      ),
    ],
  ),
];
