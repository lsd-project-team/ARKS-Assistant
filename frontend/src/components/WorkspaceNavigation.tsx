import { Settings2, Menu, Palette } from 'lucide-react';
import { useEffect, useRef, type ReactNode } from 'react';
import type { Route } from '../knowledge/routes';
import { appearanceModes, useAppearance } from '../lib/appearance';
import { NavigationDivider } from './NavigationDivider';
import { NavigationIcon } from './NavigationIcon';

export function WorkspaceNavigation({
  route,
  compact,
  hasSelectedThread,
  layout,
  onExpand,
  onCollapse,
  navigate,
  onSettings,
  children,
}: {
  route: Route;
  compact: boolean;
  hasSelectedThread: boolean;
  layout: { width: number; maximumWidth: number };
  onExpand: () => void;
  onCollapse: () => void;
  navigate: (route: Route) => void;
  onSettings: () => void;
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
  const { mode, setMode } = useAppearance();
  const active =
    route.kind === 'chat'
      ? hasSelectedThread
        ? undefined
        : 'chat'
      : ['graphs', 'graph', 'catalog'].includes(route.kind)
        ? 'graphs'
        : 'modules';
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
            { kind: 'graphs', label: '流程图谱' },
            { kind: 'modules', label: '功能说明' },
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
      </nav>
      <div className="navigation-conversations">{children}</div>
      <div className="navigation-tools">
        <button
          title={`切换外观（当前：${appearanceModes.find((item) => item.id === mode)?.title}）`}
          aria-label="切换外观"
          onClick={() =>
            setMode(
              appearanceModes[
                (appearanceModes.findIndex((item) => item.id === mode) + 1) % appearanceModes.length
              ].id,
            )
          }
        >
          <Palette size={17} />
          <span className="nav-copy">
            外观 · {appearanceModes.find((item) => item.id === mode)?.title}
          </span>
        </button>
        <button title="设置" aria-label="设置" onClick={onSettings}>
          <Settings2 size={17} />
          <span className="nav-copy">设置</span>
        </button>
      </div>
      {!compact && <NavigationDivider {...layout} />}
    </aside>
  );
}
