import { flow, outcome, step } from './builders.ts';

export const transportLifecycleFlows = [
  flow(
    'transport-bin-workers',
    '料仓定位与换层',
    '上下料仓 Start 都在未 Enable 或 DryCycle 时返回。它们是独立任务，通过允许推料和允许移动两组信号与输送段交互。',
    ['tr-loader', 'tr-unloader', 'tr-signal-types'],
    [
      step(
        'initial',
        '首次定位并允许推料',
        '两侧首轮都调用 MoveToCurrentPlaceLayer，再发对应 AllowPush 信号。结果 switch 只对 Abort 调用 Stop 并返回，Success break；这里没有默认拒绝其他返回码的分支。',
        ['tr-loader', 'tr-unloader'],
      ),
      step(
        'loader',
        '上料侧等待后推进层号',
        '等 AllowLoaderMoveSignal 后调用 MoveToNextPlaceLayer：当前层+1未越界时移动到下一层、加层号并保存，随后任务重新发 LoaderAllowPushSignal。',
        ['tr-loader', 'tr-loader-next'],
        [
          outcome(
            '料盒与越界',
            '当前层定位会核对料盒和层数；A 盒越界时换下一盒并重置层号，另一盒越界提供换仓或停止；料盒未检测到提供重试、换下一盒或停止。下一层定位有独立的换盒、重置与报警分支。',
            'tr-loader-current',
            'tr-loader-next',
          ),
        ],
      ),
      step(
        'unloader',
        '下料侧移到已推进的当前层',
        '传输控制器末尾已经 AddCurPlaceLayer。UnloaderTask 收到允许移动后仍调用 MoveToCurrentPlaceLayer，使用这个新层号定位，再发 UnloaderAllowPushSignal；并非在该任务里调用 MoveToNextPlaceLayer。',
        ['tr-unload-commit', 'tr-unloader-inc', 'tr-unloader', 'tr-unloader-current'],
        [
          outcome(
            '满仓或料盒不存在',
            '定位前核对当前盒与层数；A 盒越界换盒并重置，另一盒越界提供换仓或停止；盒未检测到提供重试、换下一盒或停止。',
            'tr-unloader-current',
          ),
        ],
      ),
      step(
        'exit',
        '观察状态与异常退出',
        '两侧外层 while 都使用 IsWorking。若在外层判断时读到 Pause，条件为 false 可直接结束任务；下料侧内部的 IsPause 分支只在已经进入循环后才执行。各自 catch 仅显示异常，不补发许可，也不重建任务。',
        ['tr-loader', 'tr-unloader', 'state-read'],
        [
          outcome(
            '继续入口',
            'Machine.Continue 恢复状态与相关标记，不重新调用这两个 Start；生产者退出后，等待者是否还能得到许可须另查信号和再次启动路径。',
            'machine-continue',
            'tr-loader',
            'tr-unloader',
          ),
        ],
      ),
    ],
  ),
  flow(
    'transport-signal-lifecycle',
    '信号等待、暂停与停止',
    '料仓允许移动使用 AutoReset，允许推料使用 ManualReset。Signal.Wait 先检查机台状态，再等待事件；它没有统一的整体等待期限。',
    ['tr-signal-types', 'tr-signal-wait', 'tr-signal-start'],
    [
      step(
        'state',
        'WaitStart 检查状态',
        '入口 Stop 返回 false；Pause 时每 20 毫秒检查并等待，退出暂停循环后返回 true。这里没有等待具体动作完成，也没有再次启动生产任务。',
        ['tr-signal-start'],
        [
          outcome(
            '暂停切换为停止的窗口',
            '暂停循环的条件重新读取状态；若这次读取已是 Stop，会直接跳出 while，末尾没有再次检查 Stop 就返回 true。Signal.Wait 后面的事件循环会再查 Stop，直接使用 WaitStart 的外层任务须看各自后续检查。',
            'tr-signal-start',
            'tr-signal-wait',
          ),
        ],
      ),
      step(
        'event',
        'Wait 轮询事件',
        'WaitStart 成功后，循环每轮先检查 Stop，再 Sleep(5)、WaitOne(recycleTime)。默认构造使用 100 毫秒周期；超时只进入下一轮，没有整体超时结果。进入事件循环后的 Pause 未在该循环内再次检查。',
        ['tr-signal-wait', 'tr-signal-default'],
        [
          outcome(
            '自动与手动复位',
            '事件成功后 AutoReset 将 State 标记改为 ReSet；ManualReset 保持已置位，需显式 ReSet。Set/ReSet 同时操作事件与 State 标记。',
            'tr-signal-wait',
            'tr-signal-set',
            'tr-signal-types',
          ),
        ],
      ),
      step(
        'producer',
        '区分继续、重试与补信号',
        '料仓线程异常的 catch 不调用 Stop 或补发信号；等待者使用无整体期限的 Wait。机台仍工作且事件未置位时可持续等待，不能把点击 Continue 描述成必然恢复握手。',
        ['tr-loader', 'tr-unloader', 'tr-signal-wait', 'machine-continue'],
        [
          outcome(
            '推料未开始',
            '料仓传输返回 NoStart 时 continue，允许推料事件没有在该分支被复位，因此下一轮可继续使用该许可；成功后的换层请求才配合显式复位。',
            'tr-bin-run',
            'tr-output-bin',
            'tr-signal-types',
          ),
        ],
      ),
    ],
  ),
  flow(
    'transport-dry-run',
    'DryCycle 交互',
    'DryCycle 经 StartTask 进入 StartDryRun，跳过普通传输任务分配。该方法调用 Clamp 并用物料记忆、对象和信号循环配合 S1/S2。',
    ['tr-entry', 'tr-dry-initial'],
    [
      step(
        'initial',
        '初始化两段模拟物料',
        '依次 Clamp S1 和 Bond；两段各先置 HasMaterial 并发完成信号，再创建对应 System1/System2 TransportUnit。发布信号与对象创建存在这个先后顺序。',
        ['tr-dry-initial'],
      ),
      step(
        's1',
        'S1 放行后重建本段物料',
        '使用与普通模式相同的 transferDispenseToBondTask 字段。循环检查状态、等待 S1→Bond 放行信号后，把 S1 重新置有料、发 S1 完成信号并创建 S1 对象；没有调用实体 TransferDispenseToBond。',
        ['tr-dry-s1'],
      ),
      step(
        's2',
        'S2 放行后重建本段物料',
        '使用 transferBondToWaitingUnloadTask 字段。等待 Bond→等待区放行后，把 Bond 重新置有料、发 Bond 完成信号并创建 S2 对象；没有调用实体 TransferBondToWaitingUnload。两侧 Wait=false 均退出。',
        ['tr-dry-s2'],
        [
          outcome(
            '对象复用判断',
            '两个字段为空或非 Running 才创建本次循环，没有在这里强制替换仍为 Running 的原任务。DryCycle 也不是从进料到出料的整条实物传输。',
            'tr-dry-s1',
            'tr-dry-s2',
            'tr-entry',
          ),
        ],
      ),
    ],
  ),
  flow(
    'transport-task-alive',
    'IsAlive 的检查范围',
    'IsAlive 按是否 LoaderBin 选择五个任务对象，要求均非空且 Status=Running；这个列表与实际配置创建的任务并不完全对应。',
    ['tr-alive'],
    [
      step(
        'list',
        '选择五个对象',
        '非料仓分支检查 Bond→等待区、S1 段间、S1→Bond、皮带→S1、等待区→皮带。料仓分支换为料仓→S1与等待区→料仓，但仍检查皮带→S1，并未检查 Bond→等待区。',
        ['tr-alive'],
        [
          outcome(
            '与创建分支的差异',
            'LoaderBin 创建料仓进料任务，不在同一分支创建皮带进料任务；None 不创建自动进出料。因而缺少这类对象可能使 IsAlive 返回 false，即使该配置实际创建的其他任务正在运行。',
            'tr-alive',
            'tr-bin-create',
            'tr-belt-create',
            'tr-feed-none',
            'tr-output-task',
          ),
        ],
      ),
      step(
        'meaning',
        '判断 Running，保留边界',
        '列表通过才返回五个 Running 判断的合取，否则 false。没有检测外部送收板、LoaderTask、UnloaderTask 或实物位置，也不能代替再次启动时的 IsAllowTaskClosed 检查。',
        ['tr-alive', 'running-tasks'],
      ),
    ],
  ),
];
