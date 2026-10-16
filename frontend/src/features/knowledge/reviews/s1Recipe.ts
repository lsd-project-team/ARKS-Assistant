import { flow, outcome, step } from './builders.ts';

export const s1RecipeFlows = [
  flow(
    's1-recipe-messages',
    '配方如何生成动作',
    'S1 线程开始时调用 Init，按启用步骤和排序设置建立动作消息；每件载具再注入焊点步骤。动作消息与焊点的步骤字典分别维护。',
    ['s1-worker-entry', 's1-init', 's1-inject'],
    [
      step(
        'enabled',
        '读取启用步骤',
        'ProcessSteps 每次访问都从 S1SystemProcess 筛选 IsEnable。Init 先清空 WorkMessages；没有启用步骤便返回，尚未执行排序、异形过滤及当前消息清空。',
        ['s1-enabled-steps', 's1-init'],
      ),
      step(
        'mode',
        '按两项配置选择排序',
        'WorkProcess 分载具、基板、基岛、焊点优先；每种再按 WorkProcessModule 是否为 StepFirst 选择方法。两项配置共同影响展开顺序，不能只按方法名字判断。',
        ['s1-sort-choice'],
      ),
      step(
        'mapping',
        '将步骤映射为点胶或检测',
        'EpoxyNameApplicationName 不等于字符串 "Null" 时生成点胶消息；只有该条件不成立且 DefectName 不等于 "Null" 才生成检测消息。这里使用 if / else if，一个步骤不会同时生成这两种消息。',
        ['s1-step-action'],
        [
          outcome(
            '两项均为 "Null"',
            '该方法返回空列表，不增加点胶或检测消息；字面字符串 "Null" 的比较不等同于统一的空值校验。',
            's1-step-action',
          ),
        ],
      ),
      step(
        'filter',
        '异形产品过滤',
        '非异形产品不执行 RemoveOtherStep。异形产品移除超出基板、基岛数量或对应基岛不含该焊点的消息；基板索引为 0 的消息跳过过滤，找不到制程步骤的消息也继续保留。',
        ['s1-filter-messages', 's1-layout-counts'],
      ),
      step(
        'inject',
        '保留已有焊点步骤状态',
        'InjectSteps 遍历载具的基板、基岛和焊点。启用步骤的 BondPositionName 与焊点名相同时，仅对字典里不存在的步骤名添加 false；已有 true 或 false 不被覆盖。',
        ['s1-inject'],
        [
          outcome(
            '当前动作的来源',
            '当前基板、基岛和焊点按消息索引及步骤名查找；胶型、检测配置按当前步骤的名称查询仓库。读取不到对象时，这些访问并没有统一补默认对象。',
            's1-current-context',
          ),
        ],
      ),
    ],
  ),
  flow(
    's1-order-expansion',
    '八种排序的实际区别',
    '排序方法添加的是动作消息。各层预备动作和配方动作的嵌套顺序不同；焊点预备动作使用按 BondPositionName 分组后的首个启用步骤。',
    ['s1-position-groups', 's1-order-transport-step', 's1-order-bond-position'],
    [
      step(
        'transport',
        '载具优先',
        '两种模式都先铺开载具、基板、基岛及焊点层动作。StepFirst 最后按步骤 → 基板 → 基岛展开配方动作；另一模式按基板 → 基岛 → 步骤展开。',
        ['s1-order-transport-step', 's1-order-transport-position'],
      ),
      step(
        'substrate',
        '基板优先',
        '载具动作之后逐块处理基板。StepFirst 在当前基板内按步骤 → 基岛展开；另一模式按基岛 → 步骤展开。当前基板的基岛和焊点预备动作在该基板的配方动作之前加入。',
        ['s1-order-substrate-step', 's1-order-substrate-position'],
      ),
      step(
        'module',
        '基岛优先',
        '逐基板加入基板动作，再逐基岛加入基岛动作、焊点预备动作及配方步骤。此处 StepFirst 和另一模式的实际循环顺序相同，没有由名称体现出两套不同的步骤排序。',
        ['s1-order-module-step', 's1-order-module-position'],
      ),
      step(
        'bond',
        '焊点优先',
        'StepFirst 的当前实现与基岛优先一样，先加入当前基岛各焊点的预备动作，再逐步骤展开。另一模式逐步骤处理；遇到某焊点的首个步骤时先加入该焊点预备动作，再加入该步骤的点胶或检测消息。',
        ['s1-order-bond-step', 's1-order-bond-position', 's1-position-groups'],
        [
          outcome(
            '分组不等于重排配方',
            'GetWorkBondPosition 按焊点名取组内首项；配方动作的 foreach 仍遍历 ProcessSteps，没有在这里把同名焊点的全部步骤重新排成连续分组。',
            's1-position-groups',
            's1-order-bond-position',
          ),
        ],
      ),
    ],
  ),
];
