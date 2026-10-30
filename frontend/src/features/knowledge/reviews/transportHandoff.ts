import { flow, outcome, step } from './builders.ts';

export const transportHandoffFlows = [
  flow(
    'transport-dispense-split',
    'S1 第一段到第二段',
    '点胶段间传输 Task 在 Start 中实际创建，旁边“下一迭代”的注释未禁用 Task.Run。控制器通过物料与许可判断后执行传输。',
    ['tr-split-task', 'tr-split-gate'],
    [
      step(
        'gate',
        '判断物料与许可',
        '没有 S1 物料返回 NoStart。自动调用等待 AllowDispense1TransferToDispense2Signal，Wait=false 返回 Abort；手动调用只允许 Divide 且 IsTuInDispense1=true。',
        ['tr-split-gate'],
      ),
      step(
        'move',
        '段间传输与位置更新',
        '置 Transfering，UnClamp，第一挡料降下、第二挡料升起，调用皮带运动等待；之后 Clamp，写 HasMaterial、Ready，置 IsTuInDispense1=false，调用 System1MoveDistance 并标记需要预点胶。',
        ['tr-split-move'],
      ),
      step(
        'signal',
        '向第二段发布完成',
        '返回 Success 时线程发 TransferToDispense2FinishedSignal；NoStart 延时后下一轮，Abort 调用 Stop 后下一轮重新检查 WaitStart。线程 catch 仅显示异常。',
        ['tr-split-task'],
      ),
    ],
  ),
  flow(
    'transport-dispense-bond',
    'S1 传入 S2',
    'S1→Bond Task 先处理首次 Bond 已有物料，再调用传输控制器。完成信号也可能来自已有物料分支。',
    ['tr-bond-first', 'tr-bond-task'],
    [
      step(
        'gate',
        '检查占用与放行',
        '需 Bond=NoMaterial 且 S1=HasMaterial。自动调用等待 AllowDispenseTransferToBondSignal，Wait=false 返回 Abort；手动 Divide 模式下，载具仍在 S1 第一段时返回 NoStart。',
        ['tr-bond-gate'],
        [
          outcome(
            '首次 Bond 已有料',
            '不提示时直接发 Bond 完成信号，继续本轮；提示时首轮处理后 continue，Yes 发完成信号，No 调用 Stop。这个信号不只在新传输成功后发出。',
            'tr-bond-first',
          ),
        ],
      ),
      step(
        'move',
        '等待气缸后传输',
        'retry 位于许可等待之后。并行调用两段 UnClamp 与挡料动作，S1 UnClamp 受配置限制；WaitAll 后启动 S1 皮带，在运动中检测 S1 出口。',
        ['tr-bond-move'],
      ),
      step(
        'alarm',
        '两处卡料与重试',
        'S1 出口未检测到物料时报警；否则启动 Bond 皮带并复查 S1 出口，仍有料时报警。两处 Retry 都回到气缸与皮带动作前的 retry；Abort 返回，Ignore 继续共同提交区。',
        ['tr-bond-alarm'],
      ),
      step(
        'commit',
        '移交载具并发信号',
        '并行 Clamp Bond、恢复 S1 两个挡料，等待后把 S1 载具移给 Bond 并 Refresh，清 S1 载具，写 Bond 有料/S1 无料、两段 Ready，保存后返回 Success；线程随后发 Bond 完成信号。',
        ['tr-bond-commit', 'tr-bond-task'],
        [
          outcome(
            '异常与返回码',
            '控制器异常返回 Exception，但本线程 switch 没有 Exception 分支；Abort 调用 Stop，NoStart 和未处理返回码进入后续循环。线程 catch 只显示异常。',
            'tr-bond-commit',
            'tr-bond-task',
          ),
          outcome(
            'Ignore 的边界',
            '两处报警忽略后同样可写入上述物料状态和 Success，状态提交不能独立证明实际传输成功。',
            'tr-bond-alarm',
            'tr-bond-commit',
          ),
        ],
      ),
    ],
  ),
  flow(
    'transport-bond-wait',
    'S2 传入等待区',
    '需 Bond 有料、等待区无料，并在自动调用中收到 Bond 放行。该段两处报警重试回到不同位置。',
    ['tr-wait-gate'],
    [
      step(
        'gate',
        '等待空位与放行',
        'Bond 不为 HasMaterial 或等待区不为 NoMaterial 返回 NoStart；自动等待 AllowBondTransferToWaitingUnloadSignal，Wait=false 返回 Abort。手动调用跳过这次信号等待。',
        ['tr-wait-gate'],
      ),
      step(
        'bond',
        '从 Bond 段送出',
        'retry1 并行 UnClamp Bond、降挡料，等待后启动 Bond 皮带并检测出口。未检测到时置 Alarm；Retry 回 retry1，Abort 返回，Ignore 跳过等待段传输的 else 而进入共同提交区。',
        ['tr-wait-first', 'tr-wait-commit'],
      ),
      step(
        'wait',
        '等待段传输与复查',
        '出口检测到时进入 retry2，启动等待段皮带，循环读取 Bond 出口与 Unloading 控制器入口；入口检测到时停止 Bond 和等待段皮带。结束后若 Bond 出口仍有料或入口未检测到，进入卡料报警。',
        ['tr-wait-second'],
        [
          outcome(
            '此处重试',
            'Retry 只回 retry2 重新运行等待段，不回前面的 Bond 解夹与启动步骤；Abort 返回，Ignore 继续共同提交。',
            'tr-wait-second',
          ),
          outcome(
            '尚未提前提交',
            '循环里“Bond 出口无料就提前提交”的赋值已被注释，实际提交在两个检测阶段之后。',
            'tr-wait-second',
            'tr-wait-commit',
          ),
        ],
      ),
      step(
        'commit',
        '提交等待区状态',
        '把 Bond 载具移到等待区并 Refresh，等待区置 HasMaterial，Bond 置 NoMaterial 并清载具，两段置 Ready；手动时另调用 Bond.UnClamp。保存后返回 Success。',
        ['tr-wait-commit'],
        [
          outcome(
            '线程分派',
            'NoStart 继续循环，Success 记录结果；Abort 或 Exception 调用 Stop 后再循环检查 WaitStart。该线程 catch 记录并提示，没有额外 Stop。',
            'tr-wait-task',
          ),
        ],
      ),
    ],
  ),
];
