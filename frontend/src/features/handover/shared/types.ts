export type Kind =
  | 'source'
  | 'interview'
  | 'candidate'
  | 'task'
  | 'decision'
  | 'constraint'
  | 'baseline'
  | 'verification'
  | 'issue'
  | 'debug_issue'
  | 'plan'
  | 'framework'
  | 'training'
  | 'receipt'
  | 'package'
  | 'job';
export type Payload = Record<string, unknown>;
export interface Evidence {
  record_id: string;
  version: number;
  locator?: string;
  quote?: string;
}
export interface HandoverRecord {
  id: string;
  scope_id: 'global';
  source_project_id?: string | null;
  kind: Kind;
  title: string;
  version: number;
  state: 'draft' | 'confirmed' | 'needs_review' | 'rejected' | 'archived';
  payload: Payload;
  created_at: string;
  updated_at: string;
  created_by?: string;
  confirmation?: {
    actor?: string;
    role?: string;
    time?: string;
    opinion?: string;
    decision?: string;
  };
}
export interface Property {
  type?: string;
  enum?: string[];
  default?: unknown;
  maxLength?: number;
  $ref?: string;
  items?: Property;
  properties?: Record<string, Property>;
}
export interface Schema {
  properties: Record<string, Property>;
  $defs?: Record<string, Property>;
}
export interface Definitions {
  kinds: Record<Kind, string>;
  fields: Record<string, string>;
  states: Record<string, string>;
  values: Record<string, string>;
  schemas: Record<string, Schema>;
}
export interface Overview {
  scope_id: 'global';
  records: HandoverRecord[];
  blocks: Record<string, string[]>;
}
export interface Event {
  id: number;
  record_id: string;
  action: string;
  actor: string;
  detail: string;
  version: number;
  created_at: string;
}
export type Tab = 'overview' | 'materials' | 'tasks' | 'issues' | 'packages' | 'updates';
export const handoverScope = 'global';
export interface HandoverContext {
  scope_id: 'global';
  source_root: string;
  knowledge_available: boolean;
  source_projects: { id: string; name: string; source_available: boolean }[];
}
export const tabs: { id: Tab; label: string }[] = [
  { id: 'overview', label: '概览' },
  { id: 'materials', label: '资料' },
  { id: 'tasks', label: '任务与进度' },
  { id: 'issues', label: '调试问题' },
  { id: 'packages', label: '交接包' },
  { id: 'updates', label: '复核与追溯' },
];
export const text = (value: unknown) => (typeof value === 'string' ? value : '');
export const ids = (value: unknown) =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
export const refs = (value: unknown) => (Array.isArray(value) ? value : []) as Evidence[];
