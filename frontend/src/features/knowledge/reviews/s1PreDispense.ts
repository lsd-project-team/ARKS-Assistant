import { flow, outcome, step } from './builders.ts';

export const s1PreDispenseFlows = [
  flow(
    's1-predispense-timing',
    '预点胶何时触发',
    '等料循环与点胶节点都会调用预点胶动作，但调用不等于出胶。IsDispense 依次检查手动、关闭、首点时机和周期时间，未满足时直接返回 Success。',
    ['s1-input-loop', 's1-point-before', 's1-pre-entry', 's1-pre-timing'],
    [
      step(
        'manual',
        '手动优先，关闭配置次之',
        'IsManual=true 首先返回 true，绕过时机与模式判断；自动路径只有模式和时机同时为 Off 才直接返回 false。DoWork 的 IsDispense=false 分支不执行条件报警、挤胶、取位置或插补。',
        ['s1-pre-timing', 's1-pre-entry'],
      ),
      step(
        'first',
        '首点还需要当前点胶节点',
        '首点分支同时要求 IsFirstDispense、CurrentActionNode 为 S1DispenseActionNode、时机为 BeforeComingFirstDispense。仅置首点标记，或在没有当前点胶节点的等料阶段调用，并不足以满足这一分支。',
        ['s1-pre-timing', 's1-current-action'],
      ),
      step(
        'periodic',
        '周期按最后更新时间判断',
        'Periodic 模式比较当前时间与 LastDispenseTime，间隔单位为毫秒，使用严格大于。字段初值是对象创建时的 DateTime.Now；DoWork 走到正常尾部才更新它，跳过执行或提前返回时不更新时间。',
        ['s1-pre-time', 's1-pre-timing', 's1-pre-check-tail'],
      ),
      step(
        'every',
        '每次点胶选项的实际消费',
        '枚举包含 BeforeEveryDispense，点胶节点尾部会为它置 IsFirstDispense=true；但 IsDispense 没有该时机的独立分支，仍需满足手动或周期条件等已有路径，不能据选项名称断言每次都执行预点胶。',
        ['s1-pre-timing', 's1-pre-enums', 's1-point-after'],
        [
          outcome(
            '异常与回调',
            'try 内异常返回 Exception；finally 无论跳过、报警还是正常结束都会清 IsManual、置动作 Stop 并调用 WorkStop。WorkStart 在 try 前，回调异常不保证被该 catch 转成返回码。',
            's1-pre-entry',
            's1-pre-finally',
          ),
        ],
      ),
    ],
  ),
  flow(
    's1-predispense-execution',
    '预点胶板、挤胶与检查',
    '触发后先检查点胶头、图案名和板示教，再挤胶、批量取得板上位置、逐点调用插补，最后按配置检查胶形或移动到手动观察位置。',
    ['s1-pre-entry', 's1-pre-ready', 's1-pre-pattern', 's1-pre-check-tail'],
    [
      step(
        'ready',
        '三项前提检查',
        '点胶头为空或未示教、预点胶图案名为空、预点胶板 IsReady=false 均弹报警并让 IsAlarm 返回 true，DoWork 返回 Abort。板 IsReady 只读取 AssistanceFinish，不在这里验证实际位置或清洁程度。',
        ['s1-pre-ready', 's1-pre-entry', 's1-plate-ready'],
      ),
      step(
        'squeeze',
        '可选挤胶先于取位置',
        'EnableEpoxySqueeze 时设胶压，调用移动到挤胶位置、开胶、睡眠、关胶，再调用移动到擦胶位置。此方法没有 DryCycle 或 isDrip 条件，也没有统一 finally 关胶；不能套用后面插补的空跑分支解释它。',
        ['s1-pre-squeeze', 's1-pre-entry'],
      ),
      step(
        'plate',
        '取得位置时就推进板索引',
        '板为空时 InitPre 按行列和首末坐标生成网格，置 Index=0 并保存。GetEpoxy 按列推进，先 Index++ 再取位置和保存；批量 GetEpoxy(count) 在任何插补开始前取得全部位置，后续动作失败不会由这些方法回退已推进的索引。',
        [
          's1-plate-init',
          's1-plate-next',
          's1-plate-index',
          's1-plate-batch',
          's1-pre-entry',
          's1-pre-pattern',
        ],
        [
          outcome(
            '板满或行列变化',
            'Index 等于网格长度时，DryCycle 自动 InitPre；其他模式确认清洁后重建，其他选择抛异常。行列变化另行询问并重建，取消同样抛异常；没有把清洁确认当作传感器检测。',
            's1-plate-next',
            's1-plate-index',
          ),
          outcome(
            '数量为零或负数',
            '批量方法的循环不进入，返回空列表；DoWork 把 null 或空列表当异常，最终转成 Exception。',
            's1-plate-batch',
            's1-pre-entry',
          ),
        ],
      ),
      step(
        'pattern',
        '逐点调用预点胶插补',
        '从仓库按配置名取得胶型，每个位置调用 InterpolationApplication，isPrePlant=true、angle=0；DryCycle 的 isDrip=false。任何一次返回非 Success，预点胶动作直接返回 Alarm，不继续剩余位置。',
        ['s1-pre-pattern'],
      ),
      step(
        'check',
        '检查结果未进入返回码判断',
        '找到胶后检查对象时，使用末次位置加检测偏移调用 CheckEpoxyApplication；该方法返回 PostBondEpoxyCheck 的结果，但 DoWork 未使用这个结果，随后更新时间并返回 Success。生产胶检节点则明确消费该返回码，两者不能合并说明。',
        ['s1-pre-check-tail', 's1-pre-check', 's1-defect-results'],
        [
          outcome(
            '手动且无检查对象',
            '调用 Z 安全位，计算末次点胶位置对应的视觉位，加 PrePlantOffSetZ 后移动。正常尾部和 finally 都清 IsManual；检查或移动抛异常则进入异常分支。',
            's1-pre-check-tail',
            's1-pre-finally',
          ),
        ],
      ),
    ],
  ),
];
