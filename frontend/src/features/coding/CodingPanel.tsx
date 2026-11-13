import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../app/api/client';
import { useWorkspace } from '../../app/state/store';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { toast } from '../../shared/utils/toasts';
import { useAuth } from '../auth/AuthContext';
import { PermissionMenu } from './PermissionMenu';

interface Approval {
  id: string;
  kind: string;
  command: string;
  cwd: string;
  status: string;
  created_at: string;
  finished_at?: string | null;
  result?: { ok?: boolean; exit_code?: number | null; output?: string; error?: string } | null;
}

interface Checkpoint {
  commit: string;
  date: string;
  label: string;
}

interface CheckpointList {
  checkpoints: Checkpoint[];
  changes: { code: string; path: string }[];
  readonly?: boolean;
}

interface CodingSettings {
  approval_mode: 'allowlist' | 'confirm' | 'full';
  permission: 'read-only' | 'workspace-write' | 'full-access';
  timeout_seconds: number;
  build_command: string;
  test_command: string;
  enabled: boolean;
  root: string;
  writable: boolean;
  readonly?: boolean;
  environment?: {
    language: string;
    build_command: string;
    test_command: string;
    detected: Record<string, string>;
  };
}

interface AuditRow {
  at: string;
  action: string;
  command: string;
  exit_code: number | null;
  mode: string;
  thread_id?: string;
  run_id?: string;
  duration_ms?: number | null;
}

interface Job {
  job_id: string;
  command: string;
  status: string;
  thread_id?: string;
  exit_code?: number | null;
  started_at?: number | null;
}

const JOB_STATUS: Record<string, string> = {
  running: '运行中',
  exited: '已退出',
  stopped: '已停止',
  interrupted: '服务重启中断',
};

const POLL = { refetchInterval: 2000 } as const;

function diffPaths(diff: string) {
  const paths: string[] = [];
  for (const line of diff.split('\n')) {
    const match = /^diff --git a\/(.*) b\/(.*)$/.exec(line);
    if (match && !paths.includes(match[2])) paths.push(match[2]);
  }
  return paths;
}

function checkpointLabel(label: string) {
  if (label.startsWith('run-start-')) return `本轮开始 · ${label.slice(-8)}`;
  if (label === 'run-end') return '本轮完成';
  if (label === 'before-command') return '命令前存档';
  if (label === 'before-delete') return '删除前存档';
  if (label === 'before-move') return '移动前存档';
  if (label.startsWith('before-restore-')) return '回滚前存档';
  if (label === 'before-undo-run') return '撤销前存档';
  if (label === 'undo-run') return '撤销本轮';
  if (label.startsWith('restore-')) return `回滚 · ${label.slice(-8)}`;
  return label;
}

