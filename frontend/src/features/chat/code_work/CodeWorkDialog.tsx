import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, FileCode2, Play, RotateCcw, Square } from 'lucide-react';
import { api, apiUrl, jsonBody } from '../../../app/api/client';
import { useAuth } from '../../auth/AuthContext';
import { sessionFetch } from '../../auth/session';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { CodeEnvironmentPanel } from './CodeEnvironmentPanel';
import { verificationBusy, type WorkDiff, type WorkStatus, type WorkSummary } from './types';
import { WorkspaceInfo } from './WorkspaceInfo';
import { RequirementPanel } from './RequirementPanel';
import { WorkHistory } from './WorkHistory';
import { WorkRecovery } from './WorkRecovery';
import { MergePanel } from './MergePanel';
import { ReviewDiff } from './ReviewDiff';
import { VerificationReport } from './VerificationReport';
import './code-work.css';

export function CodeWorkDialog({
  open,
  threadId,
  projectId,
  busy,
  onClose,
  onRequest,
  initialPath = '',
  initialRunId = '',
}: {
  open: boolean;
  threadId: string;
  projectId: string;
  busy: boolean;
  onClose: () => void;
  onRequest?: (request?: string) => void;
  initialPath?: string;
  initialRunId?: string;
}) {
  const admin = useAuth().session?.user.role === 'admin';
  const cache = useQueryClient();
  const key = ['code-work', projectId, threadId];
  const base = `/threads/${threadId}/code-work`;
  const query = useQuery({
    queryKey: key,
    queryFn: () => api<WorkStatus>(base, undefined, projectId),
    enabled: open && !!threadId,
    refetchInterval: open ? 2000 : false,
  });
  const [selected, setSelected] = useState(initialPath);
  const [runId, setRunId] = useState(initialRunId);
  const [tab, setTab] = useState<'changes' | 'checks' | 'history' | 'merge'>('changes');
  const [confirmRevert, setConfirmRevert] = useState<WorkDiff | null>(null);
  useEffect(() => {
    if (open) {
      setSelected(initialPath);
      setRunId(initialRunId);
      setTab('changes');
      setConfirmRevert(null);
    }
  }, [open, initialPath, initialRunId]);
  const status = query.data;
  const historical = useQuery({
    queryKey: [...key, 'turn', runId],
    queryFn: () =>
      api<WorkSummary>(`${base}/summary?run_id=${encodeURIComponent(runId)}`, undefined, projectId),
    enabled: open && !!runId,
  });
  const files = runId ? historical.data?.files : status?.files;
  const file = files?.find((item) => item.path === selected) || files?.[0];
  const diff = useQuery({
    queryKey: [...key, 'diff', file?.path, file?.version, runId],
    queryFn: () =>
      api<WorkDiff>(
        `${base}/diff?path=${encodeURIComponent(file!.path)}${runId ? `&run_id=${encodeURIComponent(runId)}` : ''}`,
        undefined,
        projectId,
      ),
    enabled: open && !!file,
  });
  const changed = () => {
    void cache.invalidateQueries({ queryKey: key });
  };
  const create = useMutation({
    mutationFn: () => api<WorkStatus>(base, { method: 'POST' }, projectId),
    onSuccess: changed,
  });
  const verify = useMutation({
    mutationFn: () => api<WorkStatus>(`${base}/verify`, { method: 'POST' }, projectId),
    onSuccess: changed,
  });
  const cancel = useMutation({
    mutationFn: () => api<WorkStatus>(`${base}/cancel`, { method: 'POST' }, projectId),
    onSuccess: changed,
  });
  const revert = useMutation({
    mutationFn: (target: WorkDiff) =>
      api<WorkStatus>(
        `${base}/revert`,
        { method: 'POST', body: jsonBody({ path: target.path, version: target.version }) },
        projectId,
      ),
    onSuccess: () => {
      setConfirmRevert(null);
      changed();
    },
  });
  const revertHunk = useMutation({
    mutationFn: (hunkId: string) =>
      api(
        `${base}/revert-hunk`,
        {
          method: 'POST',
          body: jsonBody({ path: diff.data!.path, version: diff.data!.version, hunk_id: hunkId }),
        },
        projectId,
      ),
    onSuccess: changed,
  });
  const download = useMutation({
    mutationFn: async () => {
      const response = await sessionFetch(
        apiUrl(`${base}/export?revision=${status!.revision}`, projectId),
      );
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '下载失败');
      }
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'code-changes.zip';
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  });
  const verifying = verificationBusy(status?.verification);
  const blocked = busy || verifying || !!status?.recovery?.length;
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="代码修改"
      description="每个对话使用独立副本，可查看差异、编译与运行原工程仿真。"
      className="code-work-dialog"
    >
      <div className="code-work-body">
        {admin && <CodeEnvironmentPanel />}
        {!threadId && (
          <div className="code-work-empty">
            <FileCode2 size={30} />
            <p>在聊天中描述修改要求，发送后会为这段对话准备独立副本。</p>
            {onRequest && <Button onClick={() => onRequest()}>开始描述修改要求</Button>}
          </div>
        )}
        {threadId && !status?.exists && (
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
            <WorkspaceInfo status={status} base={base} projectId={projectId} />
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
            <div className="code-work-toolbar">
              <span>
                副本版本 {status.revision} · {status.files?.length || 0} 个文件有修改
                <small className="code-work-source">
                  来源 {status.source_version?.slice(0, 12)}
                </small>
              </span>
              {onRequest && (
                <Button onClick={() => onRequest()} disabled={blocked}>
                  让 AI 修改
                </Button>
              )}
              <Button onClick={() => verify.mutate()} disabled={blocked || verify.isPending}>
                <Play size={13} />
                编译与仿真验证
              </Button>
              {verifying && (
                <Button onClick={() => cancel.mutate()} disabled={cancel.isPending}>
                  <Square size={13} />
                  停止验证
                </Button>
              )}
              <Button
                onClick={() => download.mutate()}
                disabled={!status.files?.length || download.isPending}
              >
                <Download size={13} />
                下载修改
              </Button>
            </div>
            <div className="code-work-tabs" role="tablist" aria-label="代码工作视图">
              {(
                [
                  ['changes', '改动'],
                  ['checks', '验证'],
                  ['history', '历史'],
                  ['merge', '合并'],
                ] as const
              ).map(([id, label]) => (
                <button
                  type="button"
                  key={id}
                  role="tab"
                  aria-selected={tab === id}
                  onClick={() => setTab(id)}
                >
                  {label}
                </button>
              ))}
            </div>
            {status.prepared === false && (
              <p className="muted">备份中的修改已保留。验证时将按同版本源码重新准备本机依赖。</p>
            )}
            {status.verification && (tab === 'changes' || tab === 'checks') && (
              <VerificationReport
                job={status.verification}
                current={!!status.verification_current}
                base={base}
                projectId={projectId}
              />
            )}
            <p className="muted code-work-scope">{status.scope}</p>
            {tab === 'checks' && (
              <RequirementPanel
                status={status}
                base={base}
                projectId={projectId}
                disabled={blocked}
                onChanged={changed}
                onRequest={onRequest}
              />
            )}
            {tab === 'history' && (
              <WorkHistory
                status={status}
                base={base}
                projectId={projectId}
                onSelect={(id) => {
                  setRunId(id);
                  setSelected('');
                  setTab('changes');
                }}
              />
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
              <>
                {runId && (
                  <div className="code-review-toolbar">
                    <span>历史轮次 {runId.slice(0, 8)} · 快照只读</span>
                    <Button
                      onClick={() => {
                        setRunId('');
                        setSelected('');
                      }}
                    >
                      查看全部待合入修改
                    </Button>
                  </div>
                )}
                {!!files?.length ? (
                  <div className="code-work-changes">
                    <nav aria-label="修改文件">
                      {files.map((item) => (
                        <button
                          key={item.path}
                          className={file?.path === item.path ? 'selected' : ''}
                          onClick={() => {
                            setSelected(item.path);
                            setConfirmRevert(null);
                          }}
                        >
                          <small>{item.kind === 'added' ? '新增' : '修改'}</small>
                          {item.path}
                        </button>
                      ))}
                    </nav>
                    <div className="code-work-diff">
                      <div className="code-work-file-heading">
                        <strong>{file?.path}</strong>
                        {!runId && (
                          <Button
                            disabled={!diff.data || blocked || revert.isPending}
                            onClick={() => setConfirmRevert(diff.data!)}
                          >
                            <RotateCcw size={12} />
                            撤销此文件
                          </Button>
                        )}
                      </div>
                      {confirmRevert?.path === file?.path && confirmRevert && (
                        <div className="code-revert-confirm" role="alert">
                          <span>撤销副本中此文件的全部修改？</span>
                          <Button
                            onClick={() => revert.mutate(confirmRevert)}
                            disabled={revert.isPending}
                          >
                            确认撤销
                          </Button>
                          <Button onClick={() => setConfirmRevert(null)}>保留修改</Button>
                        </div>
                      )}
                      {diff.data ? (
                        <ReviewDiff
                          diff={diff.data}
                          disabled={blocked || revertHunk.isPending}
                          onRevertHunk={!runId ? (hunk) => revertHunk.mutate(hunk.id) : undefined}
                          onReview={onRequest}
                        />
                      ) : (
                        <p className="muted">正在读取差异…</p>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="muted">
                    {runId
                      ? '此轮没有保存的代码修改。'
                      : '尚无待合入的代码修改。在聊天中描述需求，AI 会先读取副本再修改。'}
                  </p>
                )}
              </>
            )}
          </>
        )}
        <ErrorText
          error={
            query.error ||
            diff.error ||
            create.error ||
            verify.error ||
            cancel.error ||
            revert.error ||
            revertHunk.error ||
            historical.error ||
            download.error
          }
        />
      </div>
    </Modal>
  );
}
