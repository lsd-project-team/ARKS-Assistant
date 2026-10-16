export interface FileEntry {
  path: string;
  name: string;
  is_dir?: boolean;
  size?: number;
}
export interface SourceFile {
  source_workspace_id?: string;
  path: string;
  content: string;
  version: string;
  encoding: string;
  line_count: number;
}
export interface Selection {
  source_workspace_id?: string;
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
  source_workspace_id?: string | null;
  id: string;
  thread_id?: string;
  role: string;
  content: string;
  selections: Selection[];
  source_options?: Partial<SourceOptions>;
  created_at?: string;
  context_active?: boolean;
  replaces_id?: string | null;
  origin_message_id?: string | null;
}
export interface Run {
  id: string;
  created_at?: string;
  updated_at?: string;
  thread_id: string;
  status: string;
  answer: string;
  error: string;
  message_id: string;
  response_message_id: string | null;
  regenerated_from: string | null;
  reset_context?: boolean;
  stage?: string;
  error_code?: string;
  started_at?: string | null;
  finished_at?: string | null;
  model_snapshot?: ModelSnapshot;
}
export interface Thread {
  owner_id?: string | null;
  project_state?: 'active' | 'archived' | null;
  project_name?: string;
  project_id?: string | null;
  id: string;
  title: string;
  created_at?: string;
  updated_at: string;
  state?: 'active' | 'archived' | 'deleted';
  pinned_order?: number | null;
  has_unread?: boolean;
  latest_status?: string | null;
  message_count?: number;
  matched_message_id?: string;
  snippet?: string;
  origin_thread_id?: string | null;
  origin_message_id?: string | null;
}
export interface Project {
  owner_id?: string | null;
  source_folders: { root: string; label: string; source_id: string }[];
  deepwiki_repo: string;
  id: string;
  name: string;
  description: string;
  source_root: string | null;
  instructions: string;
  state: 'active' | 'archived';
  pinned_order: number | null;
  created_at: string;
  updated_at: string;
  thread_count?: number;
  knowledge_available?: boolean;
  source_workspace_id?: string | null;
}
export interface ProjectMaterial {
  id: string;
  project_id: string;
  title: string;
  kind: 'document' | 'conclusion';
  source_name: string;
  content?: string;
  version: number;
  state: 'active' | 'deleted';
  origin_thread_id?: string | null;
  origin_message_id?: string | null;
  created_at: string;
  updated_at: string;
  revision_at?: string;
}
export interface ProjectList {
  projects: Project[];
  default_project_id: string | null;
  default_source?: Pick<Project, 'source_root' | 'source_folders' | 'deepwiki_repo'>;
}
export interface Conversation extends Thread {
  messages: Message[];
  runs: Run[];
  has_older?: boolean;
  has_newer?: boolean;
  before_cursor?: string | null;
  editable_message_id?: string | null;
}
export interface QueuedQuestion {
  id: string;
  thread_id: string;
  content: string;
  selections: Selection[];
  source_options?: Partial<SourceOptions>;
  created_at: string;
  updated_at: string;
}
export interface QuestionQueue {
  paused: boolean;
  items: QueuedQuestion[];
}
export interface ErrorFeedback {
  text: string;
  code?: string;
  hint?: string;
  action?: string;
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
  model_profiles: ModelProfile[];
  active_profile_id: string;
  version: string;
  mcp_servers: McpServer[];
  auto_memory: boolean;
  deepwiki_repo: string;
  analysis?: AnalysisSettings;
}
export interface AnalysisSettings {
  mode: 'auto' | 'standard' | 'deep';
  standard_calls: number;
  deep_calls: number;
  verification_reserve: number;
  long_output_tokens: number;
  max_continuations: number;
}
export interface ModelSnapshot extends Omit<ModelSettings, 'api_key' | 'has_api_key'> {
  profile_id: string;
  profile_name: string;
}
export interface CapabilityCheck {
  id: string;
  label: string;
  status: 'passed' | 'failed' | 'not_run';
  detail: string;
}
export interface ModelCapabilities {
  ok: boolean;
  connection_ok: boolean;
  model: string;
  protocol: string;
  summary_model: string;
  checked_at: string;
  checks: CapabilityCheck[];
}
export interface ModelProfile {
  id: string;
  name: string;
  config: ModelSettings;
  capabilities?: ModelCapabilities;
}
export interface McpProbeResult {
  ok: boolean;
  name: string;
  tools: { name: string; description: string; schema?: unknown }[];
}
export interface Memory {
  name: string;
  scope: string;
  content: string;
  version: string | null;
  record_version?: string;
  lifecycle?: 'valid' | 'needs_review' | 'invalid';
  saved_lifecycle?: 'valid' | 'needs_review' | 'invalid';
  deleted?: boolean;
  source_thread_id?: string;
  source_thread_status?: string;
  updated_at: number;
  partial?: boolean;
  injected_text?: string;
  inclusion_reason?: string;
  conflicts?: string[];
  sources: { path: string; version: string; stale: boolean }[];
}
export interface MemoryReview {
  name: string;
  scope: string;
  version: string;
  content: string;
  kind: 'duplicate' | 'conflict' | 'similar';
  reason: string;
}
export interface MemoryRevision {
  id: number;
  name: string;
  scope: string;
  content: string;
  version: string;
  source_thread_id?: string;
  sources: Memory['sources'];
  action: string;
  created_at: string;
}
export interface ToolEvent {
  id: string;
  name: string;
  arguments?: unknown;
  result?: string;
  status?: string;
  execution_status?: 'skipped';
  skip_reason?: string;
  cached?: boolean;
}
export interface AnalysisProgress {
  checks: { path: string; start_line: number; end_line: number; reason?: string; status: string }[];
  pending: AnalysisProgress['checks'];
  reads: SourceEvidence[];
  scope: string;
}
export interface RunCompletion {
  output: 'complete' | 'incomplete' | 'suspected_truncated';
  coverage: 'partial' | 'read' | 'unassessed';
  stage: string;
  label: string;
  remaining: number;
  continuations?: number;
  finish_reason?: string | null;
  output_limit?: number;
  scope?: string;
}
export interface ContextUsage {
  tokens: number;
  limit: number;
  complete?: boolean;
  input_limit?: number;
  output_reserved?: number;
  headroom?: number;
  basis?: 'last_request' | 'legacy_messages';
  phase?: 'before_compaction' | 'model_request';
  breakdown?: Partial<Record<'system' | 'tools' | 'memory' | 'messages' | 'selections', number>>;
}
export interface StorageStats {
  groups: Record<'databases' | 'memories' | 'archives' | 'backups' | 'recovery' | 'other', number>;
  total_bytes: number;
  disk_free_bytes: number;
  unreadable_files: number;
  revision: string | null;
  counts: Record<string, number>;
}
export interface BackupReport {
  valid: boolean;
  format_version: number;
  created_at: string | null;
  workspace_root: string | null;
  database_revision: string | null;
  counts: Record<string, number>;
  file_count: number;
  expanded_bytes: number;
  warnings: string[];
}
export interface ConversationContext extends ContextUsage {
  summary: string | null;
  version: string | null;
  updated_at: string | null;
  summarized_count: number;
  message_count: number;
}
export interface RunContext {
  references?: KnowledgeReference[];
  searches?: KnowledgeSearch[];
  memory_saves?: MemorySaveFeedback[];
  handover_materials?: KnowledgeReference[];
  completion?: RunCompletion | null;
  analysis_progress?: AnalysisProgress | null;
  analysis_plan?: { mode: string; limit: number; reserve: number; output_tokens: number } | null;
  source_review?: {
    verdict: 'passed' | 'needs_correction' | 'unknown';
    issues: { claim: string; reason: string }[];
    reason?: string;
    scope?: string;
  };
  wiki_provenance?: {
    status: string;
    note: string;
    repo: string;
    remote_indexed_commit: string | null;
    local: { commit: string | null; dirty: boolean | null };
  }[];
  knowledge_retrieval?: { titles: string[]; injected: boolean }[];
  materials?: { id: string; title: string; version: number; citation: string }[];
  debug_issues?: { id: string; title: string; version: number; citation: string }[];
  model?: ModelSnapshot;
  budget?: ContextUsage | null;
  memories: Memory[];
  recorded: boolean;
  selections: Selection[];
  tools: ToolEvent[];
  source_options?: SourceOptions | null;
  source_evidence?: SourceEvidence[];
  provider_usage?: ProviderUsage[];
  answer_validation?: {
    passed: boolean;
    reasons: string[];
    citations: { target: string; valid: boolean; reason?: string }[];
    scope: string;
  } | null;
}

export interface KnowledgeReference {
  kind: 'material' | 'handover_material' | 'debug_issue';
  id: string;
  title: string;
  version: number;
  citation: string;
  compatibility?: { status: string; missing?: string[]; reason?: string };
  resolution_status?: string;
}

export interface KnowledgeSearch {
  kind: KnowledgeReference['kind'];
  matched: number;
  excluded_conditions?: number;
  unreadable?: number;
  degraded?: boolean;
}

export interface MemorySaveFeedback {
  name: string;
  scope: string;
  status: 'saved' | 'needs_review' | 'not_saved';
  text: string;
}

export interface SourceOptions {
  use_deepwiki: boolean;
  use_knowledge: boolean;
  use_memory: boolean;
}

export interface SourcePreferences {
  source_options: SourceOptions;
  version: number;
}

export interface SourceEvidence {
  source_workspace_id?: string;
  path: string;
  version: string;
  start_line: number;
  end_line: number;
  reason: string;
  current_status: 'match' | 'changed' | 'unavailable';
}

export interface ProviderUsage {
  reported: boolean;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  purpose: string;
  duration_ms?: number;
  finish_reason?: string | null;
  stop_reason?: string | null;
}
