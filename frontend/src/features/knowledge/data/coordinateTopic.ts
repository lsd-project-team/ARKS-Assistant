import type { FlowchartCatalogEntry } from '../types';
import type { PresentationTopic } from './presentation';

export const coordinateTopic: PresentationTopic = {
  id: 'g0',
  title: 'G0 坐标系',
  summary: '串起设备、产品与相机坐标，理解一个点怎样转换为生产中的运动目标。',
  purpose: '以统一参考坐标连接产品位置、视觉定位和设备轴目标。',
  conditions: ['普通坐标与相机从属坐标使用不同的转换方法。'],
  exceptions: ['父级、标定文件与调用重载决定转换的实际范围。'],
  diagrams: ['g0-coordinate-system'],
};

// 图谱与说明在现有阅读页内呈现，目录入口直接进入同一个专题。
export const coordinateCatalogEntry: FlowchartCatalogEntry = {
  id: 'g0-coordinate-system',
  title: 'G0 坐标系',
  inlineTopic: 'g0',
  type: 'architecture',
  typeLabel: '功能图谱',
  group: 'reader',
  groupLabel: '07 功能阅读',
  status: 'source-reviewed-inline',
};
