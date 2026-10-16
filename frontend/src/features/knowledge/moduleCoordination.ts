export interface SignalGuide {
  title: string;
  description: string;
  chapters: string[];
}

export const coordinationSummaries: Record<string, string> = {
  'startup-workflow':
    '启动前复位交接信号，通过就绪检查后组织各生产任务。模块按各自的条件继续运行，并通过物料状态与信号协作。',
  'transport-workflow':
    '输送与上下料机构互相确认定位和推料条件，再与点胶、固晶模块交接载具。收到加工放行后，才进入下一段输送。',
  'dispense-workflow':
    'S1 根据来料状态执行点胶动作。需要分段输送时，先发出移动许可，再等待到位通知；完成加工后通知输送模块传入 S2。',
  'wafer-supply-workflow':
    '供晶模块等待取晶需求，准备好晶粒后发出取晶许可。启用翻转时，翻转台与取晶动作还需相互确认交接状态。',
  'bonding-workflow':
    'S2 等待载具传入完成，再组织取晶与固晶。使用胶盘时需要额外协调蘸胶与滑出；载具加工结束后通知输送模块放行。',
  'pickup-workflow':
    '取晶动作与供晶、翻转模块协调：先满足取晶条件，成功后通知相关模块继续准备下一次交接。',
  'bond-action-workflow':
    '固晶动作与供晶及胶盘任务协作，相关分支会发出下一颗晶粒的需求、胶盘处理完成或滑出许可。具体条件见节点说明。',
  'failure-recovery-workflow':
    '重试、忽略和停止会影响当前动作与后续交接。恢复时需要结合所属节点的物料状态和等待条件，不能把所有异常视为同一种处理。',
};

