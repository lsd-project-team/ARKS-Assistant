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
      text: '本次依据主项目源码展开 S2 配方控制器、BondTask、取晶、固晶、焊后检测及蘸胶/预点胶的外层入口。返回枚举、后台任务、消息 Finished、步骤提交和实物质量分别说明；没有运行生产 C#、相机、轴或真实报警界面。',
      refs: [
        's2-worker-results',
        's2-pick-success',
        's2-bond-commit',
        's2-after-post-result',
        's2-pre-caller',
      ],
    },
    {
      text: '完整运动曲线、换嘴清嘴、供晶/翻转线程、校正视觉与拾回、胶检算法及焊后数据反馈仍需继续复核。当前也存在参考点模式缺少独立 case、蘸胶空跑直接抛异常等实现限制；不能按方法名或旧图把这些环节补写为已实现，更不代表全 S2 专题完成。',
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
