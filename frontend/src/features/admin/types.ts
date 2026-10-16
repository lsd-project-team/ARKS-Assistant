export interface ManagedAccount {
  id: string;
  username: string;
  display_name: string;
  role: 'admin' | 'user';
  enabled: boolean;
  created_at: string;
  sessions: number;
}
export interface UsageOverview {
  period: string;
  collected_since: string;
  range_start: string;
  as_of: string;
  active_users: number;
  visits: number;
  active_ms: number;
  tasks: number;
  data_total: number;
  data_breakdown: Record<string, number>;
  daily: { date: string; visits: number; tasks: number; active_ms: number }[];
}
export interface QuestionSummary {
  id: string;
  title: string;
  state: string;
  project_name: string;
  project_id: string | null;
  users: string[];
  questions: number;
  updated_at: string;
  status: string;
}
export interface RecordedMessage {
  id: string;
  role: string;
  content: string;
  created_at: string;
  actor_id: string | null;
  actor: { id?: string; display_name?: string; username?: string };
  origin_message_id?: string;
  replaces_id?: string;
  context_active: boolean;
  selections: {
    path: string;
    start_line: number;
    end_line: number;
    content: string;
    version: string;
  }[];
}
export interface RecordedRun {
  id: string;
  message_id: string;
  response_message_id: string | null;
  status: string;
  answer: string;
  error: string;
  error_code: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  resumed_from: string | null;
  regenerated_from: string | null;
  model_snapshot: Record<string, unknown>;
  evidence: { id: number; kind: string; payload: unknown }[];
}
export interface QuestionDetail {
  thread: { id: string; title: string; state: string };
  project_name: string;
  messages: RecordedMessage[];
  runs: RecordedRun[];
  total: number;
  offset: number;
  limit: number;
}
