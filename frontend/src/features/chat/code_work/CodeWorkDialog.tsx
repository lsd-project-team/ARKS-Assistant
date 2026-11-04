import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, FileCode2, Play, RotateCcw, Square } from 'lucide-react';
import { api, apiUrl, jsonBody } from '../../../app/api/client';
import { useAuth } from '../../auth/AuthContext';
import { sessionFetch } from '../../auth/session';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { CodeEnvironmentPanel } from './CodeEnvironmentPanel';
import { verificationBusy, verificationLabels, type WorkDiff, type WorkStatus } from './types';
import './code-work.css';

export function CodeWorkDialog({
  open,
  threadId,
  projectId,
  busy,
  onClose,
  onRequest,
}: {
  open: boolean;
  threadId: string;
  projectId: string;
  busy: boolean;
  onClose: () => void;
  onRequest: () => void;
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
  const [selected, setSelected] = useState('');
  const [confirmRevert, setConfirmRevert] = useState<WorkDiff | null>(null);
  const status = query.data;
  const file = status?.files?.find((item) => item.path === selected) || status?.files?.[0];
  const diff = useQuery({
    queryKey: [...key, 'diff', file?.path, file?.version],
    queryFn: () =>
      api<WorkDiff>(`${base}/diff?path=${encodeURIComponent(file!.path)}`, undefined, projectId),
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
            <Button onClick={onRequest}>开始描述修改要求</Button>
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
            <div className="code-work-toolbar">
              <span>
                副本版本 {status.revision} · {status.files?.length || 0} 个文件有修改
                <small className="code-work-source">
                  来源 {status.source_version?.slice(0, 12)}
                </small>
              </span>
              <Button onClick={onRequest} disabled={verifying || busy}>
                让 AI 修改
              </Button>
              <Button
                onClick={() => verify.mutate()}
                disabled={verifying || verify.isPending || busy}
              >
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
            {status.prepared === false && (
              <p className="muted">备份中的修改已保留。验证时将按同版本源码重新准备本机依赖。</p>
            )}
            {status.verification && (
              <div
                className="code-verification"
                data-status={status.verification_current ? status.verification.status : 'stale'}
                role="status"
              >
                <strong>
                  {status.verification_current
                    ? verificationLabels[status.verification.status]
                    : '代码已修改，需重新验证'}
                </strong>
                <span>验证版本 {status.verification.revision}</span>
                {status.verification.error && (
                  <p className="error-text">{status.verification.error}</p>
                )}
                {status.verification.steps.map((step, index) => (
                  <details key={`${status.verification!.id}:${index}`}>
                    <summary>
                      {step.name} ·{' '}
                      {step.status === 'passed'
                        ? '通过'
                        : step.status === 'failed'
                          ? '未通过'
                          : step.status === 'cancelled'
                            ? '已停止'
                            : '进行中'}
                      {step.checks ? `（${step.checks} 项）` : ''}
                    </summary>
                    <pre>{step.log || '执行中，完成后显示日志。'}</pre>
                  </details>
                ))}
              </div>
            )}
            <p className="muted code-work-scope">{status.scope}</p>
            {!!status.files?.length ? (
              <div className="code-work-changes">
                <nav aria-label="修改文件">
                  {status.files.map((item) => (
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
                    <Button
                      disabled={!diff.data || verifying || busy || revert.isPending}
                      onClick={() => setConfirmRevert(diff.data!)}
                    >
                      <RotateCcw size={12} />
                      撤销此文件
                    </Button>
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
                  <pre aria-label="代码差异">
                    {diff.data?.diff.split('\n').map((line, index) => (
                      <span
                        key={index}
                        className={
                          line.startsWith('+')
                            ? 'diff-add'
                            : line.startsWith('-')
                              ? 'diff-remove'
                              : line.startsWith('@@')
                                ? 'diff-context'
                                : ''
                        }
                      >
                        {line}
                        {'\n'}
                      </span>
                    )) || '正在读取差异…'}
                  </pre>
                </div>
              </div>
            ) : (
              <p className="muted">尚无代码修改。在聊天中描述需求，AI 会先读取副本再修改。</p>
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
            download.error
          }
        />
      </div>
    </Modal>
  );
}
