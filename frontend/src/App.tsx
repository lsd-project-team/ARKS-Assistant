import { useState, useEffect, lazy, Suspense } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Layers2,
  Files,
  MessageSquare,
  Brain,
  Settings2,
  PanelLeftClose,
  PanelLeftOpen,
  Code2,
  ArrowUpRight,
} from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { ChatPane } from './components/ChatPane';
import { SettingsDialog } from './components/SettingsDialog';
import { MemoryDialog } from './components/MemoryDialog';
import { useWorkspace } from './lib/store';
import { api } from './lib/api';

const CodePane = lazy(() =>
  import('./components/CodePane').then((module) => ({ default: module.CodePane })),
);

export default function App() {
  const [dialog, setDialog] = useState('');
  const [collapsed, setCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const { sidebar, setSidebar, mobile, setMobile } = useWorkspace();
  const jump = useWorkspace((state) => state.jump.time);
  const threadId = useWorkspace((state) => state.threadId);
  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [jump, threadId]);
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => api<{ ok: boolean; workspace: string }>('/health'),
    retry: 1,
  });
  return (
    <div
      className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''} mobile-${mobile} ${mobileSidebarOpen ? 'show-mobile-sidebar' : ''}`}
    >
      <nav className="navigation-rail">
        <div className="brand" title="Trunk Agent">
          <Layers2 size={23} strokeWidth={1.8} />
        </div>
        <button
          className={sidebar === 'files' ? 'active' : ''}
          aria-label="文件浏览器"
          onClick={() => {
            setSidebar('files');
            setCollapsed(false);
            setMobileSidebarOpen(true);
          }}
        >
          <Files size={19} />
        </button>
        <button
          className={sidebar === 'threads' ? 'active' : ''}
          aria-label="对话列表"
          onClick={() => {
            setSidebar('threads');
            setCollapsed(false);
            setMobileSidebarOpen(true);
          }}
        >
          <MessageSquare size={19} />
        </button>
        <div className="rail-spacer" />
        <button aria-label="长期记忆" onClick={() => setDialog('memory')}>
          <Brain size={19} />
        </button>
        <button aria-label="设置" onClick={() => setDialog('settings')}>
          <Settings2 size={19} />
        </button>
        <div className="user-avatar" title="本地工作区">
          W
        </div>
      </nav>
      <header className="app-header">
        <div>
          <button
            className="collapse-button"
            aria-label="折叠侧栏"
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
          </button>
          <strong>Trunk</strong>
          <span className="header-divider">/</span>
          <span>源码工作区</span>
          <span className="version-badge">Agent</span>
        </div>
        <div className="header-right">
          <span className={`connection-label ${health.error ? 'offline' : ''}`}>
            <span className="tiny-dot" />
            {health.error ? '服务未连接' : '本机连接'}
          </span>
          <button onClick={() => setDialog('settings')}>
            Deep Agents
            <ArrowUpRight size={12} />
          </button>
        </div>
      </header>
      {!collapsed && <Sidebar />}
      <main className="workspace-main">
        <div className="mobile-switch">
          <button className={mobile === 'code' ? 'selected' : ''} onClick={() => setMobile('code')}>
            <Code2 size={13} />
            源码
          </button>
          <button className={mobile === 'chat' ? 'selected' : ''} onClick={() => setMobile('chat')}>
            <MessageSquare size={13} />
            对话
          </button>
        </div>
        <Suspense fallback={<div className="code-pane padded muted">正在加载源码编辑器…</div>}>
          <CodePane />
        </Suspense>
        <div
          className="pane-divider"
          onPointerDown={(event) => {
            const parent = event.currentTarget.parentElement!;
            const move = (next: PointerEvent) => {
              const width = Math.min(
                650,
                Math.max(340, parent.getBoundingClientRect().right - next.clientX),
              );
              parent.style.setProperty('--chat-width', `${width}px`);
            };
            const stop = () => {
              window.removeEventListener('pointermove', move);
              window.removeEventListener('pointerup', stop);
              document.body.style.cursor = '';
            };
            document.body.style.cursor = 'col-resize';
            window.addEventListener('pointermove', move);
            window.addEventListener('pointerup', stop, { once: true });
          }}
        />
        <ChatPane />
      </main>
      <SettingsDialog open={dialog === 'settings'} onClose={() => setDialog('')} />
      <MemoryDialog open={dialog === 'memory'} onClose={() => setDialog('')} />
    </div>
  );
}
