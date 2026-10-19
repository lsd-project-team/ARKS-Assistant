import { useState, useEffect, useRef, lazy, Suspense, type CSSProperties } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MessageSquare, Code2 } from 'lucide-react';
import { WorkspaceNavigation } from './layouts/WorkspaceNavigation';
import { WorkspaceHeader, WorkspaceHeadingTarget } from './layouts/WorkspaceHeader';
import { useKnowledgeNavigation } from '../features/knowledge/hooks/useKnowledgeNavigation';
import { useAppearance } from '../features/settings/lib/appearance';
import { Sidebar } from '../features/chat/components/Sidebar';
import { FileExplorer } from '../features/source_reader/components/FileExplorer';
import { ChatPane } from '../features/chat/components/ChatPane';
import { PaneDivider } from './layouts/PaneDivider';
import { SettingsDialog } from '../features/settings/components/SettingsDialog';
import { useWorkspace } from './state/store';
import { api } from './api/client';
import { QuickOpen } from '../features/source_reader/components/QuickOpen';
import { Toasts } from '../shared/ui/Toasts';
import { WorkspaceSearch } from '../features/source_reader/components/WorkspaceSearch';
import { useWindowSync } from './hooks/useWindowSync';
import { useNavigationLayout } from './layouts/hooks/useNavigationLayout';
import { useLayoutMotion } from './layouts/hooks/useLayoutMotion';
import { WorkspaceLoadBoundary } from './layouts/WorkspaceLoadBoundary';
import { ProjectHome } from '../features/projects/components/ProjectHome';
import { useSourceContext } from '../features/source_reader/hooks/useSourceContext';
import { ErrorText } from '../shared/ui/ui';
import { useNewConversation } from '../features/chat/hooks/useNewConversation';
import { HistoricalSourceDialog } from '../features/source_reader/components/HistoricalSourceDialog';
import '../features/chat/styles/conversations.css';
import '../features/chat/styles/chat-experience.css';
import '../features/chat/styles/conversation-workflows.css';
import '../features/settings/styles/settings.css';
import { useHandoverNavigation } from '../features/handover/navigation';

const KnowledgeWorkspace = lazy(() => import('../features/knowledge/KnowledgeWorkspace'));
const HandoverWorkspace = lazy(() => import('../features/handover/HandoverWorkspace'));

const CodePane = lazy(() =>
  import('../features/source_reader/components/CodePane').then((module) => ({
    default: module.CodePane,
  })),
);

