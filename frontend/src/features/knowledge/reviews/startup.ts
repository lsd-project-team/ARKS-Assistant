import type { SourceGuide } from '../sourceGuides';
import { flow, outcome, step } from './builders.ts';

// 每条说明对应已人工阅读的源码范围；外部方法仅说明调用及返回处理，不推断设备结果。
export const startupGuide: SourceGuide = {
  id: 'startup-source-review',
  topic: 'startup',
  diagrams: ['startup-workflow', 'machine-start-readiness-workflow'],
  initialFlows: {
    startup: 'boot',
    'startup-workflow': 'boot',
    'machine-start-readiness-workflow': 'production-start',
  },
  title: '启动检查与任务放行',
  flows: [
    flow(
      'production-start',
      '生产启动',
      '从生产按钮进入 Machine.Start。下面按源码调用顺序展开；提前返回或异常会中断后续步骤。',
      [
        'ui-start',
        'prepare-reset',
        'prepare-gates',
        'prepare-motion',
        'working-state',
        'start-options',
      ],
      [
        step(
          'operator',
          '确认配方并退出单步',
          '生产按钮先禁用当前控件。按配置确认配方后，关闭手动移动面板，退出单步模式，再调用 Machine.Start。',
          ['ui-start'],
          [
            outcome(
              '取消确认',
              '配置启用配方提示时，Cancel 直接返回，不调用 Machine.Start；finally 恢复控件。',
              'ui-start',
            ),
            outcome(
              '捕获异常',
              '按钮处理中的异常进入 catch，先调用 Machine.Stop，再弹出启动失败提示；finally 恢复控件。',
              'ui-start',
            ),
          ],
        ),
        step(
          'reset',
          '清理文件并复位信号',
          'PrepareMachineReadyToStart 先按 FileSaveDue 调用 CleanFile，再复位机台信号。加密狗到期检查在这里是注释代码。',
          ['prepare-reset'],
          [
            outcome(
              '后续检查失败',
              '清理和信号复位已在前面发生，后面的 false 返回没有在此方法中撤销它们。',
              'prepare-reset',
              'prepare-gates',
            ),
          ],
        ),
        step(
          'gates',
          '检查回零、任务与初始化',
          '依次检查 AllAxisReset、任务状态、初始化、安全门和 Working 状态。回零检查在这里没有离线模式的跳过分支。',
          ['prepare-gates'],
          [
            outcome(
              '拒绝启动',
              '未回零、任务检查拒绝、初始化检查失败、已配置的安全门未关或当前已 Working，均返回 false。',
              'prepare-gates',
            ),
            outcome(
              '任务检查范围',
              'IsAllowTaskClosed 收集生产和输送 Task，只在非空任务的 Status 等于 Running 时拒绝；不能由 true 推断所有任务均已退出。',
              'running-tasks',
            ),
            outcome(
              '初始化检查',
              '检查视觉初始化标记、磁盘容量及已开启加热的预热完成状态；轴复位项还受 IsAxisResetBeforeWork 配置控制。',
              'init-state',
            ),
          ],
        ),
        step(
          'safe',
          '请求安全位置',
          '配置 S1 时调用点胶安全位；随后调用固晶安全位。顶针模块未屏蔽时，查找“顶针Z”并请求绝对移动到 0。',
          ['prepare-motion'],
          [
            outcome(
              '调用后继续',
              '这一段没有判断这些调用的返回值，随后进入运行环境检查；不能把这一节点写成“全部安全位已确认到达”。',
              'prepare-motion',
            ),
          ],
        ),
        step(
          'environment',
          '按顺序检查六个环节',
          '运行环境检查依次调用供晶、S2、S1、载具、焊点、制程检查。任一返回 false，后面的检查不再调用。',
          ['environment'],
          [
            outcome(
              '任一 false',
              'CheckOperatingEnvironment 返回 false，Prepare 返回 false，Machine.Start 在设置 Working 和分配任务之前返回。',
              'environment',
              'prepare-motion',
              'working-state',
            ),
          ],
        ),
        step(
          'working',
          '设置 Working',
          'Prepare 返回 true 后，先调用 SetState(Working)，再进入各生产模块的任务启动调用。',
          ['working-state'],
          [
            outcome(
              '状态与任务',
              '这次状态赋值没有汇总各任务入口的成功结果。',
              'working-state',
              'start-options',
            ),
          ],
        ),
        step(
          'dispatch',
          '分配生产任务',
          '按顺序调用输送、供晶、可选 S1、S2 动作初始化与固晶任务、可选胶盘、可选翻转，最后调用两种华夫盒真空检查。',
          ['working-state', 'start-options'],
          [
            outcome(
              '补偿工作模式',
              '跳过输送、供晶、S1、胶盘和翻转的 Start 调用；S2 动作初始化、固晶任务以及两种华夫盒真空检查仍在这条调用路径中。',
              'working-state',
              'start-options',
            ),
            outcome(
              '等待范围',
              'Machine.Start 中没有统一等待所有生产任务完成，也没有汇总各 Start 调用的成功结果。',
              'working-state',
              'start-options',
            ),
          ],
        ),
      ],
    ),
    flow(
      'wafer-ready',
      '供晶自检',
      '先准备状态，再按在线、示教和换料模式阅读各分支。',
      ['wafer-prefix', 'wafer-magazine', 'wafer-ready'],
      [
        step(
          'wafer-prepare',
          '设置任务模式并请求复位',
          '写入空跑、搜索记录与单次搜索标记，调用 BondZ 安全位、料盒推片气缸复位和顶针台真空关闭。这些调用发生在离线判断之前。',
          ['wafer-prefix'],
        ),
        step(
          'wafer-assistant',
          '检查料盒与示教',
          '非离线且顶针模块未屏蔽时，检查料盒配置、硬件配置及示教标记。非离线且未要求跳过示教时，还遍历顶针参数与芯片。',
          ['wafer-magazine', 'wafer-chip'],
          [
            outcome(
              '离线',
              '跳过这个在线检查块；后面的自动/手动换料处理、状态重建和就绪位置逻辑仍在方法中。',
              'wafer-magazine',
              'wafer-auto',
              'wafer-manual',
              'wafer-rebuild',
              'wafer-ready',
            ),
            outcome(
              '检查失败',
              '料盒缺失、料盒硬件缺失、示教未完成，或地图参考点不在搜晶范围，返回 false。',
              'wafer-magazine',
              'wafer-chip',
            ),
            outcome(
              '晶圆半径超限',
              'CarrierWithWaferConfig 的晶圆半径大于晶圆台半径时显示 OK/Abort；OK 继续，Abort 返回 false。',
              'wafer-chip',
            ),
          ],
        ),
        step(
          'wafer-configuration',
          '检查取片与工具组合',
          '在芯片示教检查块中核对同步顶与力控、翻转与搜晶相机、纠偏相机、提前退出力控及慢速上升组合；同时检查吸嘴和胶盘配置。',
          ['wafer-camera', 'wafer-tool'],
          [
            outcome(
              '不允许的组合',
              '力控取片与同步顶同时启用、翻转同时用 Bond 相机搜晶、纠偏相机不属于 Bond/UpLook，或提前退出力控与距离模式/慢速上升冲突，均返回 false。',
              'wafer-camera',
            ),
            outcome(
              '工具未准备',
              '吸嘴不在列表、吸嘴未配置到吸嘴架、未配置胶盘却启用蘸胶，或已配置翻转但示教未完成，返回 false。',
              'wafer-tool',
            ),
          ],
        ),
        step(
          'wafer-material',
          '处理当前料片与换料模式',
          '自动料盒模式下，当前有料且层号不大于 0 时，先请求顶针返回、扩膜下降及挡料气缸复位，再提示手动移除料片。手动模式有另一条归还料片路径。',
          ['wafer-auto', 'wafer-manual'],
          [
            outcome(
              '自动模式确认 OK',
              '将 CurrentTablet 替换为 NullTablet 并 Save；取消返回 false。前面的控制器调用已经发生。',
              'wafer-auto',
            ),
            outcome(
              '手动模式层号大于 0',
              '依次调用 PlaceWaferInSlot、晶圆夹轴安全位和料盒安全位；没有在此分支读取这些调用的返回结果。',
              'wafer-manual',
            ),
            outcome(
              '记忆无料',
              '按对应分支调用 JudgeTabletOnWaferTable(false)；两种换料模式都在处理前后调用轴安全位置检查。',
              'wafer-auto',
              'wafer-manual',
            ),
          ],
        ),
        step(
          'wafer-state',
          '按标记重建物料状态',
          '静态华夫盘配置及重建标记满足时，创建状态、将槽位标记为 Good 并复位标记。料盒重建标记满足时，更新料盒及当前晶圆/华夫盘对象，再复位标记。',
          ['wafer-rebuild'],
          [
            outcome(
              '状态含义',
              'Good 是此处写入的软件状态；这些赋值本身没有执行芯片检测，不能描述成“检测确认全部料片合格”。',
              'wafer-rebuild',
            ),
          ],
        ),
        step(
          'wafer-position',
          '请求供晶就绪位置',
          'G0 点不在碰撞圆内时，调用顶针返回及晶圆台就绪位，然后返回 true。',
          ['wafer-ready'],
          [
            outcome(
              '异常',
              '方法内抛出的异常由 catch 显示提示并返回 false；这里没有统一回滚此前状态赋值和控制器调用。',
              'wafer-prefix',
              'wafer-auto',
              'wafer-rebuild',
              'wafer-ready',
            ),
          ],
        ),
      ],
    ),
    flow(
      's2-ready',
      'S2 自检',
      '从自检开关进入，再看程式、工具配置和物料处理。',
      ['s2-open', 's2-tools', 's2-material'],
      [
        step(
          's2-switch',
          '先开真空，再看自检开关',
          '先调用 OpenBondHeadVaccum；IsActiveSelfCheck 为 false 时立即返回 true，跳过这个方法后面的检查。',
          ['s2-open'],
        ),
        step(
          's2-program',
          '检查程式和动作服务',
          '依次调用 BondProgram.SelfCheck 和 ActionNodesService.SelfCheck，任一个返回 false 就结束。',
          ['s2-open'],
        ),
        step(
          's2-teaching',
          '检查已示教参数',
          '检查 ULM、焊头点位；吸嘴架启用时检查吸嘴架点位。启用温漂或取片偏移补偿时，分别检查对应视觉点位。',
          ['s2-teach', 's2-force'],
        ),
        step(
          's2-force',
          '检查力控标定条件',
          'ForceConfig 为空时遍历芯片，只要某芯片启用力控就提示并返回 false；没有启用力控的芯片时，该空配置分支不会直接拒绝。',
          ['s2-force'],
        ),
        step(
          's2-nozzle',
          '核对吸嘴架与吸嘴记忆',
          '先调用吸嘴架硬件检查。启用工具检测时，分别读取焊头逻辑和物理吸嘴状态。',
          ['s2-tools'],
          [
            outcome('有实物、无记忆', '提示程式冲突并返回 false。', 's2-tools'),
            outcome(
              '无实物、有记忆',
              '选择 Yes 清空当前吸嘴名称后继续；选择 No 返回 false。',
              's2-tools',
            ),
          ],
        ),
        step(
          's2-material',
          '处理焊头有料与预点胶报警',
          '记忆显示焊头有料时弹出 OKCancel；OK 调用 ThrowAction。随后判断 S2 预点胶节点是否报警。',
          ['s2-material'],
          [
            outcome(
              '取消抛料',
              '这段代码只有 OK 执行抛料的分支；Cancel 没有在这里返回 false，仍进入后续预点胶报警检查。',
              's2-material',
            ),
            outcome(
              '预点胶报警',
              'IsAlarm 为 true 返回 false，否则到达方法末尾返回 true。',
              's2-material',
            ),
          ],
        ),
      ],
    ),
    flow(
      's1-ready',
      'S1 自检',
      '按点胶头、预点胶和点胶材料三个检查环节阅读。',
      ['s1-ready'],
      [
        step(
          's1-switch',
          '判断是否配置 S1',
          'IsSystem1Configrated 为 false 时返回 true，后面的 S1 检查不执行。',
          ['s1-ready'],
        ),
        step(
          's1-head',
          '调用点胶头检查',
          '调用 DispenserProgram.IsReady；返回 false 时结束本方法。',
          ['s1-ready'],
        ),
        step(
          's1-pre',
          '按模式检查预点胶',
          '预点胶模式不为 Off 时，检查预点胶板、胶型名称是否为 null，以及该名称是否存在于胶型列表。',
          ['s1-ready'],
          [
            outcome('模式为 Off', '跳过预点胶检查，但仍执行后面的点胶材料检查。', 's1-ready'),
            outcome(
              '预点胶未准备',
              '板未准备、名称为 null 或列表没有对应名称时返回 false。名称判断使用 null 比较，不是统一的空白字符串判断。',
              's1-ready',
            ),
          ],
        ),
        step(
          's1-material',
          '调用点胶材料检查',
          'EpoxyMaterialProgram.IsReady 返回 false 时拒绝；否则到达末尾返回 true。',
          ['s1-ready'],
        ),
      ],
    ),
    flow(
      'product-process',
      '载具、焊点与制程',
      '供晶、S2、S1 返回 true 后，再检查载具、焊点及 S2 制程步骤。以下只展开这些入口实际执行的检查。',
      [
        'environment',
        'product-ready',
        'bond-position-ready',
        'process-flip',
        'process-step',
        'process-function',
      ],
      [
        step(
          'product',
          '检查载具示教标记',
          'IsTransportUnitReady 读取 TransportUnitConfig.IsAssistantSucceed，未示教完成就提示并返回 false。',
          ['product-ready'],
        ),
        step(
          'bond-position',
          '遍历焊点示教标记',
          'IsBpAssistanceFinish 遍历 SingleBpPositionConfigList，只要一项未示教完成就返回 false；遍历结束返回 true。',
          ['bond-position-ready'],
          [
            outcome(
              '列表为空',
              '这个方法没有空列表拒绝分支；空列表会直接走到末尾 true，不能把 true 描述为“已有焊点”。',
              'bond-position-ready',
            ),
          ],
        ),
        step(
          'process-flip',
          '限制翻转机台的启用贴片步骤',
          '配置翻转时，统计 S2 步骤中 ComponentName 不为字符串 Null 且 IsEnable 为 true 的项；数量大于 1 时拒绝。',
          ['process-flip'],
          [
            outcome(
              '统计范围',
              '代码统计的是步骤项数量，没有对芯片名称去重；不能把提示语“一种芯片”直接等同于唯一芯片种类计数。',
              'process-flip',
            ),
          ],
        ),
        step(
          'process-target',
          '检查 S2 每个步骤的名称与焊点',
          '遍历所有 S2 步骤，检查步骤名不为空字符串、序号不为 0、焊点名不为 Null/null。普通产品还检查焊点名存在于列表。',
          ['process-step'],
          [
            outcome(
              '禁用步骤',
              '这个 foreach 没有按 IsEnable 过滤；只有前面的翻转数量统计使用启用条件。',
              'process-flip',
              'process-step',
            ),
            outcome(
              '异形产品',
              '异形分支内的焊点存在性检查被注释，不能写成“异形焊点存在性已检查”。',
              'process-step',
            ),
          ],
        ),
        step(
          'process-function',
          '检查每个步骤恰好一个功能',
          '按芯片、缺陷检测、胶型三个字段是否不等于字符串 Null 计数；0 或不是 1 都拒绝，遍历结束返回 true。',
          ['process-function'],
          [
            outcome(
              '检查范围',
              '该方法遍历的是 S2SystemProcess，没有在这里遍历 S1SystemProcess；也没有逐项确认上述功能名称在仓库中存在。',
              'process-step',
              'process-function',
            ),
          ],
        ),
      ],
    ),
    flow(
      'boot',
      '开机与主窗体',
      '先看开机回零配置，再看主窗体的加载门控。',
      ['boot-home', 'form-load-gate'],
      [
        step(
          'boot-option',
          '判断开机回零配置',
          'Main 按 IsAxisResetBeforeWork 决定是否调用 AllAxisGoHome；未启用时跳过该调用。',
          ['boot-home'],
        ),
        step(
          'boot-home',
          '调用回零后创建窗体',
          '调用回零的分支没有判断返回值。AllAxisGoHome 返回后，无论 true 或 false，Main 都继续创建 MainForm 并调用 Application.Run。',
          ['boot-home', 'home-result'],
        ),
        step(
          'boot-load',
          '主窗体检查回零门控',
          'MainForm_Load 在非离线且 AllAxisReset 为 false 时禁用主区域并立即返回；否则继续加载数据、连接仪表、选灯与启动后台。',
          ['form-load-gate'],
          [
            outcome(
              '离线加载',
              '离线可以越过这个 Load 门控；生产 Start 中对 AllAxisReset 的检查仍然存在。',
              'form-load-gate',
              'prepare-gates',
            ),
          ],
        ),
      ],
    ),
    flow(
      'home',
      '回零动作',
      '回零按确认、准备、轴复位和标记提交分段阅读。',
      ['home-confirm', 'home-prepare', 'home-result'],
      [
        step(
          'home-confirm',
          '确认回零提示',
          '配置翻转时提示焊头与翻转台干涉检查，否则提示人员离开。两条分支只有 DialogResult.OK 才继续。',
          ['home-confirm'],
          [
            outcome(
              '取消',
              '立即返回 false，尚未进入本方法后面的气缸复位和 OneKeyHome 调用。',
              'home-confirm',
            ),
          ],
        ),
        step(
          'home-prepare',
          '请求气缸复位与关闭补偿',
          '配置 S2 点胶时收回测高气缸；关闭补偿；配置顶针系统时复位推片与固定气缸；配置胶盘时调用 SlideFluxerHomeNoWait。',
          ['home-prepare'],
        ),
        step(
          'home-all-axes',
          '调用 OneKeyHome 并判断返回',
          '调用 HardwareRepositoryService.OneKeyHome；返回 false 时提示轴回零失败并返回 false。',
          ['home-result'],
        ),
        step(
          'home-success',
          '开启补偿并设置回零标记',
          'OneKeyHome 返回 true 且后续未抛异常时，调用 OpenCompensate，随后设置 AllAxisReset = true 并返回 true。',
          ['home-result'],
          [
            outcome(
              '抛出异常',
              'catch 显示异常并返回 false；本方法没有统一撤销此前气缸动作和补偿调用。',
              'home-prepare',
              'home-result',
            ),
          ],
        ),
      ],
    ),
  ],
  boundaries: [
    {
      text: '本次补充核对生产启动、回零及各自检入口的源码分支。被调用的驱动、视觉算法、全部子方法和现场动作结果仍需沿对应模块继续核对。',
      refs: ['prepare-motion', 's2-open', 'home-result'],
    },
    {
      text: '方法返回、软件状态标记及任务 Start 调用是不同的观察点；这里没有用它们替代实际生产周期完成或机械到位证据。',
      refs: ['working-state', 'start-options', 'wafer-rebuild', 'home-result'],
    },
  ],
};
