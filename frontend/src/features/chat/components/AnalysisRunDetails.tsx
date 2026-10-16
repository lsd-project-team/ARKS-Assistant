import type { AnalysisProgress, RunCompletion } from '../../../shared/types/api';
import { draftFor, useWorkspace } from '../../../app/state/store';
import { toast } from '../../../shared/utils/toasts';

export function AnalysisRunDetails({
  completion,
  progress,
}: {
  completion?: RunCompletion | null;
  progress?: AnalysisProgress | null;
}) {
  if (!completion && !progress) return null;
  return (
    <div className="analysis-run-details">
      {completion && <p role="status">{completion.label}</p>}
      {completion?.output !== undefined && completion.output !== 'complete' && (
        <p className="muted">
          {completion.output === 'incomplete'
            ? '回复尚未完整，已保留生成内容，可继续。'
            : '供应商未提供明确结束原因，输出达到上限，完整度待确认。'}
        </p>
      )}
      {!!completion?.continuations && (
        <p className="muted">已自动续写 {completion.continuations} 次</p>
      )}
      {!!progress?.pending.length && (
        <details>
          <summary>剩余源码核查 · {progress.pending.length} 项</summary>
          {progress.pending.map((item, index) => (
            <p key={index}>
              {item.path} · L{item.start_line}–{item.end_line}
              {item.reason && ` · ${item.reason}`}
            </p>
          ))}
        </details>
      )}
      {((completion && completion.output !== 'complete') || !!progress?.pending.length) && (
        <button
          type="button"
          onClick={() => {
            const state = useWorkspace.getState();
            const request = completion && completion.output !== 'complete' ? '继续' : '继续核查';
            state.setDraft([draftFor(state).content.trim(), request].filter(Boolean).join('\n\n'));
            toast('已填入继续请求，可在输入框发送');
          }}
        >
          准备继续
        </button>
      )}
      <p className="muted">{progress?.scope || completion?.scope}</p>
    </div>
  );
}
