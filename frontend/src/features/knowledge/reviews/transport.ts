import type { SourceGuide } from '../sourceGuides';
import { transportInputFlows } from './transportInput.ts';
import { transportHandoffFlows } from './transportHandoff.ts';
import { transportOutputFlows } from './transportOutput.ts';
import { transportLifecycleFlows } from './transportLifecycle.ts';

// 各段任务并行运行；节点顺序只说明选定范围内的执行先后。
export const transportGuide: SourceGuide = {
  id: 'transport-source-review',
  topic: 'transport',
  diagrams: [
    'transport-workflow',
    'transport-pause-stop-workflow',
    'transport-start-gating-workflow',
    'bin-failure-handshake-sequence',
  ],
  title: '载具输送、料仓与交接的实际分支',
  flows: [
    ...transportInputFlows,
    ...transportHandoffFlows,
    ...transportOutputFlows,
    ...transportLifecycleFlows,
  ],
  boundaries: [
    {
      text: '本次说明沿输送启动入口、各段任务、传输控制器、料仓定位和信号处理展开。各段任务分别启动，不会按页面上的环节逐个等待结束；物料状态、传感器和许可共同决定是否执行传输。',
      refs: ['tr-entry', 'tr-bin-run', 'tr-bond-gate', 'tr-wait-gate'],
    },
    {
      text: '状态提交、成功结果和完成信号只表示流程走到了对应分支。部分选择忽略的路径同样会到达提交步骤，不能据此确认物料实际到位。轴、气缸和皮带动作的内部实现以及配置加载，仍需继续核对。',
      refs: ['tr-belt-dispense', 'tr-belt-commit', 'tr-bond-alarm', 'tr-bond-commit'],
    },
  ],
};
