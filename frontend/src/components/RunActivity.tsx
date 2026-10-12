import { useEffect, useState } from 'react';
import { LoaderCircle } from 'lucide-react';
import type { Run } from '../types';
import { elapsedRun, runStages } from '../lib/runFeedback';

export function RunActivity({
  run,
  stage,
  detail,
  busy,
}: {
  run: Run;
  stage?: string;
  detail?: string;
  busy: boolean;
}) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!busy) return;
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [busy, run.id]);
  return (
    <span className="run-activity" role="status">
      {busy && <LoaderCircle size={12} className="spin" />}
      <span>
        {runStages[stage || run.stage || run.status] || '正在处理'}
        {detail ? ` · ${detail}` : ''}
      </span>
      <small>{elapsedRun(run, now)}</small>
    </span>
  );
}
