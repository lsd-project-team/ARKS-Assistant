export interface FileEntry {
  path: string;
  name: string;
  is_dir?: boolean;
  size?: number;
}
export interface SourceFile {
  path: string;
  content: string;
  version: string;
  encoding: string;
  line_count: number;
}
export interface Selection {
  path: string;
  start_line: number;
  end_line: number;
  start_column: number;
  end_column: number;
  content: string;
  version: string;
  stale?: boolean;
}
export interface Message {
  id: string;
  role: string;
  content: string;
  selections: Selection[];
}
export interface Run {
  id: string;
  thread_id: string;
  status: string;
  answer: string;
  error: string;
  message_id: string;
}
export interface Thread {
  id: string;
  title: string;
  updated_at: string;
}
export interface Conversation extends Thread {
  messages: Message[];
  runs: Run[];
}
export interface ModelSettings {
  protocol: 'openai' | 'anthropic';
  base_url: string;
  model: string;
  api_key: string;
  has_api_key?: boolean;
  context_tokens: number;
  output_tokens: number;
  temperature: number;
  timeout_seconds: number;
  summary_model: string;
}
export interface McpServer {
  id: string;
  name: string;
  enabled: boolean;
  transport: 'streamable_http' | 'sse' | 'stdio';
  url: string;
  command: string;
  args: string[];
  headers: Record<string, string>;
  env: Record<string, string>;
}
export interface Settings {
  model: ModelSettings;
  mcp_servers: McpServer[];
  auto_memory: boolean;
  deepwiki_repo: string;
}
export interface Memory {
  name: string;
  scope: string;
  content: string;
  version: string;
  source_thread_id?: string;
  sources: { path: string; version: string; stale: boolean }[];
}
export interface ToolEvent {
  id: string;
  name: string;
  arguments?: unknown;
  result?: string;
  status?: string;
}
