import { Settings2, Menu, ClipboardList, Timer } from 'lucide-react';
import { useEffect, useRef, type ReactNode } from 'react';
import type { Route } from '../../features/knowledge/routes';
import { AppearanceSwitch } from '../../features/settings/components/AppearanceSwitch';
import { NavigationDivider } from './NavigationDivider';
import { NavigationIcon } from '../../shared/ui/NavigationIcon';

export function WorkspaceNavigation({
  route,
  compact,
  layout,
  onExpand,
  onCollapse,
  navigate,
  onSettings,
  handover,
  actionTiming,
  children,
}: {
  route: Route;
  compact: boolean;
  layout: { width: number; maximumWidth: number };
  onExpand: () => void;
  onCollapse: () => void;
  navigate: (route: Route) => void;
  onSettings: () => void;
  handover?: { active: boolean; onOpen: () => void };
  actionTiming?: { active: boolean; onOpen: () => void };
  children?: ReactNode;
}) {
  const navigationControl = useRef<HTMLButtonElement>(null);
  const previousCompact = useRef(compact);
  useEffect(() => {
    if (previousCompact.current === compact) return;
    previousCompact.current = compact;
    // 收缩和展开会替换按钮，把键盘焦点交给新出现的对应入口。
    navigationControl.current?.focus();
  }, [compact]);
  // 新对话是新建动作，不代表当前页面；所有聊天入口都不高亮它。
  const active =
    handover?.active || actionTiming?.active || route.kind === 'chat' ? undefined : 'modules';
  return (
    <aside
      className="app-navigation"
      id="workspace-navigation"
      aria-label="工作区导航"
      data-compact={compact}
    >
      <div className="workspace-brand" title="ARKS软件智能助手">
        {compact ? (
          <button
            ref={navigationControl}
            className="workspace-brand-mark"
            title="展开导航"
            aria-label="展开导航"
            aria-expanded={false}
            aria-controls="workspace-navigation"
            onClick={onExpand}
          >
            <img className="workspace-brand-image" src="/brand/arks-assistant-icon.png" alt="" />
          </button>
        ) : (
          <div className="workspace-brand-mark" aria-hidden="true">
            <img className="workspace-brand-image" src="/brand/arks-assistant-icon.png" alt="" />
          </div>
        )}
        <div className="nav-copy">
          <strong>ARKS智能助手</strong>
        </div>
        {!compact && (
          <button
            ref={navigationControl}
            className="navigation-toggle"
            title="收起导航"
            aria-label="收起导航"
            aria-expanded={true}
            aria-controls="workspace-navigation"
            onClick={onCollapse}
          >
            <Menu size={16} strokeWidth={1.5} />
          </button>
        )}
      </div>
      <nav className="workspace-sections" aria-label="主要功能">
        {(
          [
            { kind: 'chat', label: '新对话' },
            { kind: 'modules', label: '功能与流程' },
          ] as const
        ).map((item) => (
          <button
            key={item.kind}
            title={item.label}
            aria-label={item.label}
            aria-current={active === item.kind ? 'page' : undefined}
            className={active === item.kind ? 'active' : ''}
            onClick={() => navigate({ kind: item.kind } as Route)}
          >
            <NavigationIcon kind={item.kind} />
            <span className="nav-copy">{item.label}</span>
          </button>
        ))}
        {handover && (
          <button
            title="交接工作台"
            aria-label="交接工作台"
            aria-current={handover.active ? 'page' : undefined}
            className={handover.active ? 'active' : ''}
            onClick={handover.onOpen}
          >
            <ClipboardList size={18} strokeWidth={1.5} />
            <span className="nav-copy">交接工作台</span>
          </button>
        )}
        {actionTiming && (
          <button
            title="动作耗时统计"
            aria-label="动作耗时统计"
            aria-current={actionTiming.active ? 'page' : undefined}
            className={actionTiming.active ? 'active' : ''}
            onClick={actionTiming.onOpen}
          >
            <Timer size={18} strokeWidth={1.5} />
            <span className="nav-copy">动作耗时统计</span>
          </button>
        )}
      </nav>
      <div className="navigation-conversations">{children}</div>
      <div className="navigation-tools">
        <AppearanceSwitch />
        <button title="设置" aria-label="设置" onClick={onSettings}>
          <Settings2 size={17} />
          <span className="nav-copy">设置</span>
        </button>
      </div>
      {!compact && <NavigationDivider {...layout} />}
    </aside>
  );
}
