import type { SourceGuide } from '../sourceGuides';
import { flow, outcome, step } from './builders.ts';

// 按当前方法体描述状态、清理和中止调用；不由方法名称推断线程或设备已停止。
export const recoveryGuide: SourceGuide = {
  id: 'recovery-source-review',
  topic: 'recovery',
  diagrams: ['failure-recovery-workflow', 'stop-cleanup-workflow'],
  title: '暂停、继续与停止的实际边界',
  flows: [
    flow(
      'machine-state',
      '状态写入',
      'IsWorking、IsPause、IsStop 都比较同一个机台状态枚举。SetState 只在新旧状态不同的分支写入状态并把变化记录加入统计队列。',
      ['state-read', 'state-write'],
      [
        step(
          'old',
          '读取旧状态',
          '读取 MachineStateModel.MachineState，与请求设置的状态比较。',
          ['state-write'],
          [
            outcome(
              '状态相同',
              '整个 if 块跳过，不再次写入状态，也不把这次调用加入变化记录队列。',
              'state-write',
            ),
          ],
        ),
        step(
          'write',
          '创建记录并写入枚举',
          '状态不同时，先创建含当前用户与状态变化描述的记录，再写入 MachineState。',
          ['state-write'],
        ),
        step(
          'queue',
          '加入统计队列',
          '状态写入后调用 DbEntityBlockingCollection.Add；这里没有等待数据库写入完成，也没有在方法内捕获异常或回滚状态。',
          ['state-write'],
          [
            outcome(
              '状态的含义',
              '这三个 Is 方法没有查询轴是否停止或 Task 是否退出，状态枚举不能代替这些结果。',
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
      'BtPause_ItemClick 调用 Machine.Pause；Pause 的方法体只请求 SetState(Pause)。',
      ['pause-ui', 'machine-pause'],
      [
        step(
          'click',
          '点击暂停入口',
          '该事件处理方法直接调用 Machine.Pause，没有在这里等待动作结束。',
          ['pause-ui'],
        ),
        step(
          'pause',
          '写入 Pause 状态',
          'Pause 调用 SetState(Pause)，方法内没有调用 StopMove、取消任务或等待任务退出。',
          ['machine-pause', 'state-write'],
          [
            outcome(
              '任务观察暂停的位置',
              'S1 GetInputSignal 在循环开头和预点胶动作后检查 Pause。动作执行期间的状态变化，需要到后续检查位置才由这段循环处理。',
              's1-input-loop',
            ),
            outcome(
              '独立操作',
              'Pause 不调用 Continue；继续按钮是另一个事件入口。',
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
      '继续按钮调用 Machine.Continue。这个入口按安全门配置处理，不重新调用生产 Start 的整套准备检查。',
      ['continue-ui', 'machine-continue', 'working-state'],
      [
        step('click', '点击继续入口', 'BtContinue_ItemClick 直接调用 Machine.Continue。', [
          'continue-ui',
        ]),
        step(
          'door',
          '按安全门配置分支',
          '未配置安全门时直接请求 Working；已配置时检查 IsSafeDoorClose。',
          ['machine-continue'],
          [
            outcome(
              '安全门未关',
              '只弹出“请先关好安全门”提示，不在该分支写入 Working 或两个 IsFirstDispense 标记。',
              'machine-continue',
            ),
          ],
        ),
        step(
          'resume',
          '按分支恢复 Working',
          '已配置且安全门关闭时，先把 S1 与 S2 的 IsFirstDispense 设为 true，再请求 Working。未配置安全门的分支没有这两个赋值。',
          ['machine-continue'],
          [
            outcome(
              '调用范围',
              'Continue 没有检查当前枚举必须是 Pause，也没有在这里创建任务、调用 Prepare 或重新加载配方；不能把它写成完整的生产重启。',
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
      '停止按钮先禁用自身控件、显示停止提示，再调用 Machine.Stop。Stop 的清理按下列顺序调用，没有统一的任务退出等待。',
      ['stop-ui', 'stop-state', 'stop-signals', 'stop-outputs'],
      [
        step(
          'entry',
          '更新按钮与停止状态',
          'BtCancel_ItemClick 设置 Enabled = false 并显示提示；Machine.Stop 首先请求 SetState(Stop)。该按钮方法内没有 finally 恢复控件。',
          ['stop-ui', 'stop-state'],
        ),
        step(
          'messages',
          '清弹窗并设置停止报警',
          '依次调用 ClearMessageBox 和 SetStopStateAlarm；不在 Stop 中捕获这些调用的异常。',
          ['stop-state'],
          [
            outcome(
              '停止报警器分支',
              'SetStopStateAlarm 在离线时直接返回；在线时按列表条件访问第一个报警器。条件把列表为 null 也列入执行分支，随后仍访问 [0]，不能描述为已安全处理报警器缺失。',
              'stop-alarm',
            ),
            outcome(
              '异常中断',
              '前序调用若抛出未处理异常，后面的清理语句不会由本方法继续执行；停止状态赋值与完整清理是不同观察点。',
              'stop-state',
              'stop-signals',
              'stop-outputs',
            ),
          ],
        ),
        step(
          'signals',
          '退出单步并复位需晶信号',
          '设置 IsSingleStepWork = false，复位 IsBondNeedChipSignal。这里只复位这个需晶信号，不能描述成清空全部交接信号。',
          ['stop-signals'],
        ),
        step(
          'outputs',
          '按配置关要料，再关顶针台真空',
          'LoadConfiguration 为 Online 时调用 SetLoadingTableNeedTabletSignal(false)。随后无此条件地调用 CloseEjectionTableVacuum。',
          ['stop-outputs', 'close-eject-vacuum'],
          [
            outcome(
              '真空关闭调用内层',
              'CloseEjectionTableVacuum 依次对吹气与真空调用 ResetCyc，两个传感器参数都传 0，并各自传入关闭延时；方法没有把返回结果汇总为停止成功标记。',
              'close-eject-vacuum',
            ),
          ],
        ),
        step(
          'counters',
          '清焊后缺陷计数',
          '遍历 PostBondInspections，把 CurrentDefectNumber 设为 0，然后方法结束。',
          ['stop-outputs'],
          [
            outcome(
              '线程与物料',
              '该方法未统一调用各任务的 Abort、Wait 或 Join，也没有在这里清空所有载具、晶圆及焊点对象；后续是否退出还需查看各任务观察停止的路径。',
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
      'EmergencyStop 先并行请求各轴停止，再调用普通 Stop，最后顺序调用 S1、S2 和供晶的中止入口。这些入口的实际方法体不同。',
      ['emergency-axes', 'emergency-tasks', 'abort-s1', 'abort-s2', 'abort-wafer'],
      [
        step(
          'axes',
          '并行调用轴停止',
          '取得 Axis 列表，以 Parallel.ForEach 调用每个 axis.StopMove(false, true)；这里只说明调用，不推断现场机械停止已确认。',
          ['emergency-axes'],
        ),
        step(
          'stop',
          '执行普通 Stop',
          '并行调用语句返回后，再调用 Machine.Stop；该方法与普通停止共用状态和清理逻辑。',
          ['emergency-tasks', 'stop-state', 'stop-signals', 'stop-outputs'],
        ),
        step(
          'abort',
          '顺序调用三个中止入口',
          '依次调用 DispenseWorkTask.AbortThread、BondTask.AbortThread 和 AbortWaferSubThread。输送 StartTask 行在这里被注释，不是实际执行语句。',
          ['emergency-tasks'],
          [
            outcome(
              'S1 方法体',
              '直接调用 DispenseTask.Dispose，没有空值分支、取消请求或等待退出语句。',
              'abort-s1',
            ),
            outcome('S2 方法体', 'BondTask.AbortThread 方法体为空。', 'abort-s2'),
            outcome(
              '供晶方法体',
              '原线程 Abort 相关语句全部被注释，当前方法没有实际执行的中止语句。',
              'abort-wafer',
            ),
          ],
        ),
        step(
          'boundary',
          '方法结束，不汇总退出结果',
          '最后一个中止入口返回后，EmergencyStop 到达方法末尾。方法没有统一捕获异常或汇总任务退出结果；前面的调用抛出异常时，后续顺序调用可能不执行。',
          ['emergency-axes', 'emergency-tasks'],
          [
            outcome(
              '方法名与结果',
              '这三个方法名不能作为所有生产线程已结束的证据。急停后的线程退出、设备状态和再次启动仍需继续核对各模块。',
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
      '再次点击生产启动仍调用 Prepare，并使用 IsAllowTaskClosed 的任务状态检查。它与 Continue 的安全门入口不同。',
      ['prepare-gates', 'running-tasks', 'machine-continue'],
      [
        step(
          'collect',
          '收集待检查 Task',
          '列表包含按配置参与的 S1、供晶、固晶、胶盘、翻转，以及各输送段和上下料 Task。',
          ['running-tasks'],
        ),
        step(
          'running',
          '只在 Running 时拒绝',
          '检查列表中的非空 Task，只要 Status 等于 Running 就提示并返回 false；遍历结束返回 true。',
          ['running-tasks'],
          [
            outcome(
              '门控范围',
              '返回 true 只说明这个判断没有发现 Running；不能据此推断全部 Task 已成功完成或全部硬件已停止。',
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
      text: '本次复核暂停、继续、普通停止、急停与再次启动的入口及中止方法体。动作内层的 Retry、Ignore、消息等待与物料恢复仍须按各生产模块继续阅读。',
      refs: ['machine-pause', 'machine-continue', 'emergency-tasks', 's1-input-loop'],
    },
    {
      text: '页面展示的是当前源码的行为和缺失的确认步骤，没有执行生产代码或修改设备控制逻辑。',
      refs: ['stop-state', 'emergency-axes', 'abort-s1', 'abort-s2', 'abort-wafer'],
    },
  ],
};
