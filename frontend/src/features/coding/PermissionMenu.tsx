import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { Check, ChevronDown, Eye, ShieldAlert, ShieldCheck } from 'lucide-react';
import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { api, jsonBody } from '../../app/api/client';
import { useWorkspace } from '../../app/state/store';
import { toast } from '../../shared/utils/toasts';

export type Permission = 'read-only' | 'workspace-write' | 'full-access';

interface CodingSettings {
  permission: Permission;
  writable: boolean;
  readonly?: boolean;
  enabled?: boolean;
}

const OPTIONS: {
  value: Permission;
  label: string;
  description: string;
  icon: typeof Eye;
}[] = [
  {
    value: 'read-only',
    label: '仅可查看',
    description: '只读取文件，命令限定为查看类',
    icon: Eye,
  },
  {
    value: 'workspace-write',
    label: '工作区内修改',
    description: '项目内可读写，未知命令需确认',
    icon: ShieldCheck,
  },
  {
    value: 'full-access',
    label: '完全权限',
    description: '项目内可读写，命令不再确认',
    icon: ShieldAlert,
  },
];

const SETTINGS_KEY = 'coding-settings';
const MENU_HEIGHT = 190;

function placeAt(rect: DOMRect) {
  const right = Math.max(12, window.innerWidth - rect.right);
  if (rect.bottom + MENU_HEIGHT + 12 > window.innerHeight) {
    // 输入框贴近窗口底部时向上展开，避免菜单被裁掉。
    return { bottom: Math.max(12, window.innerHeight - rect.top + 6), right };
  }
  return { top: rect.bottom + 6, right };
}

