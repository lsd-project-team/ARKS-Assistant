import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ChevronDown, Eye, ShieldAlert, ShieldCheck } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { api, jsonBody } from '../../app/api/client';
import { useWorkspace } from '../../app/state/store';
import { toast } from '../../shared/utils/toasts';
import { useAuth } from '../auth/AuthContext';

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

export function PermissionMenu({ inline = false }: { inline?: boolean }) {
  const projectId = useWorkspace((state) => state.projectId);
  const admin = useAuth().session?.user?.role === 'admin';
  const cache = useQueryClient();
  const root = useRef<HTMLDivElement>(null);
  const chip = useRef<HTMLButtonElement>(null);
  const popover = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; right: number } | null>(null);
  // 独立对话没有项目工作区，不显示权限入口。
  const active = Boolean(projectId) && projectId !== 'independent';
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
      if (rect) setPosition({ top: rect.bottom + 6, right: Math.max(12, window.innerWidth - rect.right) });
    };
    place();
    window.addEventListener('resize', place);
    return () => window.removeEventListener('resize', place);
  }, [open]);

  function toggle() {
    if (!admin) return;
    if (open) {
      setOpen(false);
      return;
    }
    const rect = chip.current?.getBoundingClientRect();
    if (rect) {
      setPosition({ top: rect.bottom + 6, right: Math.max(12, window.innerWidth - rect.right) });
    }
    setOpen(true);
  }

  const save = useMutation<
    CodingSettings,
    Error,
    { permission: Permission; enabled?: boolean },
    { previous?: CodingSettings }
  >({
    mutationFn: (body) =>
      api<CodingSettings>('/coding/settings', { method: 'PUT', body: jsonBody(body) }),
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
    if (!admin || save.isPending || value === current) return;
    const body: { permission: Permission; enabled?: boolean } = { permission: value };
    if (value === 'workspace-write' && settings.data?.readonly && !settings.data.enabled) {
      if (!window.confirm('该目录是只读分析目录，切换为「工作区内修改」会同时启用编码写入。继续？'))
        return;
      body.enabled = true;
    }
    if (value === 'full-access' && !window.confirm('完全权限会跳过命令确认；危险命令仍会被拒绝。确定切换？'))
      return;
    save.mutate(body);
  }

  if (!active) return null;

  if (inline) {
    return (
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
              disabled={!admin || save.isPending}
              title={admin ? item.description : '仅管理员可以切换权限'}
              onClick={() => choose(item.value)}
            >
              <Icon size={15} aria-hidden="true" />
              <span>{item.label}</span>
              <small>{item.description}</small>
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="permission-menu" ref={root}>
      <button
        type="button"
        ref={chip}
        className="permission-chip"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={!admin}
        title={admin ? '切换权限档位' : '仅管理员可以切换权限'}
        onClick={toggle}
      >
        <CurrentIcon size={15} aria-hidden="true" />
        <span className={`permission-label permission-${current}`}>{option.label}</span>
        {admin && <ChevronDown size={13} aria-hidden="true" />}
      </button>
      {open &&
        admin &&
        position &&
        createPortal(
          <div
            ref={popover}
            className="permission-popover"
            role="menu"
            style={{ position: 'fixed', top: position.top, right: position.right }}
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
  );
}
