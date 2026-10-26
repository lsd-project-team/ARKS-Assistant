export interface PresentationTopic {
  id: string;
  title: string;
  summary: string;
  purpose: string;
  conditions: string[];
  exceptions: string[];
  diagrams: string[];
}

// Reader-facing summaries of the existing diagrams; these describe source behavior.
export const presentationTopics: PresentationTopic[] = [
  {
    id: 'architecture',
    title: '系统架构与生产总流程',
    summary: '从全局了解软件结构、生产环节与模块协作。',
    purpose:
      '主界面提供操作入口，设备主控组织启动、停止和生产任务。输送、点胶、固晶、供晶及辅助模块通过信号协作。',
    conditions: [
      '设备配置决定输送、S1、翻转和胶盘等分支是否参与。',
      '生产任务并发运行，阅读连线时应区分调用顺序与交接关系。',
    ],
    exceptions: [
      '外部驱动和视觉运行环境的结果，需要结合现场配置确认。',
      '总体图用于建立系统模型，局部失败与恢复方式在对应专题中展开。',
    ],
    diagrams: [
      'zx2200-architecture',
      'framework-runtime-architecture',
      'automation-workflow',
      'automation-sequence',
      'showcase-v1',
    ],
  },
  {
    id: 'startup',
    title: '启动、回零与生产放行',
    summary: '了解程序启动、回零、就绪检查与生产任务启动条件。',
    purpose:
      '把程序初始化、主窗体加载与操作员生产启动分开阅读，说明系统何时进入工作状态、何时启动各任务。',
    conditions: [
      'Main 按回零配置调用 AllAxisGoHome；MainForm_Load 对在线且未回零另有门控。',
      '生产启动仍检查 AllAxisReset，再检查任务、初始化、安全门及六个运行环节。',
    ],
    exceptions: [
      '取消或检查失败会在相应入口返回。',
      '就绪检查可能已经清理文件、复位信号或请求安全位，失败返回不表示没有发生动作。',
    ],
    diagrams: ['startup-workflow', 'machine-start-readiness-workflow'],
  },
  {
    id: 'transport',
    title: '载具输送与上下料',
    summary: '看清皮带、料仓、在线模式及 S1/S2 的物料交接。',
    purpose: '按上下料配置组织进料、S1 到 S2、等待区和出口交接，使用物料状态与信号协调各任务。',
    conditions: [
      '上下料配置决定皮带、料仓和人工处理路径。',
      '各交接段需要满足对应物料占用、放行信号和传感器条件。',
    ],
    exceptions: [
      '超时、卡料和失败的 Retry 返回位置因交接段而异。',
      '部分 Ignore 分支仍推进软件状态，需要阅读局部处理说明。',
    ],
    diagrams: [
      'transport-workflow',
      'transport-pause-stop-workflow',
      'transport-start-gating-workflow',
      'bin-configuration-sequence',
      'bin-failure-handshake-sequence',
    ],
  },
  {
    id: 's1',
    title: 'S1 配方、点胶与分段交接',
    summary: '从配方动作生成到点胶、检测、分段与返工。',
    purpose: '把配方展开为动作消息，按来料和步骤状态执行点胶相关动作，并在符合条件时放行载具。',
    conditions: [
      '启用步骤、排序配置、分段模式和胶型设置影响动作列表。',
      '在线来料、预点胶、暂停及步骤状态共同影响执行。',
    ],
    exceptions: [
      'Retry、Abort、Fail 和检测结果在各层的传播方式不同。',
      '停止、重启和返工涉及消息与步骤状态保留，应按具体路径阅读。',
    ],
    diagrams: [
      'dispense-workflow',
      'epoxy-template',
      'dispense-config-consumption-workflow',
      's1-step-commit-gate-workflow',
      's1-return-gates-workflow',
      's1-segment-interaction-workflow',
      's1-defect-outcome-workflow',
      's1-rework-context-workflow',
      's1-stop-rework-recovery-workflow',
      's1-task-loop-pause-workflow',
    ],
  },
  {
    id: 'wafer',
    title: '晶圆供料、换料与翻转',
    summary: '了解搜晶模式、自动换片及供晶与取片的握手。',
    purpose: '根据供料模式和地图状态选择晶粒，处理换料、搜索与翻转，并向取片任务交接。',
    conditions: [
      'Wafer、Waffle、FlipTable 及搜索模式决定供料路径。',
      '当前物料、地图状态、停止状态与交接信号共同控制推进。',
    ],
    exceptions: [
      '搜索失败和换片重试分别返回各自处理位置。',
      '选中名称、保存对象和实际换片结果需要按对应步骤确认。',
    ],
    diagrams: [
      'wafer-supply-workflow',
      'wafer-selection-consistency-workflow',
      'wafer-search-gate-workflow',
      'wafer-vision-outcome-workflow',
      'wafer-change-retry-workflow',
      'wafer-pick-handshake-sequence',
    ],
  },
  {
    id: 's2',
    title: 'S2 调度、取晶与固晶',
    summary: '串起取晶、视觉校正、焊头动作、检测与载具完成。',
    purpose:
      '依据配方生成 S2 动作，在来料与就绪条件满足后执行取晶、校正、固晶和检测，完成后交接载具。',
    conditions: [
      '取晶方式、视觉步骤、补偿设置和检测配置决定动作路径。',
      '动作前的就绪、来料、清零与上下文初始化需要按流程顺序阅读。',
    ],
    exceptions: [
      '漏晶、回带、清零失败和预点胶重试有不同恢复入口。',
      '步骤提交、任务返回和载具送走属于不同层次的完成状态。',
    ],
    diagrams: [
      'bonding-workflow',
      'pickup-workflow',
      'bond-action-workflow',
      'postbond-feedback-workflow',
      'relative-bond-order-workflow',
      's2-action-boundary-workflow',
      's2-reset-retry-workflow',
      's2-task-entry-boundary-workflow',
      's2-predispense-retry',
    ],
  },
  {
    id: 'recovery',
    title: '暂停、重试、停止与恢复',
    summary: '分清暂停、继续、重试、忽略、停止和退出的处理方式。',
    purpose: '说明系统在暂停、失败和停止时如何处理信号、任务、载具与恢复前置条件。',
    conditions: [
      '继续运行需要满足所属入口的状态和门控条件。',
      '恢复路径受当前任务、物料和 Mapping 状态影响。',
    ],
    exceptions: [
      '普通 Stop 没有统一等待所有任务退出。',
      '急停、任务关闭、数据恢复与软件清理分别阅读，不能合并为统一恢复步骤。',
    ],
    diagrams: [
      'failure-recovery-workflow',
      'mapping-restore-workflow',
      'stop-cleanup-workflow',
      'emergency-stop-close-workflow',
      'task-closure-gate-workflow',
      'mapping-recovery-acceptance',
    ],
  },
  {
    id: 'recipe',
    title: '配方与配置生命周期',
    summary: '了解配方加载、编辑、切换、重载与步骤状态。',
    purpose: '说明产品、工艺、配置文件和视觉方案如何连接，以及修改配置后哪些入口消费这些变化。',
    conditions: [
      '当前配方标识、启用步骤、权限及界面事件影响编辑与重载。',
      '运行中重载需要结合任务状态、上下文和对象重新绑定来阅读。',
    ],
    exceptions: [
      '初始化异常与视觉块异常的出口不同。',
      '成功标记不保证所有视觉模板有效；步骤重新注入可能保留已有状态。',
    ],
    diagrams: [
      'recipe-initialization-workflow',
      'recipe-lifecycle-workflow',
      'permission-gating-workflow',
      'recipe-live-reload-workflow',
      'process-step-injection-workflow',
      'recipe-switch-sequence',
      'config-production-gates',
    ],
  },
  {
    id: 'maintenance',
    title: '手动维护、运动与标定',
    summary: '查看试胶、换吸嘴、安全移动、视觉补偿与标定。',
    purpose: '介绍生产之外的维护入口及运动、视觉和标定链路，帮助理解动作前置条件与结果保存。',
    conditions: [
      '手动入口、维护参数和当前任务状态决定允许执行的步骤。',
      '轴、相机、视觉方案及标定参数需要与现场设备一致。',
    ],
    exceptions: [
      '标定返回、参数更新和结果保存需要分别确认。',
      '运动等待和异常处理以具体轴与动作分支为准。',
    ],
    diagrams: [
      'safe-motion',
      'manual-epoxy-trial',
      'nozzle-exchange',
      'calibration-task-workflow',
      'calibration-execution-workflow',
      'bond-camera-calibration-workflow',
      'vision-motion-workflow',
      'maintenance-calibration-workflow',
      'motion-arrival-sequence',
    ],
  },
  {
    id: 'persistence',
    title: '后台监控与数据保存',
    summary: '了解后台刷新、图片、统计、Mapping 保存与退出。',
    purpose: '说明后台任务和异步保存链路，区分数据生产、排队、消费与文件或数据库写入。',
    conditions: [
      '主窗体加载门控和线程状态影响后台任务启动。',
      '数据类型、队列及消费者处理分支决定保存路径。',
    ],
    exceptions: [
      '线程故障、消费失败和进程退出需要分别阅读。',
      '进入队列、写入调用与持久化完成是不同阶段，现场数据库和保存结果仍需确认。',
    ],
    diagrams: [
      'background-lifecycle-workflow',
      'exit-save-workflow',
      'statistics-log-producer-workflow',
      'background-task-sequence',
      'async-persistence-dataflow',
      'runtime-dataflow',
    ],
  },
];

export const topicForDiagram = (id: string) =>
  presentationTopics.find((topic) => topic.diagrams.includes(id));
export { displayDiagramTitle } from './readingHelpers.ts';

export const localizedDiagramNotes: Record<string, Array<{ title: string; items: string[] }>> = {
  'automation-workflow': [
    {
      title: '配方与设备',
      items: [
        '运行输入包括配置、视觉模板、载具和晶粒。',
        'S1 点胶可重试未完成动作；失败的后续处理由任务决定。',
        'S2 按配方选择取晶、校正、固晶和检测动作。',
      ],
    },
    {
      title: '并发与连续生产',
      items: [
        '连线表达载具交接依赖，各工作任务可能同时运行。',
        '每个载具完成后，任务回到等待；暂停与停止影响各任务的协作。',
        'S1 按配置参与，供晶可能经过翻转任务。',
      ],
    },
  ],
  'automation-sequence': [
    {
      title: '本图选择的执行路径',
      items: [
        '普通输送与首次直接相机取晶，不经过翻转。',
        '并发任务通过事件同步；图中未表达固定耗时。',
      ],
    },
    { title: '阅读方式', items: ['重复动作调用已合并，重试路径见相应工作流图。'] },
  ],
};
