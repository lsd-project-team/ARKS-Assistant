import { ShieldQuestion } from 'lucide-react';
import { useEffect, useRef } from 'react';

import type { CodingApproval } from '../../../shared/types/api';

const STATUS_TEXT: Record<string, string> = {
  pending: '等待确认，请在弹出的确认框中处理',
  approved: '已批准，命令正在执行…',
  rejected: '已拒绝，本轮不会再执行这条命令',
  expired: '等待确认超时，命令没有执行',
  cancelled: '已取消，命令没有执行',
};

/**
 * 聊天里的审批摘要：只展示状态，真正的决策入口是全局确认弹窗。
 */
export function CodingApprovalCard({ approval }: { approval: CodingApproval }) {
  return (
    <section className="coding-approval" aria-label="命令需要确认">
      <div className="coding-approval-heading">
        <ShieldQuestion size={16} />
        <strong>需要确认的命令</strong>
      </div>
      <pre className="coding-approval-command">{approval.command}</pre>
      <p className="muted">
        目录：{approval.cwd || '.'} · {approval.kind === 'process' ? '后台常驻' : '一次性命令'}
      </p>
      <p className="coding-approval-status">
        {STATUS_TEXT[approval.status] || approval.status}
      </p>
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