export default function App() {
  useWindowSync();
  const sourceContext = useSourceContext();
  const startConversation = useNewConversation();
  const { route, navigate, knowledgeOpen } = useKnowledgeNavigation();
  const handover = useHandoverNavigation();
  const appearance = useAppearance((state) => state.mode);
  useEffect(() => {
    document.documentElement.dataset.appearance = appearance;
  }, [appearance]);
  // 第一次融合后显示左上角的完整导航；后续仍尊重用户的折叠偏好。
  useEffect(() => {
    if (localStorage.getItem('trunk-knowledge-navigation-v1')) return;
    useWorkspace.setState({ collapsed: false, readingFocused: false });
    localStorage.setItem('trunk-knowledge-navigation-v1', '1');
  }, []);
  const [dialog, setDialog] = useState('');
  const [headingTarget, setHeadingTarget] = useState<HTMLDivElement | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.shiftKey &&
        event.key.toLowerCase() === 'f' &&
        !(event.target as HTMLElement).closest('[role="dialog"]')
      ) {
        event.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, []);
  const {
    mobile,
    setMobile,
    navigationVersion,
    threadId,
    projectPage,
    collapsed,
    codeOpen,
    explorerOpen,
    chatRatio,
    explorerWidth,
    navigationWidth,
    setLayout,
    readingFocused,
    focusChatRatio,
    toggleReadingFocus,
    setWorkspaceOpen,
  } = useWorkspace();
  const navigationLayout = useNavigationLayout(navigationWidth);
  const motion = useLayoutMotion(
    { collapsed, codeOpen, explorerOpen },
    `${collapsed}:${codeOpen}:${explorerOpen}:${readingFocused}:${chatRatio}:${focusChatRatio}:${explorerWidth}:${navigationLayout.width}`,
  );
  const setCollapsed = (collapsed: boolean) => setLayout({ collapsed });
  const setExplorerOpen = (explorerOpen: boolean) => setLayout({ explorerOpen });
  // 导航只由持久化的 collapsed 控制，切页和源码专注模式都不改变展开状态。
  const expandNavigation = () => setCollapsed(false);
  const previousNavigation = useRef({ navigationVersion, threadId });
  useEffect(() => {
    const previous = previousNavigation.current;
    previousNavigation.current = { navigationVersion, threadId };
    // 刷新时保留工作区开关状态；只有实际切换文件或会话才调整文件树。
    if (previous.navigationVersion === navigationVersion && previous.threadId === threadId) return;
    // 中小窗口的文件树使用浮层，打开源码后收起，让阅读区恢复完整宽度。
    if (window.matchMedia('(max-width: 1100px)').matches) setExplorerOpen(false);
  }, [navigationVersion, threadId]);
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => api<{ ok: boolean; workspace: string }>('/health'),
    retry: 1,
    refetchInterval: 15000,
  });
  function toggleWorkspace() {
    const visible = (codeOpen || explorerOpen) && (window.innerWidth > 800 || mobile === 'code');
    setWorkspaceOpen(!visible);
  }
  return (
    <WorkspaceHeadingTarget.Provider value={headingTarget}>
      <div
        ref={motion.root}
        data-explorer-open={explorerOpen}
        style={
          {
            '--chat-ratio': chatRatio,
            '--navigation-width': `${navigationLayout.width}px`,
            '--focus-chat-ratio': focusChatRatio,
            ...(explorerWidth ? { '--explorer-width': `${explorerWidth}px` } : {}),
          } as CSSProperties
        }
        className={`app-shell legacy-visual has-account-header ${collapsed ? 'sidebar-collapsed' : ''} ${readingFocused ? 'reading-focused' : ''} ${!codeOpen ? 'code-closed' : ''} ${!codeOpen && !explorerOpen ? 'source-closed' : ''} mobile-${mobile}`}
      >
        <WorkspaceHeader headingRef={setHeadingTarget} />
        <WorkspaceNavigation
          route={route}
          compact={!motion.navigationExpanded}
          layout={navigationLayout}
          onExpand={expandNavigation}
          onCollapse={() => setCollapsed(true)}
          navigate={(next) => {
            if (readingFocused) toggleReadingFocus();
            if (next.kind === 'chat') {
              if (!startConversation()) return;
              requestAnimationFrame(() =>
                document
                  .querySelector<HTMLTextAreaElement>('textarea[aria-label="对话输入"]')
                  ?.focus(),
              );
            }
            void navigate(next);
            setMobile('chat');
          }}
          onSettings={() => {
            setDialog('settings');
          }}
          handover={{ active: handover.open, onOpen: () => handover.navigate() }}
        >
          {motion.navigationExpanded && (
            <Sidebar
              onNavigate={() => {
                void navigate({ kind: 'chat' });
              }}
              connected={!!health.data?.ok && !health.error}
              checking={health.isPending}
            />
          )}
        </WorkspaceNavigation>
        {projectPage && !knowledgeOpen && !handover.open && <ProjectHome />}
        {handover.open && (
          <Suspense
            fallback={<section className="project-home padded muted">正在加载交接工作台…</section>}
          >
            <HandoverWorkspace
              tab={handover.tab}
              recordId={handover.recordId}
              version={handover.version}
              navigate={handover.navigate}
              onWorkspaceNavigate={(kind) => {
                void navigate({ kind });
              }}
            />
          </Suspense>
        )}
        {knowledgeOpen && sourceContext.isPending && (
          <section className="project-home padded muted" role="status">
            正在读取流程与功能资料…
          </section>
        )}
        {knowledgeOpen && sourceContext.isError && (
          <section className="project-home padded">
            <ErrorText error={sourceContext.error} />
            <button className="button" onClick={() => void sourceContext.refetch()}>
              重新加载
            </button>
          </section>
        )}
        {knowledgeOpen && sourceContext.isSuccess && !sourceContext.data.knowledge_available && (
          <section className="project-home">
            <div className="project-empty">
              <h2>此项目还没有流程与功能资料</h2>
              <p>关联源码后，可以在对话中分析当前项目。已复核图谱属于原来的源码项目。</p>
              <button
                className="button"
                onClick={() => {
                  if (!startConversation()) return;
                  void navigate({ kind: 'chat' });
                }}
              >
                开始新对话
              </button>
            </div>
          </section>
        )}
        {knowledgeOpen && sourceContext.isSuccess && sourceContext.data.knowledge_available && (
          <WorkspaceLoadBoundary kind="knowledge">
            <Suspense
              fallback={
                <section className="knowledge-workspace padded muted">
                  正在加载流程与功能资料…
                </section>
              }
            >
              <KnowledgeWorkspace
                route={route}
                navigate={(next) => {
                  void navigate(next);
                }}
              />
            </Suspense>
          </WorkspaceLoadBoundary>
        )}
        <main className="workspace-main" hidden={knowledgeOpen || projectPage || handover.open}>
          <div className="mobile-switch">
            <button
              className={mobile === 'chat' ? 'selected' : ''}
              onClick={() => setMobile('chat')}
            >
              <MessageSquare size={14} />
              问答
            </button>
            <button
              className={mobile === 'code' ? 'selected' : ''}
              aria-label="切换工作区视图"
              aria-pressed={mobile === 'code' && (codeOpen || explorerOpen)}
              onClick={toggleWorkspace}
            >
              <Code2 size={14} />
              工作区
            </button>
          </div>
          <ChatPane
            showHeader={!knowledgeOpen && !projectPage && !handover.open}
            onSettings={(tab) => setDialog(tab === 'mcp' ? 'mcp' : 'settings')}
            onToggleWorkspace={toggleWorkspace}
          />
          {(motion.codeMounted || motion.filesMounted) && (
            <PaneDivider kind={motion.codeMounted ? 'chat' : 'files'} />
          )}
          <section
            className="source-workspace"
            aria-label="源码工作区"
            hidden={!motion.codeMounted && !motion.filesMounted}
            inert={!codeOpen && !explorerOpen}
          >
            {motion.codeMounted && (
              <WorkspaceLoadBoundary kind="source">
                <Suspense
                  fallback={<div className="code-pane padded muted">正在加载源码编辑器…</div>}
                >
                  <CodePane onSearch={() => setSearchOpen(true)} />
                </Suspense>
              </WorkspaceLoadBoundary>
            )}
            {motion.codeMounted && motion.filesMounted && <PaneDivider kind="files" />}
            <FileExplorer
              hidden={!motion.filesMounted}
              onClose={() => setExplorerOpen(false)}
              onQuickOpen={() => setDialog('files')}
            />
          </section>
        </main>
        <SettingsDialog
          open={dialog === 'settings' || dialog === 'mcp'}
          initialTab={dialog === 'mcp' ? 'mcp' : 'model'}
          onClose={() => setDialog('')}
        />
        <QuickOpen
          open={dialog === 'files'}
          onClose={() => setDialog('')}
          onOpen={() => setDialog('files')}
        />
        <Toasts />
        <HistoricalSourceDialog />
        {searchOpen && <WorkspaceSearch onClose={() => setSearchOpen(false)} />}
      </div>
    </WorkspaceHeadingTarget.Provider>
  );
}
