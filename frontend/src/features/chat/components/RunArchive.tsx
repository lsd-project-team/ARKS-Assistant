import type { Run } from '../../../shared/types/api';
import { Markdown } from '../../../app/components/Markdown';
import { RunActivity } from './RunActivity';
import { RunFeedback } from './RunFeedback';
import { persistedFeedback } from '../lib/runFeedback';

export function RunArchive({
  runs,
  onSettings,
  onContext,
}: {
  runs: Run[];
  onSettings: (tab: 'model' | 'mcp') => void;
  onContext: (runId: string) => void;
}) {
  return runs.map((run) => (
    <details className="past-run" key={run.id}>
      <summary>
        未完成的回复 · <RunActivity run={run} busy={false} />
      </summary>
      {run.status !== 'cancelled' && (
        <RunFeedback
          feedback={persistedFeedback(run)}
          onSettings={onSettings}
          onContext={() => onContext(run.id)}
        />
      )}
      {run.answer && <Markdown content={run.answer} />}
      <button onClick={() => onContext(run.id)}>查看当时的上下文</button>
    </details>
  ));
}
