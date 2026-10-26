export interface GraphNode {
  id: string;
  label: string;
  signals: string[];
  detail?: string;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  role?: string;
  variant?: string;
  fromSide?: string;
  toSide?: string;
  [key: string]: unknown;
}

export interface GraphCard {
  dot?: string;
  title: string;
  items: string[];
}

export interface FlowGraph {
  slug: string;
  title: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  cards: GraphCard[];
  validated?: boolean;
  diagnostic?: string;
  reviewDocument?: string;
}

export interface SignalReference {
  operation: string;
}

export interface SignalDefinition {
  name: string;
  resetMode?: string;
  declarationLine?: number;
  declarationPath?: string;
  references: SignalReference[];
}

export interface ResourceLink {
  href: string;
  label: string;
}

export interface FlowchartCatalogEntry {
  id: string;
  title: string;
  type: string;
  typeLabel: string;
  group: string;
  groupLabel: string;
  chapter?: number | null;
  qualityProfile?: string | null;
  nodeCount?: number | null;
  relationCount?: number | null;
  spec?: string | null;
  html?: string | null;
  visualCheck?: string | null;
  evidence?: string | null;
  specSha256?: string | null;
  htmlSha256?: string | null;
  visualCheckSha256?: string | null;
  evidenceSha256?: string | null;
  portalStatus?: string | null;
  status: string;
}

export interface FlowchartCatalog {
  schemaVersion: number;
  title: string;
  generatedOn: string;
  scope: string;
  counts: Record<string, number>;
  groups: Record<string, string>;
  entries: FlowchartCatalogEntry[];
  validation: Record<string, unknown>;
}

export interface ReviewSummary {
  nodeIds: string[];
  edgeIds: string[];
}

export interface ArchifyData {
  graphs: FlowGraph[];
  signals: Record<string, SignalDefinition>;
  reviewSummary: ReviewSummary;
  resourceLinks: ResourceLink[];
  flowchartCatalog: FlowchartCatalog;
  diagramNotes: Record<string, Array<{ title: string; items: string[] }>>;
  diagramRecords: Record<
    string,
    { htmlAvailable: boolean; reviewDocuments: string[]; visualAvailable: boolean }
  >;
  [key: string]: unknown;
}
