import { Button, ErrorText } from '../components/ui';
import type { Definitions, HandoverRecord } from './types';
import { localTime } from './format';

export interface RecordRevision {
  version: number;
  state: string;
  created_at: string;
  confirmation: HandoverRecord['confirmation'];
}

export function RecordHistory({
  identifier,
  history,
  error,
  loading,
  definitions,
  onOpen,
  onRetry,
}: {
  identifier: string;
  history?: RecordRevision[];
  error?: unknown;
  loading?: boolean;
  definitions: Definitions;
  onOpen: (id: string, version?: number) => void;
  onRetry: () => void;
}) {
  return (
    <details className="handover-form-section handover-record-history">
      <summary>修改与确认历史</summary>
      <ErrorText error={error} />
      {!!error && <Button onClick={onRetry}>重试读取历史</Button>}
      {loading && <p role="status">正在读取历史…</p>}
      {history?.map((item) => (
        <div className="handover-history" key={item.version}>
          <Button onClick={() => onOpen(identifier, item.version)}>
            v{item.version} · {definitions.states[item.state] || item.state}
          </Button>
          <span>
            {item.confirmation?.actor && `${item.confirmation.actor} · `}
            {localTime(item.created_at)}
          </span>
        </div>
      ))}
    </details>
  );
}