export function CodingPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const projectId = useWorkspace((state) => state.projectId);
  const canConfigure = useAuth().session?.user.role === 'admin';
  const [selected, setSelected] = useState('');
  const [form, setForm] = useState<Partial<CodingSettings>>({});
  const cache = useQueryClient();
  const settings = useQuery({
    queryKey: ['coding-settings', projectId],
    queryFn: () => api<CodingSettings>('/coding/settings'),
    enabled: open,
  });
  const approvals = useQuery({
    queryKey: ['coding-approvals', projectId],
    queryFn: () => api<{ approvals: Approval[] }>('/coding/approvals'),
    enabled: open,
    ...POLL,
  });
  const recent = useQuery({
    queryKey: ['coding-approvals-recent', projectId],
    queryFn: () => api<{ approvals: Approval[] }>('/coding/approvals?recent=true'),
    enabled: open,
    ...POLL,
  });
  const checkpoints = useQuery({
    queryKey: ['coding-checkpoints', projectId],
    queryFn: () => api<CheckpointList>('/coding/checkpoints'),
    enabled: open,
    ...POLL,
  });
  const audit = useQuery({
    queryKey: ['coding-audit', projectId],
    queryFn: () => api<{ rows: AuditRow[] }>('/coding/audit?limit=30'),
    enabled: open && canConfigure,
  });
  const jobs = useQuery({
    queryKey: ['coding-jobs', projectId],
    queryFn: () => api<{ jobs: Job[] }>('/coding/jobs'),
    enabled: open,
    ...POLL,
  });
  const diff = useQuery({
    queryKey: ['coding-diff', projectId, selected],
    queryFn: () => api<{ diff: string }>(`/coding/diff?commit=${encodeURIComponent(selected)}`),
    enabled: open && Boolean(selected),
  });
  const decide = useMutation({
    mutationFn: ({ id, approved }: { id: string; approved: boolean }) =>
      api(`/coding/approvals/${id}`, {
        method: 'POST',
        body: jsonBody({ approved }),
      }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['coding-approvals'] });
      void cache.invalidateQueries({ queryKey: ['coding-approvals-recent'] });
      void cache.invalidateQueries({ queryKey: ['coding-checkpoints'] });
    },
    onError: (error: Error) => toast(error.message, undefined, 'error'),
  });
  const restore = useMutation({
    mutationFn: (body: { commit: string; paths?: string[] }) =>
      api('/coding/restore', { method: 'POST', body: jsonBody(body) }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['coding-checkpoints'] });
      void cache.invalidateQueries({ queryKey: ['coding-diff'] });
      toast('已回滚到检查点');
    },
    onError: (error: Error) => toast(error.message, undefined, 'error'),
  });
  const save = useMutation({
    mutationFn: () =>
      api('/coding/settings', {
        method: 'PUT',
        body: jsonBody({
          timeout_seconds: Number(form.timeout_seconds),
          build_command: form.build_command ?? '',
          test_command: form.test_command ?? '',
          enabled: Boolean(form.enabled),
        }),
      }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['coding-settings'] });
      toast('编码设置已保存');
    },
    onError: (error: Error) => toast(error.message, undefined, 'error'),
  });

  useEffect(() => {
    if (settings.data) setForm(settings.data);
  }, [settings.data]);

  if (!open) return null;
  const readonly = checkpoints.data?.readonly ?? settings.data?.writable === false;
  const files = selected ? diffPaths(diff.data?.diff || '') : [];
  const finished = (recent.data?.approvals || []).filter((row) => row.status !== 'pending');
  return (
    <Modal open onClose={onClose} title="项目编码">
      <div className="dialog-body" style={{ minWidth: 720, maxHeight: '70vh', overflow: 'auto' }}>
        {readonly && (
          <p className="muted">
            {settings.data?.permission === 'read-only'
              ? '当前权限为「仅可查看」，写入文件、删除和写命令都会被拒绝；在聊天头部切换权限后即可修改。'
              : '当前项目是只读分析目录。启用编码后才能修改文件；也可在项目编辑中更换为其他目录。'}
          </p>
        )}
        <section>
          <h4>待确认命令</h4>
          {approvals.data?.approvals.length ? (
            approvals.data.approvals.map((row) => (
              <div key={row.id} style={{ border: '1px solid #d7e1ef', padding: 8, marginBottom: 8, borderRadius: 4 }}>
                <code>{row.command}</code>
                <span className="muted">
                  {row.kind === 'process' ? ' 后台常驻' : ' 一次性命令'} · cwd: {row.cwd}
                </span>
                <div>
                  <Button
                    className="primary"
                    disabled={decide.isPending}
                    onClick={() => decide.mutate({ id: row.id, approved: true })}
                  >
                    允许一次
                  </Button>
                  <Button
                    disabled={decide.isPending}
                    onClick={() => decide.mutate({ id: row.id, approved: false })}
                  >
                    拒绝
                  </Button>
                </div>
              </div>
            ))
          ) : (
            <p className="muted">没有待确认的命令。命令需要确认时也会直接显示在聊天里。</p>
          )}
        </section>
        {!!finished.length && (
          <section>
            <h4>最近审批</h4>
            {finished.slice(0, 5).map((row) => (
              <div key={row.id} style={{ marginBottom: 6 }}>
                <code>{row.command}</code>{' '}
                <span className="muted">
                  {row.status === 'approved'
                    ? `已批准 · 退出码 ${row.result?.exit_code ?? '—'}`
                    : row.status === 'rejected'
                      ? '已拒绝'
                      : row.status === 'expired'
                        ? '等待超时'
                        : '已取消'}
                </span>
                {row.result?.output && (
                  <pre style={{ maxHeight: 120, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                    {row.result.output.slice(-1200)}
                  </pre>
                )}
                {row.result?.error && <p className="muted">{row.result.error}</p>}
              </div>
            ))}
          </section>
        )}
        <section>
          <h4>检查点</h4>
          {checkpoints.data?.changes.length ? (
            <p className="muted">
              未提交改动：{checkpoints.data.changes.map((row) => row.path).join('、')}
            </p>
          ) : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(checkpoints.data?.checkpoints || []).map((row) => (
              <div key={row.commit} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button
                  type="button"
                  className={selected === row.commit ? 'active' : ''}
                  onClick={() => setSelected(row.commit)}
                >
                  {checkpointLabel(row.label)} · {row.date}
                </button>
                <Button
                  disabled={restore.isPending || readonly}
                  onClick={() => {
                    if (
                      window.confirm(
                        `回滚到「${checkpointLabel(row.label)}」？该检查点之后新增的文件会被删除，改动会先自动存档。`,
                      )
                    )
                      restore.mutate({ commit: row.commit });
                  }}
                >
                  回滚到此
                </Button>
              </div>
            ))}
          </div>
          {!checkpoints.data?.checkpoints.length && <p className="muted">还没有检查点。</p>}
          {selected && (
            <>
              <pre style={{ background: '#f6f9fd', border: '1px solid #d7e1ef', padding: 8, maxHeight: 320, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                {diff.data?.diff || '该检查点没有改动。'}
              </pre>
              {files.length > 0 && (
                <p className="muted">
                  单文件恢复：
                  {files.map((path) => (
                    <Button
                      key={path}
                      disabled={restore.isPending || readonly}
                      onClick={() => {
                        if (window.confirm(`把 ${path} 恢复到该检查点？`))
                          restore.mutate({ commit: selected, paths: [path] });
                      }}
                    >
                      {path}
                    </Button>
                  ))}
                </p>
              )}
            </>
          )}
        </section>
        {!!jobs.data?.jobs.length && (
          <section>
            <h4>后台任务</h4>
            <div style={{ display: 'grid', gap: 4 }}>
              {jobs.data.jobs.map((job) => (
                <div key={job.job_id} className="muted">
                  <code>{job.command}</code> · {JOB_STATUS[job.status] || job.status}
                  {job.exit_code !== null && job.exit_code !== undefined
                    ? ` · 退出码 ${job.exit_code}`
                    : ''}
                </div>
              ))}
            </div>
          </section>
        )}
        {canConfigure && !!audit.data?.rows.length && (
          <details>
            <summary>命令记录</summary>
            <div style={{ display: 'grid', gap: 4, marginTop: 8 }}>
              {audit.data.rows.map((row, index) => (
                <div key={`${row.at}:${index}`} className="muted">
                  <code>{row.command}</code> · {row.mode} · 退出码 {row.exit_code ?? '—'}
                  {row.duration_ms ? ` · ${Math.round(row.duration_ms / 100) / 10}s` : ''}
                </div>
              ))}
            </div>
          </details>
        )}
        {canConfigure && (
          <details>
            <summary>编码设置</summary>
            <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
              <div>
                <p className="muted">权限档位（切换后立即生效）</p>
                <PermissionMenu inline />
              </div>
              <label>
                命令超时（秒）
                <input
                  type="number"
                  min={10}
                  max={900}
                  value={form.timeout_seconds ?? 120}
                  onChange={(event) => setForm({ ...form, timeout_seconds: Number(event.target.value) })}
                />
              </label>
              <label>
                构建命令（可选）
                <input
                  value={form.build_command ?? ''}
                  onChange={(event) => setForm({ ...form, build_command: event.target.value })}
                />
              </label>
              <label>
                测试命令（可选）
                <input
                  value={form.test_command ?? ''}
                  onChange={(event) => setForm({ ...form, test_command: event.target.value })}
                />
              </label>
              <label>
                {form.readonly ? (
                  <input
                    type="checkbox"
                    checked={Boolean(form.enabled)}
                    onChange={(event) => setForm({ ...form, enabled: event.target.checked })}
                  />
                ) : null}
                {form.readonly
                  ? '允许在该目录编码（只读分析目录需要显式开启）'
                  : '普通项目默认可编码；这里的开关只影响只读分析目录。'}
              </label>
              <p className="muted">目录：{form.root}</p>
              {form.environment?.language && (
                <p className="muted">
                  识别到 {form.environment.language} 工程
                  {form.environment.detected.test
                    ? `，建议测试命令：${form.environment.detected.test}`
                    : ''}
                </p>
              )}
              <Button className="primary" disabled={save.isPending} onClick={() => save.mutate()}>
                保存设置
              </Button>
            </div>
          </details>
        )}
        <ErrorText
          error={
            settings.error ||
            approvals.error ||
            recent.error ||
            checkpoints.error ||
            audit.error ||
            jobs.error ||
            diff.error ||
            decide.error ||
            restore.error ||
            save.error
          }
        />
      </div>
    </Modal>
  );
}
