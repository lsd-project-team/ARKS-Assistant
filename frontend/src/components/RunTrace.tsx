import { useQuery } from '@tanstack/react-query';
import { Check, ChevronDown } from 'lucide-react';
import { api } from '../lib/api';
import type { ToolEvent } from '../types';

interface Event {
  kind: string;
  payload: ToolEvent;
}
export function RunTrace({ runId }: { runId: string }) {
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
      return { ...event.payload, ...end?.payload };
    });
  if (!tools?.length) return null;
  return (
    <details className="saved-trace">
      <summary>
        <Check size={12} />
        已调用 {tools.length} 个工具
        <ChevronDown size={12} />
      </summary>
      <div className="tool-activity">
        {tools.map((tool) => (
          <details key={tool.id}>
            <summary>
              <Check size={12} />
              {tool.name}
            </summary>
            <pre>{JSON.stringify(tool.arguments, null, 2)}</pre>
            <pre>{tool.result}</pre>
          </details>
        ))}
      </div>
    </details>
  );
}
