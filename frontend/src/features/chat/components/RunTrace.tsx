import { useProjectApi } from '../../projects/hooks/useProjectApi';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, ChevronDown, ListTree } from 'lucide-react';
import type { ToolEvent, RunCompletion, AnalysisProgress } from '../../../shared/types/api';
import { ToolActivity } from './ToolActivity';
import { toolSummary } from '../lib/runCompletion';
import { AnalysisRunDetails } from './AnalysisRunDetails';

interface Event {
  kind: string;
  payload: Record<string, unknown>;
}
export function RunTrace({
  runId,
  onContext,
}: {
  runId: string;
  onContext: (runId: string) => void;
}) {
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
  // 历史运行可能没有工具或完成事件，仍需保留本轮上下文的查看入口。
  return (
    <details className="saved-trace">
      <summary>
        <ListTree size={12} />
        <span>运行详情</span>
        {tools?.length ? toolSummary(tools) : completion?.label}
        {!!tools?.length && completion && <span>{completion.label}</span>}
        <ChevronDown size={12} />
      </summary>
      <AnalysisRunDetails completion={completion} progress={progress} />
      <ToolActivity tools={tools || []} />
      <div className="answer-actions">
        <button type="button" onClick={() => onContext(runId)}>
          <BookOpen size={14} />
          查看本轮上下文
        </button>
      </div>
    </details>
  );
}
