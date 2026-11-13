import * as Dialog from '@radix-ui/react-dialog';
import { ChevronDown, SquareTerminal } from 'lucide-react';
import { useEffect, useId, useRef, useState } from 'react';

import { toast } from '../../shared/utils/toasts';
import { useApprovals, useDecideApproval } from './useApprovals';

const KIND_LABEL: Record<string, string> = {
  command: '终端',
  process: '后台进程',
};

const TITLE: Record<string, string> = {
  command: '允许运行这条命令吗？',
  process: '允许启动这个后台进程吗？',
};

/**
 * 全局审批弹窗：命令需要确认时盖在页面最上层，离开聊天页也不会丢。
 * 同一时刻只处理一条，其余排队；`Esc` 拒绝、`Enter` 允许一次。
 */
export function ApprovalDialogHost() {
  const approvals = useApprovals();
  const decide = useDecideApproval();
  const pending = (approvals.data?.approvals || []).filter((row) => row.status === 'pending');
  const current = pending[0];
  const [menuOpen, setMenuOpen] = useState(false);
  const metaId = useId();
  const allowRef = useRef<HTMLButtonElement>(null);
  const activeId = useRef<string | null>(null);
  const settled = useRef(false);

  useEffect(() => {
    if (current) {
      if (activeId.current !== current.id) {
        activeId.current = current.id;
        settled.current = false;
        setMenuOpen(false);
      }
      return;
    }
    // 请求在别处被处理、超时或权限切换取消时，弹窗会自动消失，这里只补一条提示。
    if (activeId.current && !settled.current) {
      toast('该命令的确认已结束', undefined, 'success', { plain: true });
    }
    activeId.current = null;
  }, [current]);

  if (!current) return null;

  function resolve(approved: boolean, scope: 'once' | 'session') {
    if (!current || decide.isPending) return;
    settled.current = true;
    setMenuOpen(false);
    decide.mutate(
      { id: current.id, approved, scope },
      {
        onSuccess: () =>
          toast(
            approved ? '已允许，命令开始执行' : '已拒绝，本轮不会执行这条命令',
            undefined,
            'success',
          ),
        onError: (error: Error) => {
          settled.current = false;
          toast(error.message, undefined, 'error');
        },
      },
    );
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== 'Enter' || menuOpen) return;
    const target = event.target as HTMLElement;
    // 焦点在「拒绝」上时让按钮自己响应，避免把拒绝误操作成允许。
    if (target.closest('[data-deny]')) return;
    event.preventDefault();
    resolve(true, 'once');
  }

  return (
    <Dialog.Root open>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay approval-overlay" />
        <Dialog.Content
          className="modal-content approval-dialog"
          aria-describedby={metaId}
          onKeyDown={onKeyDown}
          onEscapeKeyDown={(event) => {
            event.preventDefault();
            if (menuOpen) {
              setMenuOpen(false);
              return;
            }
            resolve(false, 'once');
          }}
          onPointerDownOutside={(event) => event.preventDefault()}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            allowRef.current?.focus();
          }}
        >
          <div className="approval-dialog-kind">
            <SquareTerminal size={16} aria-hidden="true" />
            <span>{KIND_LABEL[current.kind] || '终端'}</span>
          </div>
          <Dialog.Title className="approval-dialog-title">
            {TITLE[current.kind] || TITLE.command}
          </Dialog.Title>
          <pre className="approval-dialog-command" aria-label="待执行的命令">
            {current.command}
          </pre>
          <p className="approval-dialog-meta" id={metaId}>
            目录：{current.cwd || '.'} · {current.kind === 'process' ? '后台常驻' : '一次性命令'}
          </p>
          <div className="approval-dialog-actions">
            <button
              type="button"
              className="button approval-deny"
              data-deny=""
              disabled={decide.isPending}
              onClick={() => resolve(false, 'once')}
            >
              拒绝 <kbd>Esc</kbd>
            </button>
            <div className="approval-allow-group">
              <button
                ref={allowRef}
                type="button"
                className="button primary approval-allow"
                disabled={decide.isPending}
                onClick={() => resolve(true, 'once')}
              >
                {decide.isPending ? '处理中…' : '允许一次'} {!decide.isPending && <kbd>↵</kbd>}
              </button>
              <button
                type="button"
                className="button approval-more"
                aria-label="更多允许方式"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                disabled={decide.isPending}
                onClick={() => setMenuOpen((value) => !value)}
              >
                <ChevronDown size={14} aria-hidden="true" />
              </button>
              {menuOpen && (
                <div className="approval-menu" role="menu">
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => resolve(true, 'once')}
                  >
                    允许一次
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    disabled={!current.thread_id}
                    title={current.thread_id ? undefined : '这条命令不属于任何对话，只能允许一次'}
                    onClick={() => resolve(true, 'session')}
                  >
                    本会话内允许这条命令
                  </button>
                </div>
              )}
            </div>
          </div>
          {pending.length > 1 && (
            <p className="approval-dialog-remaining">还有 {pending.length - 1} 条待确认</p>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
