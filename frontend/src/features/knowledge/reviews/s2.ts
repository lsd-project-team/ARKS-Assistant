import type { SourceGuide } from '../sourceGuides';
import { s2RecipeFlows } from './s2Recipe.ts';
import { s2WorkerFlows } from './s2Worker.ts';
import { s2ContextFlows } from './s2Context.ts';
import { s2PickFlows } from './s2Pick.ts';
import { s2BondFlows } from './s2Bond.ts';
import { s2InspectionFlows } from './s2Inspection.ts';
import { s2AuxiliaryFlows } from './s2Auxiliary.ts';

export const s2Guide: SourceGuide = {
  id: 's2-source-review',
  topic: 's2',
  diagrams: [
    'bonding-workflow',
    'pickup-workflow',
    'bond-action-workflow',
    's2-task-entry-boundary-workflow',
    'relative-bond-order-workflow',
    's2-action-boundary-workflow',
  ],
  title: 'S2 配方、取晶、固晶与检测',
  initialFlows: {
    'bonding-workflow': 's2-task-entry',
    's2-task-entry-boundary-workflow': 's2-task-entry',
    'relative-bond-order-workflow': 's2-filter-relative',
    'pickup-workflow': 's2-pick-leak-options',
    'bond-action-workflow': 's2-bond-rework',
    's2-action-boundary-workflow': 's2-after-modes',
  },
  flows: [
    ...s2RecipeFlows,
    ...s2WorkerFlows,
    ...s2ContextFlows,
    ...s2PickFlows,
    ...s2BondFlows,
    ...s2InspectionFlows,
    ...s2AuxiliaryFlows,
  ],
  boundaries: [
    {
      text: '本次说明覆盖 S2 配方编排、固晶生产线程、取晶、固晶、焊后检测及蘸胶与预点胶的外层入口，依据现有流程资料整理。结果返回、后台任务、完成消息、步骤提交和实物质量分别说明；没有实际运行生产程序、相机、轴或报警界面。',
      refs: [
        's2-worker-results',
        's2-pick-success',
        's2-bond-commit',
        's2-after-post-result',
        's2-pre-caller',
      ],
    },
    {
      text: '完整运动曲线、换嘴清嘴、供晶与翻转线程、校正视觉与拾回、胶检算法及焊后数据反馈仍需继续复核。目前还存在参考点模式缺少独立入口、蘸胶空跑直接报错等限制；不能凭名称或旧图把这些环节补写为已实现，也不代表整个 S2 图谱已经完成。',
      refs: [
        's2-pick-mode',
        's2-bond-move-mode',
        's2-after-reference',
        's2-dip-dry',
        's2-after-post-result',
      ],
    },
  ],
};
