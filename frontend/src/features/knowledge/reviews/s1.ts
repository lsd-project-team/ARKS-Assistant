import type { SourceGuide } from '../sourceGuides';
import { s1RecipeFlows } from './s1Recipe.ts';
import { s1WorkerFlows } from './s1Worker.ts';
import { s1ActionFlows } from './s1Actions.ts';
import { s1PreDispenseFlows } from './s1PreDispense.ts';
import { s1InterpolationFlows } from './s1Interpolation.ts';
import { s1InspectionFlows } from './s1Inspection.ts';

// 说明按控制流程、生产线程和动作执行分组，软件提交与现场结果各自保持范围。
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
      text: '本次沿着点胶工作线程、S1 动作控制和点胶、检测、分段交互展开，分清动作消息完成、焊点剩余步骤和传输放行三件事。动作成功、消息完成或日志，只说明流程走到了对应位置，不证明视觉合格，也不证明物料实际到位。',
      refs: ['s1-worker-results', 's1-worker-release', 's1-point-finished', 's1-defect-results'],
    },
    {
      text: '继续展开预点胶时机、板序号、胶型预处理、插补分支、视觉采集、胶量公式和报警选择。驱动库内部执行、PR 算法内部、定位测高和物料恢复的完整入口仍待复核；本次没有运行生产程序、设备、相机或真实报警界面，不把静态阅读结论写成现场验收。',
      refs: ['s1-pre-timing', 's1-ipol-gugao', 's1-vision-service', 's1-check-hand'],
    },
  ],
};
