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
      text: '本页说明供晶线程、自动换料、四种搜索、参考点寻路、翻转交接，以及共用的视觉定位、精度重试、取晶中心补偿和 PR 相机与已有图片两个采图入口。文中区分跳过结果、PR 返回结果、机械动作请求、参数保存与界面展示；没有在实际设备程序上运行，也没有执行任何设备动作。',
      refs: ['w-carrier', 'w-change-operation', 'w-single-finish', 'w-flip-worker-results'],
    },
    {
      text: '完整换片向导中的选择与保存、地图库内部的寻路和文件保存机制、PR 算法控制器以及底层运动与相机驱动，仍待补充。当前已知的边界包括：九点搜索的墨点判定没有写回存在标记、同一张图片被多个候选复用、地图双点定位会直接中止、多次定位失败后选择确认会读到空结果，以及部分等待没有整体期限；因此不能把整张供晶图谱当作已经完成。',
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
