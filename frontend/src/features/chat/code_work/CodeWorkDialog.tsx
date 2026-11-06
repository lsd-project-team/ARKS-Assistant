import { useEffect, useRef, useState } from 'react';
import { useIsMutating, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileCode2 } from 'lucide-react';
import { api } from '../../../app/api/client';
import { useAuth } from '../../auth/AuthContext';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { verificationBusy, type WorkStatus, type WorkSummary } from './types';
import { RequirementPanel } from './RequirementPanel';
import { WorkRecovery } from './WorkRecovery';
import { MergePanel } from './MergePanel';
import { VerificationReport } from './VerificationReport';
import { CodeReviewToolbar } from './CodeReviewToolbar';
import { CodeReviewFile } from './CodeReviewFile';
import './code-work.css';
import './code-review-layout.css';

export function CodeWorkDialog({
  open,
  threadId,
  projectId,
  busy,
  onClose,
  onRequest,
  initialPath = '',
  initialRunId = '',
  embedded = false,
}: {
  open: boolean;
  threadId: string;
  projectId: string;
  busy: boolean;
  onClose: () => void;
  onRequest?: (request?: string) => void;
  initialPath?: string;
  initialRunId?: string;
  embedded?: boolean;
}) {
  const admin = useAuth().session?.user.role === 'admin';
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (embedded && open) panel.current?.focus({ preventScroll: true });
  }, [embedded, open]);
  const cache = useQueryClient();
  const key = ['code-work', projectId, threadId];
  const base = `/threads/${threadId}/code-work`;
  const query = useQuery({
    queryKey: key,
    queryFn: () => api<WorkStatus>(base, undefined, projectId),
    enabled: open && !!threadId,
    refetchInterval: open ? 2000 : false,
  });
  const [runId, setRunId] = useState(initialRunId);
  const [tab, setTab] = useState<'changes' | 'checks' | 'merge'>('changes');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [split, setSplit] = useState(false);
  useEffect(() => {
    if (open) {
      setRunId(initialRunId);
      setTab('changes');
      setExpanded({});
    }
  }, [open, initialPath, initialRunId, projectId, threadId]);
  const status = query.data;
  const summary = useQuery({
    queryKey: [...key, 'review-summary', status?.revision, runId],
    queryFn: () =>
      api<WorkSummary>(
        `${base}/summary${runId ? `?run_id=${encodeURIComponent(runId)}` : ''}`,
        undefined,
        projectId,
      ),
    enabled: open && !!threadId && (!!runId || !!status?.exists),
  });
  const files = runId ? summary.data?.files : status?.files;
  const versions = new Map(status?.files?.map((file) => [file.path, file.version]));
  const currentSummary =
    summary.data &&
    (runId ||
      (summary.data.revision === status?.revision &&
        summary.data.files.length === versions.size &&
        summary.data.files.every((file) => versions.get(file.path) === file.version)))
      ? summary.data
      : undefined;
  const defaultPath = files?.find((file) => file.path === initialPath)?.path || files?.[0]?.path;
  const isExpanded = (path: string) => expanded[path] ?? path === defaultPath;
  const editing = useIsMutating({ mutationKey: [...key, 'edit'] }) > 0;
  const changeScope = (id: string) => {
    setRunId(id);
    setExpanded({});
  };
  const changed = () => {
    void cache.invalidateQueries({ queryKey: key });
  };
  const create = useMutation({
    mutationFn: () => api<WorkStatus>(base, { method: 'POST' }, projectId),
    onSuccess: changed,
  });
  const verify = useMutation({
    mutationFn: () => api<WorkStatus>(`${base}/verify`, { method: 'POST' }, projectId),
    onSuccess: () => {
      changed();
      setTab('checks');
    },
  });
  const cancel = useMutation({
    mutationFn: () => api<WorkStatus>(`${base}/cancel`, { method: 'POST' }, projectId),
    onSuccess: changed,
  });
  const verifying = verificationBusy(status?.verification);
  const blocked = busy || verifying || editing || !!status?.recovery?.length;
  const body = (
    <div className="code-work-body code-work-compact">
      <CodeReviewToolbar
        title={tab === 'changes' ? undefined : { checks: '验证详情', merge: '合并' }[tab]}
        onBack={() => setTab('changes')}
        status={status}
        runId={runId}
        onScope={changeScope}
        summary={currentSummary}
        onClose={onClose}
        verifying={verifying}
        blocked={blocked}
        verifyPending={verify.isPending}
        cancelPending={cancel.isPending}
        onVerify={() => verify.mutate()}
        onCancel={() => cancel.mutate()}
        split={split}
        onToggleView={() => setSplit((current) => !current)}
        onMerge={() => setTab('merge')}
      />
      {!threadId && tab === 'changes' && (
        <div className="code-work-empty">
          <FileCode2 size={30} />
          <p>在聊天中描述修改要求，发送后会为这段对话准备独立副本。</p>
          {onRequest && <Button onClick={() => onRequest()}>开始描述修改要求</Button>}
        </div>
      )}
      {threadId && !status?.exists && tab === 'changes' && (
        <div className="code-work-empty">
          <p>
            {status?.configured
              ? '为本对话创建原工程的独立副本，之后可以让 AI 修改并验证。'
              : '请先由管理员配置仿真源码和编译环境。'}
          </p>
          <Button
            disabled={!status?.configured || create.isPending || busy}
            onClick={() => create.mutate()}
          >
            {create.isPending ? '正在复制源码与依赖…' : '创建独立副本'}
          </Button>
        </div>
      )}
      {status?.exists && (
        <>
          {!!status.recovery?.length && (
            <WorkRecovery
              items={status.recovery}
              base={base}
              projectId={projectId}
              admin={admin}
              busy={busy || verifying}
              onChanged={changed}
            />
          )}
          {status.prepared === false && tab === 'checks' && (
            <p className="muted">备份中的修改已保留。验证时将按同版本源码重新准备本机依赖。</p>
          )}
          {status.verification && tab === 'checks' && (
            <VerificationReport
              job={status.verification}
              current={!!status.verification_current}
              base={base}
              projectId={projectId}
            />
          )}
          {tab === 'checks' && (
            <>
              <p className="muted code-work-scope">{status.scope}</p>
              <RequirementPanel
                status={status}
                base={base}
                projectId={projectId}
                disabled={blocked}
                onChanged={changed}
                onRequest={onRequest}
              />
            </>
          )}
          {tab === 'merge' && (
            <MergePanel
              status={status}
              base={base}
              projectId={projectId}
              admin={admin}
              busy={blocked}
              onChanged={changed}
            />
          )}
          {tab === 'changes' && (
            <div className="code-review-files" aria-label="修改文件">
              {!!files?.length ? (
                files.map((file) => (
                  <CodeReviewFile
                    key={`${projectId}:${threadId}:${runId}:${file.path}`}
                    file={file}
                    stats={currentSummary?.files.find(
                      (item) => item.path === file.path && item.version === file.version,
                    )}
                    base={base}
                    projectId={projectId}
                    threadId={threadId}
                    runId={runId}
                    expanded={isExpanded(file.path)}
                    onToggle={() =>
                      setExpanded((current) => ({
                        ...current,
                        [file.path]: !isExpanded(file.path),
                      }))
                    }
                    focus={!!initialPath && file.path === initialPath}
                    view={{ split, wrap: false }}
                    disabled={blocked}
                    onChanged={changed}
                    onReview={onRequest}
                  />
                ))
              ) : (
                <p className="muted code-review-loading">
                  {summary.isPending
                    ? '正在读取变更…'
                    : runId
                      ? '此轮没有保存的代码修改。'
                      : '尚无待合入的代码修改。在聊天中描述需求，AI 会先读取副本再修改。'}
                </p>
              )}
            </div>
          )}
        </>
      )}
      <ErrorText
        error={query.error || create.error || verify.error || cancel.error || summary.error}
      />
    </div>
  );
  if (embedded)
    return open ? (
      <section
        ref={panel}
        id="code-work-panel"
        className="code-work-pane"
        aria-label="代码变更"
        tabIndex={-1}
        onKeyDown={(event) => {
          if (
            event.key === 'Escape' &&
            !event.defaultPrevented &&
            !(event.target as HTMLElement).closest('input, textarea, [contenteditable="true"]')
          ) {
            event.stopPropagation();
            onClose();
          }
        }}
      >
        {body}
      </section>
    ) : null;
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="代码变更"
      className="code-work-dialog"
      onEscapeKeyDown={(event) => {
        if ((event.target as HTMLElement).closest('.code-work-options-menu')) {
          event.preventDefault();
        }
      }}
    >
      {body}
    </Modal>
  );
}
