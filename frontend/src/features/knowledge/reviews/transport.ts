import type { SourceGuide } from '../sourceGuides';
import { transportInputFlows } from './transportInput.ts';
import { transportHandoffFlows } from './transportHandoff.ts';
import { transportOutputFlows } from './transportOutput.ts';
import { transportLifecycleFlows } from './transportLifecycle.ts';

// 各段 Task 并行运行；节点顺序只描述所选方法内的执行路径。
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
      text: '本次说明沿 StartTask、各段 Task、传输控制器、料仓定位与 Signal 方法展开。各段由 Task.Run 分别启动，不按页面环节逐个等待结束；物料状态、传感器和许可共同决定是否执行传输。',
      refs: ['tr-entry', 'tr-bin-run', 'tr-bond-gate', 'tr-wait-gate'],
    },
    {
      text: '状态提交、Success 和完成信号表示代码走到对应分支。部分 Ignore 路径同样到达提交语句，不能据此确认物料实际到位。轴、气缸、皮带方法的内层实现和配置加载仍需继续阅读。',
      refs: ['tr-belt-dispense', 'tr-belt-commit', 'tr-bond-alarm', 'tr-bond-commit'],
    },
  ],
};
