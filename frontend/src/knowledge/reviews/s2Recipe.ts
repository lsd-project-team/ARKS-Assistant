import { choices, flow, outcome, step } from './builders.ts';

// 排序按实际循环嵌套解释，模式名称本身不作为执行顺序的证据。
export const s2RecipeFlows = [
  flow(
    's2-recipe-init',
    '配方初始化与消息生成',
    'S2 在生产启动处初始化消息表，随后异步启动 BondTask；线程 DoWork 中的再次 Init 已被注释。初始化不是每片载具都重新执行的步骤。',
    ['working-state', 's2-worker-entry'],
    [
      step(
        'clear',
        '清空消息，读取启用步骤',
        'ProcessSteps 每次从配方中筛出 IsEnable 的步骤。Init 先清空 WorkMessages，若无启用步骤直接返回，尚未清空缓存 ProcessStep，也未执行后续过滤和相对排序。',
        ['s2-enabled-steps', 's2-controller-init'],
      ),
      step(
        'choose',
        '选择八种排序入口',
        'TransportFirst、SubstrateFirst、ModuleFirst、BondPositionFirst 各按 StepFirst 或 else 进入一个方法。WorkProcess switch 没有 default；未知值在此不会生成消息。',
        ['s2-sort-switch'],
      ),
      step(
        'prepare',
        '插入各层准备动作',
        '准备动作来自仓库的载具、基板、基岛、焊点四组：各组包含定位、测高和标识节点。消息携带动作名、基板号、基岛号和步骤名；零号和空步骤名用于较高层准备动作。',
        ['s2-repository-prep', 's2-transport-prep', 's2-message-model'],
      ),
      step(
        'post',
        '依次过滤，再改相对顺序',
        '生成消息后依次 RemoveOtherStep、RemoveDisableActionNode、SortRelativeBond。后两者不能交换成“先相对排序，再过滤”，也不能将消息生成当作硬件执行完成。',
        ['s2-controller-init'],
        [
          outcome(
            '无消息的后续边界',
            'Finish 只检查列表是否为 null，随后读取 WorkMessages[0]；空列表在收尾处仍可能抛出越界异常。',
            's2-controller-finish',
          ),
        ],
      ),
    ],
  ),
  choices(
    's2-recipe-sort',
    '八种排序的实际区别',
    '下列顺序指生产消息的嵌套循环；准备消息按各方法自己的循环先行插入。每个启用步骤再展开为取晶、检测或点胶消息。',
    ['s2-sort-switch', 's2-message-choose'],
    [
      step(
        'transport',
        '载具优先：按基板分组',
        'WorkCycleNumber 用作每组基板数；关闭分组配置时用全部基板数。StepFirst 的生产顺序为组 → 步骤 → 基板 → 基岛；PositionFirst 为组 → 基板 → 基岛 → 步骤。每组先加入基板、基岛及去重焊点的准备消息。',
        ['s2-transport-cycle', 's2-transport-prep', 's2-transport-step', 's2-transport-position'],
        [
          outcome(
            '分组参数边界',
            'GetCycleList 生成从 0 开始的连续索引，调用方转为 1 开始的消息编号。该方法没有校验 cycleNumber；当总数大于 0 且组大小不大于 0 时，外层索引不前进。',
            's2-cycle-list',
          ),
        ],
      ),
      step(
        'substrate',
        '基板优先：按基岛分组',
        '每块基板先加入基板准备消息，再按 WorkCycleNumber 分基岛组，关闭分组时采用全部基岛数。StepFirst 为基板 → 组 → 步骤 → 基岛；PositionFirst 为基板 → 组 → 基岛 → 步骤。焊点准备的内层顺序也分别为步骤 → 基岛、基岛 → 步骤。',
        ['s2-substrate-step', 's2-substrate-position'],
      ),
      step(
        'same',
        '三个入口的循环结构相同',
        'ModuleFirst 的 StepFirst、PositionFirst，以及 BondPositionFirst 的 StepFirst，当前都按基板 → 基岛 → 步骤生成生产消息，并先加入该基岛全部去重焊点的准备消息。不能仅凭名称写出三套不同的执行顺序。',
        ['s2-module-step', 's2-module-position', 's2-position-step'],
      ),
      step(
        'interleave',
        '焊点优先：准备消息穿插',
        'BondPositionFirst + PositionFirst 在每个基岛内依次读步骤：遇到某焊点的首个启用步骤，先加入该焊点准备消息，再生成本步骤生产消息，并从去重列表移除该步骤。GetWorkBondPosition 按 BondPositionName 分组取首项，未另按名称排序。',
        ['s2-position-position', 's2-distinct-position'],
      ),
    ],
  ),
  choices(
    's2-message-map',
    '取晶、检测与点胶消息映射',
    'GetActionNodeMessageByProcess 使用 ComponentName、DefectName、EpoxyNameApplicationName 的 if / else if 链，比较的是字符串 "Null"；三个用途不会在这里自动叠加。',
    ['s2-message-choose', 's2-message-other'],
    [
      step(
        'component',
        '先选择芯片配方',
        'ComponentName 不等于 "Null" 时查 CarrierConfigRepository。找不到配置会直接抛异常，此处没有改走胶检或点胶分支；空字符串或 C# null 也不等于字面字符串 "Null"。',
        ['s2-message-choose'],
      ),
      step(
        'after',
        '翻转台：校正后蘸胶',
        'IsUseFlipTable 且 DipMode 为 AfterAccuracyMode 时，消息顺序为 Pick → UpLookCorrection → DipFlux → SubstrateCameraCorrection → Bond。这里生成的是消息，并未在排序时执行各动作。',
        ['s2-message-after'],
      ),
      step(
        'before',
        '翻转台：关闭或其他蘸胶模式',
        'DipMode 为 Off 时没有 DipFlux：Pick → UpLookCorrection → SubstrateCameraCorrection → Bond。其余值走 Pick → DipFlux → UpLookCorrection → SubstrateCameraCorrection → Bond。',
        ['s2-message-off', 's2-message-before'],
      ),
      step(
        'direct',
        '未使用翻转台',
        'IsUseFlipTable 为 false 时生成 Pick → UpLookCorrection → SubstrateCameraCorrection → Bond。该分支没有再判断 DipMode，也不在这里加入 DipFlux。',
        ['s2-message-direct'],
      ),
      step(
        'other',
        '后续才考虑检测或点胶',
        '只有 ComponentName 等于 "Null" 才检查 DefectName：非 "Null" 时加入 AfterBondCheck；否则 EpoxyNameApplicationName 非 "Null" 时加入 S2Dispense；三个名称都为 "Null" 则返回空消息集合。',
        ['s2-message-other'],
      ),
    ],
  ),
  flow(
    's2-filter-relative',
    '物料过滤与相对贴片排序',
    '这部分调整 WorkMessages，不代表视觉检测或贴片已执行；相对贴片重排在物料过滤之后发生。',
    ['s2-controller-init', 's2-relative-read', 's2-relative-insert'],
    [
      step(
        'shape',
        '按异形结构过滤',
        '非异形配置直接返回。异形时保留基板号为 0 的消息，删除超出基板或基岛范围的消息，再按步骤对应焊点是否存在过滤；步骤名找不到时继续保留该消息。',
        ['s2-shape-filter'],
      ),
      step(
        'disable',
        '有条件地过滤禁用物料',
        'RemoveDisableActionNode 仅在 LagerNumber 为 true 且当前载具非空时运行，先按 WorkIndex 排序实际基板和基岛。基板准备按基板状态过滤；带步骤消息按焊点状态过滤；空步骤的基岛消息按基岛状态过滤，不是统一检查动作启用开关。',
        ['s2-disable-entry', 's2-disable-items'],
        [
          outcome(
            '索引和配置边界',
            '该段用消息编号减 1 直接索引集合；步骤和焊点查找结果在读取属性前没有 null 保护，缺少匹配可能抛异常。',
            's2-disable-items',
          ),
        ],
      ),
      step(
        'remove',
        '查相对焊点，删除原视觉消息',
        '只读取 RelativeBondPosition 的配置，查其首个启用步骤，然后删除同步骤名的 BondPositionVisionActionNode。找不到步骤仍把 null 加入列表，列表非空检查不能排除这个空项。',
        ['s2-relative-read', 's2-relative-remove'],
        [
          outcome(
            '缺少步骤',
            '后续访问 singleProcess.ProcessStepName 时可能抛异常；不能把配置存在写成配对步骤一定存在。',
            's2-relative-remove',
            's2-relative-insert',
          ),
        ],
      ),
      step(
        'insert',
        '在每条取晶消息前重插视觉',
        '扫描同步骤名的 PickActionNode，在它前面插入同基板、同基岛、同步骤的视觉消息。无 Pick 就没有替代插入；此时已经越过禁用过滤阶段，插入后没有再次调用该过滤方法。',
        ['s2-relative-insert', 's2-controller-init'],
      ),
    ],
  ),
];
