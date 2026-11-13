import { useProjectApi } from '../../projects/hooks/useProjectApi';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ListTree } from 'lucide-react';
import type {
  AcceptanceResult,
  AnalysisProgress,
  PlanItem,
  RunCompletion,
  ToolEvent,
  UiCheckResult,
  VerificationResult,
} from '../../../shared/types/api';
import { ToolActivity } from './ToolActivity';
import { toolSummary } from '../lib/runCompletion';
import { AnalysisRunDetails } from './AnalysisRunDetails';

interface Event {
  kind: string;
  payload: Record<string, unknown>;
}

const PLAN_STATUS_LABEL = {
  todo: '待办',
  doing: '进行中',
  done: '完成',
  blocked: '受阻',
} as const;

export function RunChecksSummary({
  plan,
  verification,
  uiCheck,
  acceptance,
}: {
  plan?: PlanItem[];
  verification?: VerificationResult;
  uiCheck?: UiCheckResult;
  acceptance?: AcceptanceResult;
}) {
  if (!plan?.length && !verification && !uiCheck && !acceptance) return null;
  return (
    <section className="run-checks" aria-label="任务计划与验收">
      <div className="run-checks-title">任务计划与验收</div>
      {!!plan?.length && (
        <ol className="run-checks-plan">
          {plan.map((item) => (
            <li key={item.id} className={`run-check-${item.status}`}>
              <span>{PLAN_STATUS_LABEL[item.status]}</span>
              {item.title}
              {item.note ? `（${item.note}）` : ''}
            </li>
          ))}
        </ol>
      )}
      <ul className="run-checks-results">
        {verification && (
          <li>
            构建/测试：{verification.ok ? '通过' : '未通过'}
            {verification.summary ? ` · ${verification.summary}` : ''}
            {verification.error ? ` · ${verification.error}` : ''}
          </li>
        )}
        {uiCheck && (
          <li>
            界面自检：{uiCheck.ok ? '通过' : '未通过'}
            {!!uiCheck.issues?.length && ` · ${uiCheck.issues.join('；')}`}
            {uiCheck.error ? ` · ${uiCheck.error}` : ''}
          </li>
        )}
        {acceptance && (
          <li>
            验收门禁：{acceptance.ok ? '通过' : '未通过'}
            {!!acceptance.missing?.length && `（${acceptance.missing.join('；')}）`}
          </li>
        )}
      </ul>
    </section>
  );
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
  const latest = (kind: string) =>
    trace.data?.slice().reverse().find((event) => event.kind === kind)?.payload;
  const completion = latest('run_completion') as RunCompletion | undefined;
  const progress = latest('analysis_progress') as AnalysisProgress | undefined;
  const plan = latest('plan')?.items as PlanItem[] | undefined;
  const verification = latest('verify') as VerificationResult | undefined;
  const uiCheck = latest('ui_check') as UiCheckResult | undefined;
  const acceptance = latest('acceptance') as AcceptanceResult | undefined;
  return (
    <RunTraceDetails
      tools={tools || []}
      completion={completion}
      progress={progress}
      plan={plan}
      verification={verification}
      uiCheck={uiCheck}
      acceptance={acceptance}
    />
  );
}

export function RunTraceDetails({
  tools,
  completion,
  progress,
  plan,
  verification,
  uiCheck,
  acceptance,
}: {
  tools: ToolEvent[];
  completion?: RunCompletion;
  progress?: AnalysisProgress;
  plan?: PlanItem[];
  verification?: VerificationResult;
  uiCheck?: UiCheckResult;
  acceptance?: AcceptanceResult;
}) {
  if (!tools.length && !completion && !progress && !plan?.length && !verification && !uiCheck)
    return null;
  return (
    // 使用原生折叠状态，工具及答案更新不改变用户手动展开或收起的选择。
    <details className="saved-trace">
      <summary>
        <ListTree size={12} />
        <span>运行详情</span>
        {tools?.length ? toolSummary(tools) : completion?.label}
        {!!tools?.length && completion && <span>{completion.label}</span>}
        <ChevronDown size={12} />
      </summary>
      <RunChecksSummary
        plan={plan}
        verification={verification}
        uiCheck={uiCheck}
        acceptance={acceptance}
      />
      <AnalysisRunDetails completion={completion} progress={progress} showSummary={false} />
      <ToolActivity tools={tools} showSummary={false} />
    </details>
  );
}
