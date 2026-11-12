import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../app/api/client';
import { useWorkspace } from '../../app/state/store';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { toast } from '../../shared/utils/toasts';

interface Approval {
  id: string;
  command: string;
  cwd: string;
  status: string;
  created_at: string;
}

interface Checkpoint {
  commit: string;
  date: string;
  label: string;
}

interface CheckpointList {
  checkpoints: Checkpoint[];
  changes: { code: string; path: string }[];
}

const POLL = { refetchInterval: 2000 } as const;

export function CodingPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const projectId = useWorkspace((state) => state.projectId);
  const [selected, setSelected] = useState('');
  const cache = useQueryClient();
  const approvals = useQuery({
    queryKey: ['coding-approvals', projectId],
    queryFn: () => api<{ approvals: Approval[] }>('/coding/approvals'),
    enabled: open,
    ...POLL,
  });
  const checkpoints = useQuery({
    queryKey: ['coding-checkpoints', projectId],
    queryFn: () => api<CheckpointList>('/coding/checkpoints'),
    enabled: open,
    ...POLL,
  });
  const diff = useQuery({
    queryKey: ['coding-diff', projectId, selected],
    queryFn: () =>
      api<{ diff: string }>(`/coding/diff?base=${encodeURIComponent(selected)}`),
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
      void cache.invalidateQueries({ queryKey: ['coding-checkpoints'] });
    },
    onError: (error: Error) => toast(error.message, undefined, 'error'),
  });
  const restore = useMutation({
    mutationFn: (commit: string) =>
      api('/coding/restore', { method: 'POST', body: jsonBody({ commit }) }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['coding-checkpoints'] });
      void cache.invalidateQueries({ queryKey: ['coding-diff'] });
      toast('已回滚到检查点');
    },
    onError: (error: Error) => toast(error.message, undefined, 'error'),
  });

  if (!open) return null;
  return (
    <Modal open onClose={onClose} title="项目编码">
      <div className="dialog-body" style={{ minWidth: 720, maxHeight: '70vh', overflow: 'auto' }}>
        <section>
          <h4>待确认命令</h4>
          {approvals.data?.approvals.length ? (
            approvals.data.approvals.map((row) => (
              <div key={row.id} style={{ border: "1px solid #d7e1ef", padding: 8, marginBottom: 8, borderRadius: 4 }}>
                <code>{row.command}</code>
                <span className="muted">cwd: {row.cwd}</span>
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
            <p className="muted">没有待确认的命令。</p>
          )}
        </section>
        <section>
          <h4>检查点</h4>
          {checkpoints.data?.changes.length ? (
            <p className="muted">
              未提交改动：{checkpoints.data.changes.map((row) => row.path).join('、')}
            </p>
          ) : null}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(checkpoints.data?.checkpoints || []).map((row) => (
              <div key={row.commit} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button
                  type="button"
                  className={selected === row.commit ? 'active' : ''}
                  onClick={() => setSelected(row.commit)}
                >
                  {row.label} · {row.date}
                </button>
                <Button
                  disabled={restore.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        `回滚到「${row.label}」？该检查点之后新增的文件会被删除，改动会先自动存档。`,
                      )
                    )
                      restore.mutate(row.commit);
                  }}
                >
                  回滚到此
                </Button>
              </div>
            ))}
          </div>
          {!checkpoints.data?.checkpoints.length && <p className="muted">还没有检查点。</p>}
          {selected && (
            <pre style={{ background: "#f6f9fd", border: "1px solid #d7e1ef", padding: 8, maxHeight: 320, overflow: "auto", whiteSpace: "pre-wrap" }}>{diff.data?.diff || '暂无差异。'}</pre>
          )}
        </section>
        <ErrorText
          error={approvals.error || checkpoints.error || diff.error || decide.error || restore.error}
        />
      </div>
    </Modal>
  );
}
