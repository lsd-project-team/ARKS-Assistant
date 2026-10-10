import { useState, useEffect, lazy, Suspense } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Home, Files, MessageSquare, Brain, Settings2, Code2 } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { FileExplorer } from './components/FileExplorer';
import { ChatPane } from './components/ChatPane';
import { PaneDivider } from './components/PaneDivider';
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
  const [explorerOpen, setExplorerOpen] = useState(true);
  const { mobile, setMobile, jump, threadId } = useWorkspace();
  useEffect(() => {
    setMobileSidebarOpen(false);
    // 窄屏文件树是浮层，打开源码后收起，让编辑器恢复完整宽度。
    if (window.matchMedia('(max-width: 800px)').matches) setExplorerOpen(false);
  }, [jump.time, threadId]);
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => api<{ ok: boolean; workspace: string }>('/health'),
    retry: 1,
  });
  function showSource() {
    setMobileSidebarOpen(false);
    setMobile('code');
    setExplorerOpen(true);
  }
  return (
    <div
      className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''} mobile-${mobile} ${mobileSidebarOpen ? 'show-mobile-sidebar' : ''}`}
    >
      <nav className="navigation-rail" aria-label="工作区导航">
        <button className="rail-home" aria-label="问答" onClick={() => setMobile('chat')}>
          <Home size={18} fill="currentColor" />
        </button>
        <button
          aria-label="对话列表"
          onClick={() => {
            setCollapsed(false);
            setMobileSidebarOpen(!mobileSidebarOpen);
            setMobile('chat');
          }}
        >
          <MessageSquare size={19} />
        </button>
        <button aria-label="文件浏览器" onClick={showSource}>
          <Files size={19} />
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
      {!collapsed && (
        <Sidebar
          onCollapse={() => {
            setCollapsed(true);
            setMobileSidebarOpen(false);
          }}
          onNavigate={() => setMobileSidebarOpen(false)}
          onShowSource={showSource}
          connected={!health.error}
        />
      )}
      <main className="workspace-main">
        <div className="mobile-switch">
          <button className={mobile === 'chat' ? 'selected' : ''} onClick={() => setMobile('chat')}>
            <MessageSquare size={14} />
            问答
          </button>
          <button className={mobile === 'code' ? 'selected' : ''} onClick={() => setMobile('code')}>
            <Code2 size={14} />
            源码
          </button>
        </div>
        <ChatPane
          onShowSource={showSource}
          onShowSidebar={() => {
            setCollapsed(false);
            setMobileSidebarOpen(!mobileSidebarOpen);
          }}
        />
        <PaneDivider />
        <section className="source-workspace" aria-label="源码工作区">
          <Suspense fallback={<div className="code-pane padded muted">正在加载源码编辑器…</div>}>
            <CodePane
              explorerOpen={explorerOpen}
              onToggleExplorer={() => setExplorerOpen(!explorerOpen)}
            />
          </Suspense>
          {explorerOpen && <FileExplorer onClose={() => setExplorerOpen(false)} />}
        </section>
      </main>
      <SettingsDialog open={dialog === 'settings'} onClose={() => setDialog('')} />
      <MemoryDialog open={dialog === 'memory'} onClose={() => setDialog('')} />
    </div>
  );
}
