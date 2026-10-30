import { useProjectApi } from '../../projects/hooks/useProjectApi';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ChevronDown, ListTree } from 'lucide-react';
import type {
  ToolEvent,
  RunCompletion,
  AnalysisProgress,
  RunContext,
} from '../../../shared/types/api';
import { ToolActivity } from './ToolActivity';
import { toolSummary } from '../lib/runCompletion';
import { AnalysisRunDetails } from './AnalysisRunDetails';
import { RunTraceSummary } from './RunTraceSummary';
import { useSourceCitation } from '../../source_reader/hooks/useSourceCitation';
import { ErrorText } from '../../../shared/ui/ui';
import '../styles/context-dialog.css';

interface Event {
  kind: string;
  payload: Record<string, unknown>;
}
export function RunTrace({ runId }: { runId: string }) {
  const api = useProjectApi();
  const [expanded, setExpanded] = useState(false);
  const openSource = useSourceCitation();
  const context = useQuery({
    queryKey: ['run-context', runId],
    queryFn: () => api<RunContext>(`/runs/${runId}/context`),
    enabled: expanded,
    staleTime: 1000,
    refetchInterval: (query) =>
      ['queued', 'running', 'cancelling'].includes(query.state.data?.trace?.status || '')
        ? 1000
        : false,
  });
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
  if (!trace.data?.length && !completion && !progress) return null;
  return (
    <details className="saved-trace" onToggle={(event) => setExpanded(event.currentTarget.open)}>
      <summary>
        <ListTree size={12} />
        <span>运行详情</span>
        {tools?.length ? toolSummary(tools) : completion?.label}
        {!!tools?.length && completion && <span>{completion.label}</span>}
        <ChevronDown size={12} />
      </summary>
      {expanded && context.isPending && <p role="status">正在读取本轮依据与耗时…</p>}
      <ErrorText error={context.error} />
      {context.data && <RunTraceSummary context={context.data} onOpen={openSource} />}
      <AnalysisRunDetails completion={completion} progress={progress} showSummary={false} />
      <ToolActivity tools={tools || []} showSummary={false} />
    </details>
  );
}
