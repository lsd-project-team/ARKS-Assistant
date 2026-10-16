import type { SourceGuide } from '../sourceGuides';
import { waferWorkerFlows } from './waferWorker.ts';
import { waferChangeFlows } from './waferChange.ts';
import { waferPreparationFlows } from './waferPreparation.ts';
import { waferSearchFlows } from './waferSearch.ts';
import { waferFlipFlows } from './waferFlip.ts';
import { waferNineFlows } from './waferNine.ts';
import { waferMappingFlows } from './waferMapping.ts';
import { waferBoxFlows } from './waferBox.ts';
import { waferVisionFlows } from './waferVision.ts';
import { waferAccuracyFlows } from './waferAccuracy.ts';
import { waferVisionMotionFlows } from './waferVisionMotion.ts';
import { waferPrFlows } from './waferPr.ts';

export const waferGuide: SourceGuide = {
  id: 'wafer-source-review',
  topic: 'wafer',
  diagrams: [
    'wafer-supply-workflow',
    'wafer-search-gate-workflow',
    'wafer-change-retry-workflow',
    'wafer-pick-handshake-sequence',
    'wafer-vision-outcome-workflow',
  ],
  title: '供晶、换料、四种搜索与翻转交接',
  initialFlows: {
    'wafer-supply-workflow': 'wafer-demand',
    'wafer-search-gate-workflow': 'wafer-search-dispatch',
    'wafer-change-retry-workflow': 'wafer-change-retries',
    'wafer-pick-handshake-sequence': 'wafer-publish',
    'wafer-vision-outcome-workflow': 'wafer-vision-blank',
  },
  flows: [
    ...waferWorkerFlows,
    ...waferChangeFlows,
    ...waferPreparationFlows,
    ...waferSearchFlows,
    ...waferFlipFlows,
    ...waferNineFlows,
    ...waferMappingFlows,
    ...waferBoxFlows,
    ...waferVisionFlows,
    ...waferAccuracyFlows,
    ...waferVisionMotionFlows,
    ...waferPrFlows,
  ],
  boundaries: [
    {
      text: '从主项目源码展开供晶线程、自动换料、四种搜索、参考点寻路、翻转交接，以及共享视觉包装、精度重试、中心补偿与 PR 相机/已有图片入口。说明区分跳过返回、PR 枚举、机械调用、保存与展示；没有执行生产 C# 或设备动作。',
      refs: ['w-carrier', 'w-change-operation', 'w-single-finish', 'w-flip-worker-results'],
    },
    {
      text: '完整换片向导选择保存、AKRS.WM 内部寻路和文件机制、PR 算法控制器及底层运动/相机驱动仍待展开。当前有 Nine 标记未回写与图片复用、地图双点抛异常、多次定位失败 OK 读取 null 结果、部分等待无整体期限等边界；不能把整个供晶专题视为完成。',
      refs: [
        'ws-nine-ink',
        'ws-nine-struct',
        'v-pr-bitmap-dispose',
        'ws-map-search-a',
        'ws-map-find-wait',
        'v-accuracy-choice-b',
        'v-match-fail',
        'w-change-dry',
        'w-prepare-end',
        'w-flip-worker-end',
        'w-publish',
      ],
    },
  ],
};
