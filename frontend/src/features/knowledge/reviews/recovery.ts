import type { SourceGuide } from '../sourceGuides';
import { flow, outcome, step } from './builders.ts';

// 本页只说明各入口实际做过的状态写入、清理和中止动作；不据名称推断线程或设备已经停止。
export const recoveryGuide: SourceGuide = {
  id: 'recovery-source-review',
  topic: 'recovery',
  diagrams: ['failure-recovery-workflow', 'stop-cleanup-workflow'],
  title: '暂停、继续与停止的实际边界',
  flows: [
    flow(
      'machine-state',
      '状态写入',
      '工作、暂停、停止这三个状态判断，比较的是同一个机台状态。只有旧状态与本次请求的状态不同，才写入新状态，并把这次变化记入统计队列。',
      ['state-read', 'state-write'],
      [
        step(
          'old',
          '读取旧状态',
          '先取出机台当前状态，再与本次请求设置的状态作比较。',
          ['state-write'],
          [
            outcome(
              '状态未变化',
              '整段写入动作都跳过：既不重复写状态，也不把这次请求记入变化队列。',
              'state-write',
            ),
          ],
        ),
        step(
          'write',
          '创建记录并写入枚举',
          '状态确有变化时，先建一条记录，写明当前用户和这次状态变化的内容，再写入新的机台状态。',
          ['state-write'],
        ),
        step(
          'queue',
          '加入统计队列',
          '状态写入后，把这条变化记录交给后台的落库队列。这里不等待数据库真正写完，也没有就地处理写入异常或回滚状态。',
          ['state-write'],
          [
            outcome(
              '状态不能替代实况',
              '这三个状态判断都不去查轴是否停下、任务是否退出，因此机台状态不能当作这些结果的替代证据。',
              'state-read',
              'state-write',
            ),
          ],
        ),
      ],
    ),
    flow(
      'pause-entry',
      '暂停入口',
      '暂停按钮只向机台发出暂停请求，实际动作就是把状态改成暂停，没有附带别的清理。',
      ['pause-ui', 'machine-pause'],
      [
        step('click', '点击暂停入口', '点击后立即发出暂停请求，界面不在这里等待动作收尾。', [
          'pause-ui',
        ]),
        step(
          'pause',
          '写入暂停状态',
          '写暂停状态这一步里没有停轴指令、没有取消任务，也没有等待任务退出。',
          ['machine-pause', 'state-write'],
          [
            outcome(
              '任务在检查点看暂停',
              'S1 的取信号环节只在循环开头和预点胶动作之后看暂停状态。动作执行过程中按下的暂停，要等到下一个检查位置才被处理。',
              's1-input-loop',
            ),
            outcome(
              '继续是独立入口',
              '暂停不会顺带触发继续；继续按钮走的是另一个入口。',
              'machine-pause',
              'continue-ui',
            ),
          ],
        ),
      ],
    ),
    flow(
      'continue-entry',
      '继续入口',
      '继续按钮走独立的继续入口：按安全门配置决定如何恢复，不会重跑生产启动那整套准备检查。',
      ['continue-ui', 'machine-continue', 'working-state'],
      [
        step('click', '点击继续入口', '点击继续后直接进入继续处理，没有额外的确认环节。', [
          'continue-ui',
        ]),
        step(
          'door',
          '按安全门配置分支',
          '没有配置安全门时，直接请求回到工作状态；配置了安全门的，先确认安全门是否关好。',
          ['machine-continue'],
          [
            outcome(
              '安全门未关',
              '只弹出“请先关好安全门”提示；这条分支既不写工作状态，也不置位第一颗点胶的两个标记。',
              'machine-continue',
            ),
          ],
        ),
        step(
          'resume',
          '按分支恢复工作状态',
          '配置了安全门且门已关好时，先把 S1 和 S2 的首颗点胶标记置位，再请求回到工作状态。没有配置安全门的分支不做这两个置位。',
          ['machine-continue'],
          [
            outcome(
              '不等同于重新生产',
              '继续入口不检查当前是否处于暂停，也不新建任务、不做启动前准备、不重载配方，因此不能写成完整的生产重启。',
              'machine-continue',
              'working-state',
            ),
          ],
        ),
      ],
    ),
    flow(
      'ordinary-stop',
      '普通停止',
      '停止按钮先把自己置灰并给出停止提示，再进入停止处理；停止里的各项清理按下面的顺序执行，全程没有统一的等待任务退出。',
      ['stop-ui', 'stop-state', 'stop-signals', 'stop-outputs'],
      [
        step(
          'entry',
          '更新按钮与停止状态',
          '点下停止后按钮立即置灰并弹出提示；停止处理的第一件事是把状态写成停止。按钮这边没有兜底动作在结束时恢复控件。',
          ['stop-ui', 'stop-state'],
        ),
        step(
          'messages',
          '清弹窗并设置停止报警',
          '接着清掉提示框，再设置停止报警；这两步没有就地处理异常。',
          ['stop-state'],
          [
            outcome(
              '停止报警器分支',
              '离线时，设置停止报警直接返回。在线时按条件去取第一个报警器，而这个条件把报警器列表为空也算作可执行，随后仍去取第一个；所以不能说报警器缺失已被稳妥处理。',
              'stop-alarm',
            ),
            outcome(
              '异常中断',
              '前面任一步出现未被处理的异常，后面的清理就不会继续执行。因此“状态已写成停止”和“清理已全部做完”是两件事。',
              'stop-state',
              'stop-signals',
              'stop-outputs',
            ),
          ],
        ),
        step(
          'signals',
          '退出单步并复位需晶信号',
          '退出单步状态，并复位固晶的需晶信号。这里只复位这一个需晶信号，不等于把所有交接信号都清零。',
          ['stop-signals'],
        ),
        step(
          'outputs',
          '按配置关要料，再关顶针台真空',
          '只有当前配置为在线时，才撤销上料台的需料片信号；随后不论是否在线，都会关闭顶针台真空。',
          ['stop-outputs', 'close-eject-vacuum'],
          [
            outcome(
              '真空关闭的内层动作',
              '关闭真空这一步先对吹气、再对真空各复位一个周期，两者的传感器参数都取零，并各自带一段关闭延时；这些结果不会被汇总成“停止成功”的标记。',
              'close-eject-vacuum',
            ),
          ],
        ),
        step(
          'counters',
          '清焊后缺陷计数',
          '最后把焊后检测记录里的当前缺陷数逐条清零，然后停止处理结束。',
          ['stop-outputs'],
          [
            outcome(
              '线程与物料未一并处理',
              '整个停止处理没有逐个任务发中止指令，也没有等待任务结束；也没有在这里清空载具、晶圆和焊点对象。任务之后是否退出，还要看各任务什么时候去看停止状态。',
              'stop-state',
              'stop-signals',
              'stop-outputs',
            ),
          ],
        ),
      ],
    ),
    flow(
      'emergency-stop-entry',
      '急停调用',
      '急停先同时向各轴发停止请求，再走一遍普通停止，最后依次通知 S1、S2 和供晶三个中止入口；这三个入口的实际动作并不相同。',
      ['emergency-axes', 'emergency-tasks', 'abort-s1', 'abort-s2', 'abort-wafer'],
      [
        step(
          'axes',
          '并行调用轴停止',
          '取到轴清单后，对各轴同时发出停止指令。这里只说明指令已发出，不能推断现场机构确实已经停住。',
          ['emergency-axes'],
        ),
        step(
          'stop',
          '执行普通停止',
          '轴停止请求发出后，再执行一次普通停止；它和普通停止共用同一套状态写入和清理。',
          ['emergency-tasks', 'stop-state', 'stop-signals', 'stop-outputs'],
        ),
        step(
          'abort',
          '顺序调用三个中止入口',
          '接着依次通知点胶任务、固晶任务和供晶子任务中止。输送任务的启动那一行已被注释，因此不在这条路径上执行。',
          ['emergency-tasks'],
          [
            outcome(
              'S1 入口',
              '点胶这边只做一次资源释放，没有空值判断、没有取消请求，也没有等待退出。',
              'abort-s1',
            ),
            outcome('S2 入口', '固晶任务这边收到通知后什么也没做，中止入口是空的。', 'abort-s2'),
            outcome(
              '供晶入口',
              '供晶这边原有的线程中止语句全被注释掉，目前没有任何实际执行的中止动作。',
              'abort-wafer',
            ),
          ],
        ),
        step(
          'boundary',
          '方法结束，不汇总退出结果',
          '三个中止入口都返回后，急停流程就结束了。整段既不统一处理异常，也不汇总各任务有没有退出；前面任一步出现异常，后面的顺序调用就可能不再执行。',
          ['emergency-axes', 'emergency-tasks'],
          [
            outcome(
              '名称不等于结果',
              '这三个中止入口的名字，不能当作所有生产任务已经结束的证据。急停之后任务何时真正退出、设备处于什么状态、能否再次启动，还要逐个模块继续核对。',
              'abort-s1',
              'abort-s2',
              'abort-wafer',
              'running-tasks',
            ),
          ],
        ),
      ],
    ),
    flow(
      'task-closed-gate',
      '再次启动门控',
      '停止或急停后再次点生产启动，仍会重新走启动前的准备检查，其中有一道任务状态检查；它和继续入口的安全门分支是两条不同的路。',
      ['prepare-gates', 'running-tasks', 'machine-continue'],
      [
        step(
          'collect',
          '收集待检查任务',
          '参与检查的清单按当前配置来定，包括 S1、供晶、固晶、胶盘、翻转，以及各段输送和上下料的任务。',
          ['running-tasks'],
        ),
        step(
          'running',
          '只在运行中时拒绝',
          '逐个看清单里已存在的任务，只要有一个仍处于运行中，就提示并拒绝启动；全部看完都没有运行中的，才放行。',
          ['running-tasks'],
          [
            outcome(
              '门控范围',
              '放行只说明这轮检查没有发现运行中的任务，不能据此推断所有任务都已正常完成，也不能推断硬件都已停下。',
              'running-tasks',
              'state-read',
            ),
          ],
        ),
      ],
    ),
  ],
  boundaries: [
    {
      text: '本页核对暂停、继续、普通停止、急停和再次启动这几个入口，以及各自中止时到底做了什么。动作内部的失败重试、可忽略的结果、提示等待和物料恢复，仍要按各生产模块继续核对。',
      refs: ['machine-pause', 'machine-continue', 'emergency-tasks', 's1-input-loop'],
    },
    {
      text: '本页只说明程序当前已有的行为，以及仍然缺失的确认步骤；没有运行生产，也没有改动设备控制逻辑。',
      refs: ['stop-state', 'emergency-axes', 'abort-s1', 'abort-s2', 'abort-wafer'],
    },
  ],
};
