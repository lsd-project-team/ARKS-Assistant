import { useProjectApi } from '../../projects/hooks/useProjectApi';
import { useId, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jsonBody } from '../../../app/api/client';
import type { ConversationContext, RunContext } from '../../../shared/types/api';
import { useWorkspace } from '../../../app/state/store';
import { Modal, Button, ErrorText } from '../../../shared/ui/ui';
import { UnsavedNotice } from '../../../shared/ui/UnsavedNotice';
import { useUnsavedGuard } from '../../../shared/hooks/useUnsavedGuard';
import { toast } from '../../../shared/utils/toasts';
import { RunContextPanel } from './RunContextPanel';
import { ContextSummaryPanel } from './ContextSummaryPanel';
import '../styles/context-dialog.css';
import { useSourceCitation } from '../../source_reader/hooks/useSourceCitation';

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
  const panelId = useId();
  const tabList = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState<'sources' | 'summary'>(runId ? 'sources' : 'summary');
  const selected = runId ? tab : 'summary';
  const tabs: ('sources' | 'summary')[] = runId ? ['sources', 'summary'] : ['summary'];
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
      description={
        runId
          ? '查看本轮资料，管理后续回复使用的压缩摘要。'
          : '查看当前对话的上下文用量与压缩摘要。'
      }
    >
      {runId && (
        <div
          className="context-tabs"
          role="tablist"
          aria-label="上下文内容"
          ref={tabList}
          onKeyDown={(event) => {
            if (correction.isPending) return;
            if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const index =
              event.key === 'Home'
                ? 0
                : event.key === 'End'
                  ? tabs.length - 1
                  : (tabs.indexOf(selected) + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) %
                    tabs.length;
            setTab(tabs[index]);
            tabList.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[index]?.focus();
          }}
        >
          {tabs.map((item) => (
            <button
              key={item}
              type="button"
              role="tab"
              id={`${panelId}-tab-${item}`}
              aria-selected={selected === item}
              aria-controls={`${panelId}-panel-${item}`}
              disabled={correction.isPending}
              tabIndex={selected === item ? 0 : -1}
              onClick={() => setTab(item)}
            >
              {item === 'sources' ? '本轮资料' : '压缩摘要'}
            </button>
          ))}
        </div>
      )}
      <div className="dialog-body context-body">
        {runId && (
          <div
            role="tabpanel"
            tabIndex={0}
            id={`${panelId}-panel-sources`}
            aria-labelledby={`${panelId}-tab-sources`}
            hidden={selected !== 'sources'}
          >
            <ErrorText error={sources.error} />
            {sources.isPending && (
              <p className="muted" role="status">
                正在读取本轮资料…
              </p>
            )}
            {sources.data && (
              <RunContextPanel
                context={sources.data}
                onOpen={(path, line, endLine, version) =>
                  guard.request(async () => {
                    await openCitation(path, line, endLine, version);
                    close();
                  })
                }
                onSelection={(selection) =>
                  guard.request(() => {
                    openFile(selection.path, selection.start_line);
                    close();
                  })
                }
              />
            )}
          </div>
        )}
        <div
          role={runId ? 'tabpanel' : 'region'}
          tabIndex={0}
          id={`${panelId}-panel-summary`}
          aria-labelledby={runId ? `${panelId}-tab-summary` : undefined}
          aria-label={runId ? undefined : '当前对话用量与压缩摘要'}
          hidden={selected !== 'summary'}
        >
          <ErrorText error={current.error || correction.error} reveal={!!correction.error} />
          {current.isPending && (
            <p className="muted" role="status">
              正在读取上下文…
            </p>
          )}
          {current.data && (
            <ContextSummaryPanel
              context={current.data}
              edit={edit}
              saving={correction.isPending}
              onStart={() => {
                correction.reset();
                setEdit({
                  summary: current.data!.summary!,
                  original: current.data!.summary!,
                  version: current.data!.version!,
                });
              }}
              onChange={(summary) => setEdit((value) => value && { ...value, summary })}
              onSave={() => correction.mutate()}
              onCancel={() => {
                setEdit(undefined);
                correction.reset();
              }}
            />
          )}
        </div>
      </div>
      <div className="context-unsaved">
        <UnsavedNotice guard={guard} />
      </div>
      <div className="modal-footer context-footer">
        {selected === 'summary' ? (
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
            {current.isFetching ? '正在刷新…' : '刷新上下文'}
          </Button>
        ) : (
          <span>本轮资料为这次回复的记录快照</span>
        )}
        <Button disabled={correction.isPending} onClick={() => guard.request(close)}>
          关闭
        </Button>
      </div>
    </Modal>
  );
}
