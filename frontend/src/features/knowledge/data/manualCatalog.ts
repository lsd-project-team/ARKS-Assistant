import catalog from './manualCatalog.json' with { type: 'json' };
import type { FlowchartCatalogEntry } from '../types';

export interface ManualEntry {
  id: string;
  file: string;
  title: string;
  summary: string;
  detailAnchor: string;
  type: string;
  topicIds: string[];
  documents: string[];
  searchText: string;
  htmlSha256: string;
  documentHashes: Partial<Record<string, string>>;
}

export const manuals: ManualEntry[] = catalog.entries;
export const manualById = (id: string) => manuals.find((entry) => entry.id === id);
export const manualForDocument = (file: string) =>
  manuals.find((entry) => entry.documents.length === 1 && entry.documents[0] === file);
export const manualsForTopic = (id: string) =>
  manuals.filter((entry) => entry.topicIds.includes(id));
export const manualResource = (file: string) => `/archify/manuals/${encodeURIComponent(file)}`;
export const manualDocumentResource = (file: string) =>
  `/archify/manuals/docs/${encodeURIComponent(file)}`;

export const manualCatalogEntries: FlowchartCatalogEntry[] = manuals.map((entry) => ({
  id: entry.id,
  title: entry.title,
  type: entry.type,
  typeLabel:
    entry.type === 'sequence' ? '时序图' : entry.type === 'lifecycle' ? '状态图' : '架构图',
  group: 'manuals',
  groupLabel: '模块图解与详细说明',
  html: `docs/archify/manuals/${entry.file}`,
  htmlSha256: entry.htmlSha256,
  status: 'available',
}));

export const manualRecords = Object.fromEntries(
  manuals.map((entry) => [
    entry.id,
    {
      htmlAvailable: true,
      reviewDocuments: [],
      visualAvailable: false,
    },
  ]),
);

export const manualReadings = Object.fromEntries(
  manuals.map((entry) => [
    entry.id,
    {
      title: entry.title,
      summary: entry.summary,
      condition: '按所属业务图谱阅读具体入口、配置与执行分支。',
      exception: '图解概括主干，详细说明保留各分支的处理条件与原有风险记录。',
    },
  ]),
);
