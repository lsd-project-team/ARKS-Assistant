import { useEffect, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, ShieldQuestion, X } from 'lucide-react';
import { api } from '../../../app/api/client';
import type { CodingApproval } from '../../../shared/types/api';
import { toast } from '../../../shared/utils/toasts';

export function CodingApprovalCard({ approval }: { approval: CodingApproval }) {
  const cache = useQueryClient();
  const [decided, setDecided] = useState<'approved' | 'rejected' | null>(null);
  const decide = useMutation({
    mutationFn: (approved: boolean) =>
      api(`/coding/approvals/${approval.id}`, {
        method: 'POST',
        body: JSON.stringify({ approved }),
      }),
    onSuccess: (_data, approved) => {
      setDecided(approved ? 'approved' : 'rejected');
      void cache.invalidateQueries({ queryKey: ['coding-approvals'] });
      void cache.invalidateQueries({ queryKey: ['coding-checkpoints'] });
    },
    onError: (error: Error) => toast(error.message, undefined, 'error'),
  });
  if (approval.status !== 'pending') return null;
  return (
    <section className="coding-approval" aria-label="命令需要确认">
      <div className="coding-approval-heading">
        <ShieldQuestion size={16} />
        <strong>{approval.kind === 'process' ? '需要确认的后台命令' : '需要确认的命令'}</strong>
      </div>
      <pre className="coding-approval-command">{approval.command}</pre>
      <p className="muted">
        目录：{approval.cwd || '.'} · 批准后会在本项目内执行并自动继续本轮
      </p>
      {decided ? (
        <p className="coding-approval-status">
          {decided === 'approved' ? '已批准，正在执行…' : '已拒绝，本轮不会再执行这条命令。'}
        </p>
      ) : (
        <div className="coding-approval-actions">
          <button
            type="button"
            className="primary"
            disabled={decide.isPending}
            onClick={() => decide.mutate(true)}
          >
            <Check size={14} />
            允许一次
          </button>
          <button type="button" disabled={decide.isPending} onClick={() => decide.mutate(false)}>
            <X size={14} />
            拒绝
          </button>
        </div>
      )}
    </section>
  );
}

export function CodingConsole({ output }: { output: string }) {
  const ref = useRef<HTMLPreElement>(null);
  const container = useRef<HTMLDetailsElement>(null);
  const opened = useRef(false);
  useEffect(() => {
    if (output && !opened.current && container.current) {
      container.current.open = true;
      opened.current = true;
    }
    const node = ref.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [output]);
  if (!output) return null;
  return (
    <details className="coding-console" ref={container}>
      <summary>命令输出 · 实时</summary>
      <pre ref={ref}>{output}</pre>
    </details>
  );
}