function PermissionConfirm({
  permission,
  submitting,
  onCancel,
  onConfirm,
}: {
  permission: Permission;
  submitting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const descriptionId = useId();
  const fullAccess = permission === 'full-access';
  const effects = fullAccess
    ? [
        '对本项目的所有对话生效',
        '命令不再逐条确认，危险命令仍会被拒绝',
        '切换后待确认的命令会被取消，可随时切回',
      ]
    : [
        '对本项目的所有对话生效',
        '允许写入项目文件，并在可行时启用编码',
        '切回「仅可查看」即可停止写入',
      ];
  return (
    <Dialog.Root open onOpenChange={(next) => !next && onCancel()}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay permission-confirm-overlay" />
        <Dialog.Content
          className="modal-content permission-confirm"
          aria-describedby={descriptionId}
        >
          <Dialog.Title className="permission-confirm-title">
            {fullAccess ? '切换到完全权限？' : '启用编码并切换到工作区内修改？'}
          </Dialog.Title>
          <p className="permission-confirm-desc" id={descriptionId}>
            {fullAccess
              ? '完全权限会让项目内的命令直接执行，不再逐条确认；危险命令仍会被拒绝。'
              : '当前目录是只读分析目录。确认后会同时允许写入项目文件，项目内的编码能力随之启用。'}
          </p>
          <ul className="permission-confirm-effects">
            {effects.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <div className="permission-confirm-actions">
            <button type="button" className="button" onClick={onCancel}>
              取消
            </button>
            <button
              type="button"
              className="button primary"
              disabled={submitting}
              onClick={onConfirm}
            >
              {fullAccess ? '确认切换' : '启用并切换'}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function PermissionMenu({ inline = false }: { inline?: boolean }) {
  const projectId = useWorkspace((state) => state.projectId);
  const cache = useQueryClient();
  const root = useRef<HTMLDivElement>(null);
  const chip = useRef<HTMLButtonElement>(null);
  const popover = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState<{ permission: Permission; enabled?: boolean } | null>(
    null,
  );
  const [position, setPosition] = useState<{
    top?: number;
    bottom?: number;
    right: number;
  } | null>(null);
  // 独立对话也使用基础工作区，权限请求照常走 /coding/permission。
  const active = Boolean(projectId);
  const settings = useQuery({
    queryKey: [SETTINGS_KEY, projectId],
    queryFn: () => api<CodingSettings>('/coding/settings'),
    staleTime: 15000,
    enabled: active,
  });
  const current: Permission = settings.data?.permission ?? 'workspace-write';
  const option = OPTIONS.find((item) => item.value === current) || OPTIONS[1];
  const CurrentIcon = option.icon;

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!root.current?.contains(target) && !popover.current?.contains(target)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', escape);
    };
  }, [open]);

  // 顶栏的标题槽有 overflow hidden，弹出层必须挂到 body 上并按按钮位置固定定位。
  useEffect(() => {
    if (!open) return;
    const place = () => {
      const rect = chip.current?.getBoundingClientRect();
      if (!rect) return;
      setPosition(placeAt(rect));
    };
    place();
    window.addEventListener('resize', place);
    return () => window.removeEventListener('resize', place);
  }, [open]);

  function toggle() {
    if (save.isPending) return;
    if (open) {
      setOpen(false);
      return;
    }
    const rect = chip.current?.getBoundingClientRect();
    if (rect) setPosition(placeAt(rect));
    setOpen(true);
  }

  const save = useMutation<
    CodingSettings,
    Error,
    { permission: Permission; enabled?: boolean },
    { previous?: CodingSettings }
  >({
    mutationFn: (body) =>
      api<CodingSettings>('/coding/permission', { method: 'PUT', body: jsonBody(body) }),
    onMutate: async (body) => {
      const key = [SETTINGS_KEY, projectId] as const;
      await cache.cancelQueries({ queryKey: key });
      const previous = cache.getQueryData<CodingSettings>(key);
      if (previous)
        cache.setQueryData(key, {
          ...previous,
          permission: body.permission,
          writable: body.permission !== 'read-only',
        });
      return { previous };
    },
    onError: (error, _body, context) => {
      if (context?.previous)
        cache.setQueryData([SETTINGS_KEY, projectId], context.previous);
      toast(error.message, undefined, 'error');
    },
    onSuccess: () => toast('权限已切换'),
    onSettled: () => {
      void cache.invalidateQueries({ queryKey: [SETTINGS_KEY] });
    },
  });

  function choose(value: Permission) {
    setOpen(false);
    if (save.isPending || value === current) return;
    if (value === 'full-access') {
      setPending({ permission: value });
      return;
    }
    if (value === 'workspace-write' && settings.data?.readonly && !settings.data.enabled) {
      setPending({ permission: value, enabled: true });
      return;
    }
    save.mutate({ permission: value });
  }

  function confirmPending() {
    if (!pending) return;
    const body: { permission: Permission; enabled?: boolean } = { permission: pending.permission };
    if (pending.enabled) body.enabled = true;
    setPending(null);
    save.mutate(body);
  }

  const confirmDialog = pending ? (
    <PermissionConfirm
      permission={pending.permission}
      submitting={save.isPending}
      onCancel={() => setPending(null)}
      onConfirm={confirmPending}
    />
  ) : null;

  if (!active) return null;

  if (inline) {
    return (
      <>
        {confirmDialog}
        <div className="permission-inline" role="radiogroup" aria-label="权限档位">
        {OPTIONS.map((item) => {
          const Icon = item.icon;
          const active = item.value === current;
          return (
            <button
              key={item.value}
              type="button"
              role="radio"
              aria-checked={active}
              className={active ? 'active' : ''}
              disabled={save.isPending}
              title={item.description}
              onClick={() => choose(item.value)}
            >
              <Icon size={15} aria-hidden="true" />
              <span>{item.label}</span>
              <small>{item.description}</small>
            </button>
          );
        })}
        </div>
      </>
    );
  }

  return (
    <>
      {confirmDialog}
      <div className="permission-menu" ref={root}>
      <button
        type="button"
        ref={chip}
        className="permission-chip"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={save.isPending}
        title="切换权限档位"
        onClick={toggle}
      >
        <CurrentIcon size={15} aria-hidden="true" />
        <span className={`permission-label permission-${current}`}>{option.label}</span>
        <ChevronDown size={13} aria-hidden="true" />
      </button>
      {open && position && createPortal(
          <div
            ref={popover}
            className="permission-popover"
            role="menu"
            style={{
              position: 'fixed',
              right: position.right,
              ...(position.top !== undefined
                ? { top: position.top, bottom: 'auto' }
                : { top: 'auto', bottom: position.bottom }),
            }}
          >
            {OPTIONS.map((item) => {
              const Icon = item.icon;
              const checked = item.value === current;
              return (
                <button
                  key={item.value}
                  type="button"
                  role="menuitemradio"
                  aria-checked={checked}
                  onClick={() => choose(item.value)}
                >
                  <Icon size={16} aria-hidden="true" />
                  <span>
                    {item.label}
                    <small>{item.description}</small>
                  </span>
                  {checked && <Check size={15} aria-hidden="true" />}
                </button>
              );
            })}
          </div>,
          document.body,
        )}
      </div>
    </>
  );
}
