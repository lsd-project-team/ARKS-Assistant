import type { SourceGuide } from '../sourceGuides';
import { s1RecipeFlows } from './s1Recipe.ts';
import { s1WorkerFlows } from './s1Worker.ts';
import { s1ActionFlows } from './s1Actions.ts';
import { s1PreDispenseFlows } from './s1PreDispense.ts';
import { s1InterpolationFlows } from './s1Interpolation.ts';
import { s1InspectionFlows } from './s1Inspection.ts';

// 说明分别跟随控制器、线程和动作方法；软件提交与现场结果保持各自范围。
export const s1Guide: SourceGuide = {
  id: 's1-source-review',
  topic: 's1',
  diagrams: [
    'dispense-workflow',
    's1-step-commit-gate-workflow',
    's1-return-gates-workflow',
    's1-segment-interaction-workflow',
    's1-defect-outcome-workflow',
    's1-rework-context-workflow',
  ],
  title: 'S1 配方、点胶、检测与分段的实际分支',
  initialFlows: {
    's1-step-commit-gate-workflow': 's1-dispense-commit',
    's1-return-gates-workflow': 's1-action-selection',
    's1-segment-interaction-workflow': 's1-segment-handshake',
    's1-defect-outcome-workflow': 's1-defect-result',
    's1-rework-context-workflow': 's1-rework-state',
  },
  flows: [
    ...s1RecipeFlows,
    ...s1WorkerFlows,
    ...s1ActionFlows,
    ...s1PreDispenseFlows,
    ...s1InterpolationFlows,
    ...s1InspectionFlows,
  ],
  boundaries: [
    {
      text: '本次沿 DispenseWorkTask、S1ActionNodeController、点胶/检测/交互节点和步骤字典展开，分清消息 Finished、焊点 S1RemainingSteps 与传输许可。Success、消息完成或日志只证明走到相应代码，不证明视觉合格或物料实际到位。',
      refs: ['s1-worker-results', 's1-worker-release', 's1-point-finished', 's1-defect-results'],
    },
    {
      text: '继续展开预点胶时机、板索引、胶型预处理、插补分支、视觉采集、胶量公式及报警选择。驱动库内部执行、PR 算法内部、定位测高和物料恢复完整入口仍待复核；本次没有运行生产 C#、设备、相机或真实报警界面，不把静态源码路径写成现场验收。',
      refs: ['s1-pre-timing', 's1-ipol-gugao', 's1-vision-service', 's1-check-hand'],
    },
  ],
};
