import { choices, flow, outcome, step } from './builders.ts';

export const s2ContextFlows = [
  flow(
    's2-action-selection',
    '消息选择与当前上下文',
    '控制器从未完成消息中查动作对象，同时更新步骤、基板、基岛和焊点缓存；查到动作对象与这些缓存完整匹配是两个不同条件。',
    ['s2-next-message', 's2-change-message', 's2-context-update'],
    [
      step(
        'next',
        '从队首找未完成消息',
        'GetNextActionNode 保存上一动作名，清 CurrentBondActionNode，再从队首查首条 !Finished 消息；全部完成返回 null。命中连续同名的两种校正动作时先抛异常，不会完成该消息。',
        ['s2-next-message'],
      ),
      step(
        'lookup',
        '按消息名称查动作',
        'ChangeNameToActionNode 先调用 ActionNodes.Find，再检查 ActionNodes 是否为 null；它没有检查查到的 actionNode 是否为 null。随后初始化上下文并返回对象；未知动作名可返回 null，使线程结束选动作循环。',
        ['s2-change-message', 's2-worker-select'],
      ),
      step(
        'step',
        '更新步骤及检测、胶型对象',
        '按步骤名查启用步骤；找到步骤才重新查 PostBondInspection 与 EpoxyApplication，未找到不会清除这两个旧缓存。这两次仓库查询发生在下面物料遍历的 try 之前。',
        ['s2-context-update'],
      ),
      step(
        'matter',
        '按工作编号定位物料',
        '基板和基岛按 WorkIndex、焊点按步骤的 BondPositionName 匹配后更新缓存，遍历前没有统一清空旧基板、基岛、焊点。未匹配可保留旧值；物料遍历异常只弹提示，此方法没有返回失败状态或 Stop。',
        ['s2-context-update'],
      ),
    ],
  ),
  choices(
    's2-rework-messages',
    '消息重做与步骤状态保留',
    '两个 SetActionNodeReWork 重载只重置精确匹配消息的 Finished。焊点步骤字典由 InjectSteps 另行维护，消息重做不能直接等同于焊点制程重做。',
    ['s2-rework-current', 's2-rework-named', 's2-inject-steps'],
    [
      step(
        'current',
        '按当前步骤匹配动作',
        '动作名、当前基板号、当前基岛号、当前步骤名同时匹配时，取首条消息改为 Finished=false。找不到直接抛 ActionNode Sort Error；空消息表也会查不到，不同于跳过重置。',
        ['s2-rework-current'],
      ),
      step(
        'named',
        '按提供的步骤名匹配',
        '元组重载使用提供的动作名和步骤名，但仍使用当前消息的基板、基岛。每项找到即改 false，后面的查找失败没有本地回滚前面已经修改的消息。',
        ['s2-rework-named'],
      ),
      step(
        'steps',
        '步骤注入只补缺失键',
        'InjectSteps 遍历载具焊点和启用步骤，同焊点名且字典中没有该步骤名时才添加 false。已有 true 或 false 均不被覆盖；两个消息重做方法未在这里同步修改步骤字典。',
        ['s2-inject-steps', 's2-rework-current', 's2-rework-named'],
        [
          outcome(
            '收尾复位的区别',
            'Finish 对所有消息改 false；它也没有在同一方法中重置焊点步骤字典。具体固晶节点何时提交步骤，仍须继续沿节点源码展开。',
            's2-controller-finish',
          ),
        ],
      ),
    ],
  ),
];
