import { useProjectApi } from '../hooks/useProjectApi';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jsonBody } from '../lib/api';
import type { ConversationContext, RunContext } from '../types';
import { useWorkspace } from '../lib/store';
import { toolLabel } from '../lib/toolLabels';
import { Modal, Button, ErrorText } from './ui';
import { UnsavedNotice } from './UnsavedNotice';
import { useUnsavedGuard } from '../hooks/useUnsavedGuard';
import { toast } from '../lib/toasts';
import { ContextBudgetDetails } from './ContextBudgetDetails';
import { RunEvidenceDetails } from './RunEvidenceDetails';
import { useSourceCitation } from '../hooks/useSourceCitation';

export function ContextDialog({
  open,
  onClose,
  threadId,
  runId,
}: {
  open: boolean;
  onClose: () => void;
  threadId: string;
  runId?: string;
}) {
  const api = useProjectApi();
  const [edit, setEdit] = useState<{ summary: string; original: string; version: string }>();
  const cache = useQueryClient();
  const openFile = useWorkspace((state) => state.openFile);
  const openCitation = useSourceCitation();
  const current = useQuery({
    queryKey: ['context', threadId],
    queryFn: () => api<ConversationContext>(`/threads/${threadId}/context`),
    enabled: open && !!threadId,
    staleTime: 0,
  });
  const sources = useQuery({
    queryKey: ['run-context', runId],
    queryFn: () => api<RunContext>(`/runs/${runId}/context`),
    enabled: open && !!runId,
    staleTime: Infinity,
  });
  const correction = useMutation({
    mutationFn: () =>
      api<ConversationContext>(`/threads/${threadId}/context`, {
        method: 'PATCH',
        body: jsonBody({ summary: edit?.summary, version: edit?.version }),
      }),
    onSuccess: (result) => {
      cache.setQueryData(['context', threadId], result);
      setEdit(undefined);
      toast('压缩摘要已更新');
    },
  });
  const guard = useUnsavedGuard(!!edit && edit.summary !== edit.original, correction.isPending);
  function close() {
    setEdit(undefined);
    correction.reset();
    onClose();
  }
  return (
    <Modal
      open={open}
      onClose={() => guard.request(close)}
      title="对话上下文"
      className="context-dialog"
      description="本轮带入的资料是记录快照；压缩摘要是当前对话后续回复使用的内容。"
    >
      <div className="dialog-body context-body">
        {runId && (
          <section>
            <h3>本轮带入的资料</h3>
            {sources.isPending && <p className="muted">正在读取记录…</p>}
            {sources.data && (
              <>
                {sources.data.model?.profile_id && (
                  <div className="run-model-record">
                    <strong>
                      {sources.data.model.profile_name} ·{' '}
                      {sources.data.model.model || '未填写模型名称'}
                    </strong>
                    <small>
                      {sources.data.model.protocol === 'anthropic'
                        ? 'Anthropic Messages'
                        : 'OpenAI Chat Completions'}{' '}
                      · {sources.data.model.base_url}
                    </small>
                    <small>
                      压缩模型：
                      {sources.data.model.summary_model || sources.data.model.model || '未配置'}
                    </small>
                  </div>
                )}
                {!sources.data.recorded && (
                  <p className="muted">未记录本轮长期记忆快照，无法追溯实际带入的记忆。</p>
                )}
                {sources.data.budget && (
                  <details>
                    <summary>
                      本轮请求预算 · 估算 {sources.data.budget.tokens.toLocaleString()} tokens
                    </summary>
                    <ContextBudgetDetails usage={sources.data.budget} snapshot />
                  </details>
                )}
                <RunEvidenceDetails
                  context={sources.data}
                  onOpen={(path, line, endLine, version) =>
                    guard.request(async () => {
                      await openCitation(path, line, endLine, version);
                      close();
                    })
                  }
                />
                {sources.data.selections.map((selection, index) => (
                  <button
                    key={index}
                    className="context-source"
                    onClick={() =>
                      guard.request(() => {
                        openFile(selection.path, selection.start_line);
                        close();
                      })
                    }
                  >
                    {selection.path} · L{selection.start_line}–{selection.end_line}
                    {selection.stale ? ' · 旧版本' : ''}
                  </button>
                ))}
                {!sources.data.references?.length &&
                  sources.data.debug_issues?.map((issue) => (
                    <button
                      key={issue.id}
                      className="context-source"
                      onClick={() =>
                        guard.request(() => {
                          window.location.hash = `handover/issues?record=${issue.id}&version=${issue.version}`;
                          close();
                        })
                      }
                    >
                      调试记录 · {issue.title} · v{issue.version}
                    </button>
                  ))}
                {sources.data.memories.map((memory) => (
                  <details className="context-memory" key={`${memory.scope}/${memory.name}`}>
                    <summary>
                      {memory.name}
                      <span>
                        {memory.scope === 'user' ? '用户偏好' : '项目记忆'}
                        {memory.partial && ' · 部分带入'}
                      </span>
                    </summary>
                    <pre>{memory.injected_text || memory.content}</pre>
                    <small>带入版本：{memory.version?.slice(0, 10)}</small>
                    {memory.inclusion_reason && <small>{memory.inclusion_reason}</small>}
                    {!!memory.conflicts?.length && (
                      <small>同字段值不同，需核对：{memory.conflicts.join('、')}</small>
                    )}
                  </details>
                ))}
                {sources.data.recorded && !sources.data.memories.length && (
                  <p className="muted">本轮未带入长期记忆。</p>
                )}
                {!!sources.data.tools.length && (
                  <p className="muted">
                    资料获取：
                    {[...new Set(sources.data.tools.map((tool) => toolLabel(tool.name)))].join(
                      '、',
                    )}
                  </p>
                )}
              </>
            )}
          </section>
        )}
        <section>
          <h3>当前压缩摘要</h3>
          <ErrorText
            error={current.error || sources.error || correction.error}
            reveal={!!correction.error}
          />
          {current.isPending && <p className="muted">正在读取上下文…</p>}
          {current.data && (
            <>
              <p className="muted">
                {current.data.complete ? '完整输入估算' : '历史消息估算'}{' '}
                {current.data.tokens.toLocaleString()} /{' '}
                {(current.data.input_limit || current.data.limit).toLocaleString()} 输入 tokens
                {current.data.summary && ` · 已归纳 ${current.data.summarized_count} 条图内消息`}
              </p>
              <ContextBudgetDetails usage={current.data} />
              {current.data.summary ? (
                edit ? (
                  <>
                    <textarea
                      aria-label="纠正压缩摘要"
                      rows={12}
                      disabled={correction.isPending}
                      value={edit.summary}
                      onChange={(event) => setEdit({ ...edit, summary: event.target.value })}
                    />
                    <div className="button-row">
                      <Button
                        className="primary"
                        disabled={correction.isPending || !edit.summary.trim()}
                        onClick={() => correction.mutate()}
                      >
                        保存纠正
                      </Button>
                      <Button
                        disabled={correction.isPending}
                        onClick={() => {
                          setEdit(undefined);
                          correction.reset();
                        }}
                      >
                        取消编辑
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <pre className="summary-content">{current.data.summary}</pre>
                    <Button
                      onClick={() => {
                        correction.reset();
                        setEdit({
                          summary: current.data!.summary!,
                          original: current.data!.summary!,
                          version: current.data!.version!,
                        });
                      }}
                    >
                      纠正摘要
                    </Button>
                  </>
                )
              ) : (
                <p className="muted">
                  尚未产生压缩摘要，当前使用原始对话。达到阈值后会自动压缩，也可在输入框输入
                  /compact 手动请求压缩。
                </p>
              )}
              {current.data.summary && (
                <p className="muted">
                  纠正后用于后续回答，原始消息继续保留。运行中禁止修改；版本变化时请先重新加载。
                </p>
              )}
            </>
          )}
          <Button
            disabled={current.isFetching || correction.isPending}
            onClick={() =>
              guard.request(() => {
                setEdit(undefined);
                correction.reset();
                void current.refetch();
              })
            }
          >
            重新加载上下文
          </Button>
          <UnsavedNotice guard={guard} />
        </section>
      </div>
    </Modal>
  );
}
