import type { PresentationTopic } from './presentation';
import type { FlowchartCatalogEntry } from '../types';
import type { CoordinateArtifact } from './coordinateDiagrams';

// 只发布已经逐条复核的专题；全部制作范围保存在开发覆盖清单，避免空目录冒充已完成内容。
export const functionalTopics: PresentationTopic[] = [
  {
    id: 'product-coordinates',
    title: '产品层级与产品坐标',
    summary: '看清载具到焊点的层级、实例展开，以及定位结果怎样改变后续加工目标。',
    purpose: '将产品局部位置、视觉定位和工位偏移连接到同一条坐标父链。',
    conditions: ['普通矩阵与异形结构使用不同的配置，位置和加工顺序分别计算。'],
    exceptions: ['定位更新有差值限值；坐标更新、参数保存和轴到位分别判断。'],
    diagrams: ['product-coordinate-lifecycle'],
  },
];

export const functionalCatalogEntries: FlowchartCatalogEntry[] = functionalTopics.map((topic) => ({
  id: topic.diagrams[0],
  inlineTopic: topic.id,
  title: topic.title,
  type: 'architecture',
  typeLabel: '功能图谱',
  group: 'reader',
  groupLabel: '07 功能阅读',
  status: 'source-reviewed-inline',
}));

export const functionalArtifacts: Record<string, CoordinateArtifact> = {
  'product-update': {
    path: 'functional-atlas/product-update.html',
    sha256: '549a0bb2d54fe761b0d1a6f76b54b7c3666dbc6903fa88418481630ad50a0eba',
    specificationSha256: '7e3f63c9c35218f8d98a1dfa5283b9c0ae8cffcc4199a71199a0fbeac1c9f043',
  },
};
