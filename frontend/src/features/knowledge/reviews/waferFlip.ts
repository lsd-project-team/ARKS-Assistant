import { choices, flow, outcome, step } from './builders.ts';

export const waferFlipFlows = [
  flow(
    'wafer-flip-task',
    '翻转线程与焊头交接',
    '翻转线程先等供晶许可，执行翻转动作，再通知焊头可以取料并等待取料完成。动作返回与线程回零并不是统一的收尾。',
    ['w-flip-worker-entry', 'w-flip-worker-results'],
    [
      step(
        'start',
        '线程创建与本轮芯片',
        '启动时若任务为空或不在运行中，就把状态切到工作状态，并创建一个不带取消条件的长期任务；启动本身随即返回成功，并不等待任务结束。任务主体先把翻转台回零，再等待启动指令；没有所需芯片时延时 100 毫秒进入下一轮。',
        ['w-flip-start', 'w-flip-worker-entry'],
      ),
      step(
        'wait',
        '需要翻转且工具未持晶才等供晶',
        '启用翻转台、且软件持晶标记为否时，才进入下一颗搜索并等待供晶许可；许可未到就直接结束本轮。已有持晶标记时，会跳过供晶等待和本次翻转动作。',
        ['w-flip-worker-entry'],
      ),
      step(
        'results',
        '成功、未启动与退出结果',
        '空跑时走空跑翻转动作，其余情况走普通翻转入口。动作成功才置软件持晶标记；结果为未启动时回到下一颗搜索，不重新获取本轮芯片。异常和中止会先对晶圆料片请求退料，再结束本轮；其他未列出的结果不会置持晶标记，但仍可能继续走到发布许可。',
        ['w-flip-worker-results'],
      ),
      step(
        'handoff',
        '发布后等待固晶取片成功',
        '发出翻转可取料许可后，等待焊头取料完成信号；信号未到就直接结束本轮。翻转台回零只在循环正常退出后执行，提前结束和未捕获的异常都不保证经过这一步；这里没有统一的收尾保护。',
        ['w-flip-worker-end'],
      ),
    ],
  ),
  choices(
    'wafer-flip-notify',
    '翻转避让后的后台供晶请求',
    '翻转动作结束后会通知供晶，但通知只是另起一段后台轮询；发出通知不等于下一次供晶请求已经发出。',
    ['w-flip-notify-entry', 'w-flip-notify-exit', 'w-flip-controller-transfer'],
    [
      step(
        'avoid',
        '先等翻转轴越过搜索避让位',
        '后台任务读取翻转轴当前位置，只有越过搜索避让位才继续判断下一颗芯片。没有下一颗芯片时，这一轮通知直接结束，既不会刷新地图，也不会发出新的需求。',
        ['w-flip-notify-entry'],
      ),
      step(
        'request',
        '存在下一芯片才更新与请求',
        '查到下一颗芯片名时，若当前料片是晶圆配置，先请求顶针准备位，再刷新地图；随后把当前需求芯片名设为当前料片名，并发出需求。这里用的是当前料片的名称，不是查询到的下一颗芯片名。',
        ['w-flip-notify-entry'],
      ),
      step(
        'timeout',
        '十秒提示、停止与调度边界',
        '等待超过 10 秒会提示继续或退出；选择忽略会重新计时，选择中止会先停机再结束。每轮还会检查停止状态，并延时 10 毫秒。发起通知的一侧不会等待这段后台任务结束，取用的又是当前料片信息，因此不能保证名称已经固定，也不能保证在翻转成功之前完成。',
        ['w-flip-notify-exit', 'w-flip-worker-results'],
      ),
    ],
  ),
  choices(
    'wafer-flip-actions',
    '普通与空跑翻转动作的差别',
    '普通动作和空跑都会做真空准备并驱动运动机构；空跑并不是只在界面上模拟、不碰硬件。',
    ['w-flip-controller-entry', 'w-flip-dry-entry', 'w-flip-dry-return'],
    [
      step(
        'prepare',
        '载具真空准备与取片高度',
        '两个入口都取当前翻转工具，用工具晶圆高度加芯片过行程算出取片位置，再做取片前准备。准备过程按晶圆或华夫盒开关对应的真空，开启分支还会延时；其他类型没有对应的处理分支。',
        ['w-flip-controller-entry', 'w-flip-prepare', 'w-flip-dry-entry'],
      ),
      step(
        'pick',
        '普通下降、真空与顶针',
        '普通路径按开关选择一次下降，或者先高速预取再低速取片。拾取延时取翻转工具拾取延时与关真空延时的差值，不足时按零处理；随后打开翻转真空。只有带晶圆的载具配置才请求顶针抬起，之后执行真空延时。',
        ['w-flip-controller-entry', 'w-flip-controller-pick'],
      ),
      step(
        'transfer',
        '普通上抬决定检测和通知时机',
        '启用取后慢速时先低速上抬，只有这一分支并且启用了检测，才检查是否漏晶；处理完成后通知供晶，并移到交接位。未启用取后慢速时直接通知和移动，不执行这里的漏晶检查。',
        ['w-flip-controller-pick', 'w-flip-leak-entry', 'w-flip-controller-transfer'],
      ),
      step(
        'dry',
        '空跑仍开真空、抬顶针并交接',
        '空跑时移动到取片位再抬高 3 毫米，延时并打开翻转真空；晶圆配置仍会请求抬起顶针，之后做真空延时、通知供晶并移到交接位。空跑没有普通路径的低速漏晶检查。两个入口正常结束时都按成功返回，出现异常只做记录后按异常返回，没有统一的回零收尾。',
        ['w-flip-dry-entry', 'w-flip-dry-return', 'w-flip-controller-transfer'],
      ),
    ],
  ),
  choices(
    'wafer-flip-leak',
    '翻转漏晶的五种选择',
    '漏晶检查只在普通动作的取后慢速分支里启用。每次判定漏晶都会增加真空报警计数；重新检测、重新取片和改取下一颗，返回的位置并不相同。',
    ['w-flip-leak-entry', 'w-flip-leak-repick', 'w-flip-controller-transfer'],
    [
      step(
        'recheck',
        '重新检测',
        '选择继续会回到真空复检，只重复软件持晶判断；不会重新下压和开真空取片。再次失败会再增加一次报警计数。',
        ['w-flip-leak-entry'],
      ),
      step(
        'abort',
        '终止',
        '选择中止会先停止设备，再按中止结束。若停止动作本身抛出异常，会被这一层转成异常结果，因此不能保证最终仍记为中止。',
        ['w-flip-leak-entry', 'w-flip-controller-transfer'],
      ),
      step(
        'ignore',
        '忽略',
        '选择忽略会跳过这次判断，继续后面的通知和交接，并按成功结束；但这不能证明工具上确实有芯片。软件持晶标记要到翻转动作成功之后才置位。',
        ['w-flip-leak-entry', 'w-flip-controller-transfer', 'w-flip-worker-results'],
      ),
      step(
        'repick',
        '重取当前芯片',
        '选择重取会先关真空，再低速下压、等待拾取延时、开真空、做真空延时、低速上抬，然后回到真空复检。这里没有重做完整的取片前准备，也没有重新请求顶针抬起。',
        ['w-flip-leak-repick'],
      ),
      step(
        'next',
        '请求下一颗',
        '选择改取下一颗时，先通知供晶，再把翻转台回零，并按未启动结束；翻转线程收到未启动后回到下一颗搜索，重新等待供晶许可，不发布本轮的翻转可取料许可。后台通知此时可能还没有完成。',
        ['w-flip-controller-transfer', 'w-flip-worker-results'],
        [
          outcome(
            '通知完成不是同步前提',
            '通知内部另起的后台任务没有在发起处等待结束；如果通知条件不满足，还可能根本不会发出下一次需求。',
            'w-flip-notify-entry',
            'w-flip-notify-exit',
          ),
        ],
      ),
    ],
  ),
];
