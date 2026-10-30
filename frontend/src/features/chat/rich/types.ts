export interface SourcePointer {
  path: string;
  start_line: number;
  end_line?: number;
  version?: string;
  source_workspace_id?: string;
}

interface BlockBase {
  id: string;
}
export interface TextBlock extends BlockBase {
  type: 'text' | 'markdown';
  content: string;
}
export interface ToolCallBlock extends BlockBase {
  type: 'tool_call';
  tool: ToolEvent;
}
// 仅由前端校验器生成，模型不能借此注册组件或事件。
export interface UnsupportedBlock extends BlockBase {
  type: 'unsupported';
  original_type: string;
  raw: unknown;
  error: string;
}
export interface OverviewBlock extends BlockBase {
  type: 'overview_grid';
  title?: string;
  items: {
    id: string;
    title: string;
    description: string;
    icon?: 'code' | 'layers' | 'settings' | 'workflow';
    status?: string;
    source?: SourcePointer;
  }[];
}
export interface StepFlowBlock extends BlockBase {
  type: 'step_flow';
  title?: string;
  description?: string;
  steps: {
    id: string;
    title: string;
    description: string;
    details?: string;
    sources?: SourcePointer[];
  }[];
}
export interface SourceBlock extends BlockBase {
  type: 'source_reference';
  sources: SourcePointer[];
}
export interface CodeContentBlock extends BlockBase {
  type: 'code';
  content: string;
  language?: string;
  filename?: string;
  start_line?: number;
  source?: SourcePointer;
}
export interface TableBlock extends BlockBase {
  type: 'table';
  title?: string;
  columns: { id: string; label: string; align?: 'left' | 'right' | 'center' }[];
  rows: { id: string; cells: (string | number | null)[] }[];
}
export interface DiagramBlock extends BlockBase {
  type: 'diagram';
  title: string;
  description?: string;
  layout?: 'vertical' | 'horizontal';
  nodes: { id: string; label: string; description?: string }[];
  edges: { from: string; to: string; label?: string }[];
}
export interface CollapsibleBlock extends BlockBase {
  type: 'collapsible';
  title: string;
  default_open?: boolean;
  blocks: ContentBlock[];
}
export type ContentBlock =
  | TextBlock
  | OverviewBlock
  | StepFlowBlock
  | SourceBlock
  | CodeContentBlock
  | TableBlock
  | DiagramBlock
  | ToolCallBlock
  | UnsupportedBlock
  | CollapsibleBlock;
export interface RichDocument {
  version: 1;
  blocks: ContentBlock[];
}
import type { ToolEvent } from '../../../shared/types/api';