export const signalGuides: Record<string, SignalGuide> = {
  System2SingleStepSignal: {
    title: 'S2 与供晶单步继续',
    description: '单步模式下，由操作界面发出继续指令，S2 或供晶任务在对应的单步等待点继续执行。',
    chapters: ['bonding-workflow', 'wafer-supply-workflow'],
  },
  System1SingleStepSignal: {
    title: 'S1 单步继续',
    description: '单步模式下，S1 在等待点暂停，收到操作界面的继续指令后执行后续动作。',
    chapters: ['dispense-workflow'],
  },
  AllowLoaderMoveSignal: {
    title: '上料机构可以移动',
    description: '输送任务发出移动许可，上料任务收到后继续定位与上料动作。',
    chapters: ['transport-workflow'],
  },
  LoaderAllowPushSignal: {
    title: '上料机构允许推料',
    description: '上料任务发出推料许可，输送任务等待该条件后进行载具交接，并在相关位置清除许可。',
    chapters: ['transport-workflow'],
  },
  AllowDispense1TransferToDispense2Signal: {
    title: '点胶第一段可以移至第二段',
    description: 'S1 配方中的交互动作发出分段移动许可，由输送控制器等待并执行移动。',
    chapters: ['dispense-workflow', 'transport-workflow'],
  },
  AllowDispenseTransferToBondSignal: {
    title: '点胶完成，可以传入固晶区',
    description: 'S1 工作任务或输送分支发出放行通知，输送控制器或任务等待后继续传入 S2。',
    chapters: ['dispense-workflow', 'transport-workflow'],
  },
  AllowBondTransferToWaitingUnloadSignal: {
    title: '固晶完成，可以移至等待下料区',
    description: '固晶任务发出放行通知，输送控制器或任务收到后继续将载具移至等待下料区。',
    chapters: ['bonding-workflow', 'transport-workflow'],
  },
  AllowWaitingUnloadTransferToOutloadSignal: {
    title: '等待区至下料区预留通知',
    description:
      '当前记录只有复位操作，未记录发出或等待此通知的活动引用，不作为本页的实际交接条件。',
    chapters: ['transport-workflow'],
  },
  TransferToDispense1FinishedSignal: {
    title: '载具已传入点胶第一段',
    description: '输送任务发出到位通知，S1 工作任务读取其状态，作为来料判断的一部分。',
    chapters: ['dispense-workflow', 'transport-workflow'],
  },
  TransferToDispense2FinishedSignal: {
    title: '载具已传入点胶第二段',
    description: '输送任务发出分段到位通知，S1 配方交互动作等待该通知后继续。',
    chapters: ['dispense-workflow', 'transport-workflow'],
  },
  TransferToBondFinishedSignal: {
    title: '载具已传入固晶区',
    description: '输送任务发出传入完成通知，固晶任务等待该通知后进入后续加工。',
    chapters: ['bonding-workflow', 'transport-workflow'],
  },
  AllowUnloaderMoveSignal: {
    title: '下料机构可以移动',
    description: '输送任务发出移动许可，下料任务等待后继续定位与下料动作。',
    chapters: ['transport-workflow'],
  },
  UnloaderAllowPushSignal: {
    title: '下料机构允许推料',
    description: '下料任务发出推料许可，输送任务等待该条件后进行载具交接，并在相关位置清除许可。',
    chapters: ['transport-workflow'],
  },
  IsBondPickSucceedSignal: {
    title: '取晶成功，通知翻转任务',
    description: '取晶动作成功时发出通知，翻转任务等待该通知后继续相应的交接步骤。',
    chapters: ['wafer-supply-workflow', 'pickup-workflow'],
  },
  IsWaferAllowPickSignal: {
    title: '供晶已准备好，可以取晶',
    description: '供晶任务发出取晶许可，取晶、翻转或相关控制步骤等待许可后继续。',
    chapters: ['wafer-supply-workflow', 'pickup-workflow', 'bonding-workflow'],
  },
  IsBondNeedChipSignal: {
    title: '请求下一颗晶粒',
    description:
      '取晶、固晶及相关操作发出晶粒需求，供晶任务等待需求后准备晶粒，并在交接过程中清除需求状态。',
    chapters: [
      'wafer-supply-workflow',
      'pickup-workflow',
      'bonding-workflow',
      'bond-action-workflow',
    ],
  },
  IsBondNeedEjectionSignal: {
    title: '顶针需求预留通知',
    description:
      '当前数据保留信号声明，未记录活动引用。实际顶针动作请结合供晶流程中的具体节点阅读。',
    chapters: ['wafer-supply-workflow'],
  },
  IsEjectionComplete: {
    title: '顶针完成预留通知',
    description: '当前数据保留信号声明，未记录活动引用，不将该通知视为已确认的流程放行条件。',
    chapters: ['wafer-supply-workflow'],
  },
  IsLoadWaferMap: {
    title: '晶圆地图加载预留通知',
    description: '当前数据保留信号声明，未记录活动引用。地图加载行为见供晶流程中的地图与换料步骤。',
    chapters: ['wafer-supply-workflow'],
  },
  IsFlipTableAllowPickSignal: {
    title: '翻转台允许取晶',
    description: '翻转任务发出取晶许可，S2 的运行控制步骤等待该许可后继续。',
    chapters: ['wafer-supply-workflow', 'pickup-workflow', 'bonding-workflow'],
  },
  IsAllowDipFluxSignal: {
    title: '胶盘已准备好，可以蘸胶',
    description: '胶盘任务发出蘸胶许可，蘸胶动作等待该许可后继续。',
    chapters: ['bonding-workflow'],
  },
  BondDipFluxFinishSignal: {
    title: '通知胶盘相关处理完成',
    description: '固晶或上视校正分支发出处理完成通知，胶盘任务在对应等待点收到后继续。',
    chapters: ['bonding-workflow', 'bond-action-workflow'],
  },
  AllowSlideOutSignal: {
    title: '胶盘可以滑出',
    description: '固晶或上视校正分支发出滑出许可，胶盘任务等待许可后继续滑出步骤。',
    chapters: ['bonding-workflow', 'bond-action-workflow'],
  },
};
