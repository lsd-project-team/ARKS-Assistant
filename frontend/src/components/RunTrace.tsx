import { useProjectApi } from '../hooks/useProjectApi';
import { useQuery } from '@tanstack/react-query';
import { Check, ChevronDown } from 'lucide-react';
import type { ToolEvent, RunCompletion, AnalysisProgress } from '../types';
import { ToolActivity } from './ToolActivity';
import { toolSummary } from '../lib/runCompletion';
import { AnalysisRunDetails } from './AnalysisRunDetails';

interface Event {
  kind: string;
  payload: Record<string, unknown>;
}
export function RunTrace({ runId }: { runId: string }) {
  const api = useProjectApi();
  const trace = useQuery({
    queryKey: ['trace', runId],
    queryFn: () => api<Event[]>(`/runs/${runId}/trace`),
    staleTime: Infinity,
  });
  const tools = trace.data
    ?.filter((event) => event.kind === 'tool_start')
    .map((event) => {
      const end = trace.data?.find(
        (row) => row.kind === 'tool_end' && row.payload.id === event.payload.id,
      );
      return { ...event.payload, ...end?.payload } as unknown as ToolEvent;
    });
  const completion = trace.data
    ?.slice()
    .reverse()
    .find((event) => event.kind === 'run_completion')?.payload as RunCompletion | undefined;
  const progress = trace.data
    ?.slice()
    .reverse()
    .find((event) => event.kind === 'analysis_progress')?.payload as AnalysisProgress | undefined;
  if (!tools?.length && !completion) return null;
  return (
    <details className="saved-trace">
      <summary>
        <Check size={12} />
        {tools?.length ? toolSummary(tools) : completion?.label}
        {!!tools?.length && completion && <span>{completion.label}</span>}
        <ChevronDown size={12} />
      </summary>
      <AnalysisRunDetails completion={completion} progress={progress} />
      <ToolActivity tools={tools || []} />
    </details>
  );
}
