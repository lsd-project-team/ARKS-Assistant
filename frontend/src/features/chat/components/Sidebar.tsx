import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { LoaderCircle, Plus } from 'lucide-react';
import { api } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import {
  recentThreadPreview,
  threadProject,
  threadSelectedAt,
  visibleThreads,
  type SidebarView,
  type ThreadEntry,
} from '../lib/sidebarNavigation';
import { useSidebarActions } from '../hooks/useSidebarActions';
import { useCurrentProject } from '../../projects/hooks/useProjects';
import { useNewConversation } from '../hooks/useNewConversation';
import type { Thread } from '../../../shared/types/api';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { ConversationSearchDialog } from './ConversationSearchDialog';
import { ThreadItem } from './ThreadItem';
import { ProjectNavigation } from '../../projects/components/ProjectNavigation';
import { ProjectEditor } from '../../projects/components/ProjectEditor';
import { MoveThreadsDialog } from './MoveThreadsDialog';

interface SidebarProps {
  onNavigate: () => void;
  connected: boolean;
  checking?: boolean;
}

export function Sidebar({ onNavigate, connected, checking }: SidebarProps) {
  const {
    sidebarView: view,
    setSidebarView,
    projectId,
    threadId,
    projectPage,
    threadEntries,
  } = useWorkspace();
  const actions = useSidebarActions();
  const [creatingProject, setCreatingProject] = useState(false);
  const [locatedThread, setLocatedThread] = useState<Thread>();
  const list = useRef<HTMLDivElement>(null);
  useEffect(() => setLocatedThread(undefined), [view]);
  useEffect(() => {
    if (view === 'deleted' && locatedThread)
      list.current?.querySelector('.thread-row.active')?.scrollIntoView({ block: 'nearest' });
  }, [locatedThread, view]);
  const project = useCurrentProject();
  const previousProject = useRef({ id: projectId, state: project.data?.state });
  useEffect(() => {
    if (!project.data) return;
    const previous = previousProject.current;
    if (project.data.state === 'archived') setSidebarView('archived');
    else if (previous.id === projectId && previous.state === 'archived') setSidebarView('active');
    previousProject.current = { id: projectId, state: project.data.state };
    // 项目归档、恢复后跟随它的新位置；用户随后仍可手动切换三个列表。
  }, [project.data?.state, projectId, setSidebarView]);
  const selected = useQuery({
    queryKey: ['thread', threadId, 'navigation'],
    queryFn: () => api<Thread>(`/threads/${threadId}?limit=1`, undefined, projectId),
    enabled: !!threadId && !projectPage,
    retry: false,
  });
  const selectedThread =
    threadId && !projectPage && selected.data
      ? { ...selected.data, project_state: project.data?.state || null }
      : undefined;
  const renderThread = (row: Thread, readOnly = false, entry: ThreadEntry = 'project') => (
    <ThreadItem
      key={row.id}
      row={row}
      selected={
        row.state === 'deleted'
          ? view === 'deleted' && locatedThread?.id === row.id
          : threadSelectedAt(row, entry, { projectId, threadId, projectPage, threadEntries })
      }
      filter=""
      busy={actions.pending === row.id}
      readOnly={readOnly}
      onSelect={() => {
        onNavigate();
        useWorkspace.getState().switchProject(threadProject(row));
        useWorkspace.getState().selectThread(row.id);
        useWorkspace.getState().setThreadEntry(row.id, entry);
      }}
      onAction={(action) => {
        if (locatedThread?.id === row.id) setLocatedThread(undefined);
        void actions.act(row, action);
      }}
      onRename={(title) => actions.rename(row, title)}
    />
  );
  return (
    <aside className="sidebar" aria-label="会话导航">
      <div className="sidebar-views" aria-label="会话列表类型">
        {(
          [
            { id: 'active', label: '最近' },
            { id: 'archived', label: '已归档' },
            { id: 'deleted', label: '回收站' },
          ] as const
        ).map((item) => (
          <button
            key={item.id}
            aria-pressed={view === item.id}
            className={view === item.id ? 'selected' : ''}
            onClick={() => setSidebarView(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="sidebar-heading">
        <strong>
          {view === 'deleted' ? '已删除对话' : view === 'archived' ? '已归档项目' : '项目'}
        </strong>
        <div>
          {view === 'active' && (
            <button aria-label="新建项目" title="新建项目" onClick={() => setCreatingProject(true)}>
              <Plus size={15} />
            </button>
          )}
          <ConversationSearchDialog
            key={view}
            view={view}
            onNavigate={(row) => {
              if (row.state === 'deleted') {
                setLocatedThread(row);
                return;
              }
              setSidebarView(
                row.state === 'archived' ||
                  row.project_state === 'archived' ||
                  (threadProject(row) === projectId && project.data?.state === 'archived')
                  ? 'archived'
                  : 'active',
              );
              onNavigate();
            }}
          />
        </div>
      </div>
      <div className="sidebar-scroll" ref={list}>
        <ErrorText error={actions.error} />
        {view !== 'deleted' && (
          <ProjectNavigation
            key={`projects:${view}`}
            view={view}
            onNavigate={onNavigate}
            renderThread={renderThread}
            selectedThread={selectedThread}
          />
        )}
        <RecentThreads
          key={`threads:${view}`}
          view={view}
          renderThread={renderThread}
          selectedThread={view === 'deleted' ? locatedThread : selectedThread}
          onNavigate={onNavigate}
        />
      </div>
      <div className={`sidebar-footer ${checking ? 'checking' : connected ? '' : 'offline'}`}>
        <span className="tiny-dot" />
        <span>{checking ? '正在连接…' : connected ? '本机工作区' : '服务未连接'}</span>
      </div>
      <Modal
        open={!!actions.purging}
        onClose={() => {
          if (!actions.pending) {
            actions.setPurging(undefined);
            actions.setError(undefined);
          }
        }}
        title="彻底删除对话"
        className="confirmation-dialog"
        description="此操作无法撤销。"
      >
        <div className="dialog-body">
          <p>将删除“{actions.purging?.title}”的消息、运行记录、检查点和归属档案。</p>
          <p className="muted">独立的长期记忆保留，来源标记为已删除。</p>
          <ErrorText error={actions.error} />
        </div>
        <div className="modal-footer">
          <Button disabled={!!actions.pending} onClick={() => actions.setPurging(undefined)}>
            取消
          </Button>
          <Button
            className="danger-button"
            disabled={!!actions.pending}
            onClick={() => void actions.permanentlyDelete()}
          >
            {actions.pending ? '正在删除…' : '彻底删除'}
          </Button>
        </div>
      </Modal>
      {actions.moving && (
        <MoveThreadsDialog ids={actions.moving} onClose={() => actions.setMoving(undefined)} />
      )}
      {creatingProject && <ProjectEditor onClose={() => setCreatingProject(false)} />}
    </aside>
  );
}

function RecentThreads({
  view,
  renderThread,
  selectedThread,
  onNavigate,
}: {
  view: SidebarView;
  renderThread: (row: Thread, readOnly?: boolean, entry?: ThreadEntry) => ReactNode;
  selectedThread?: Thread;
  onNavigate: () => void;
}) {
  const startConversation = useNewConversation();
  const [all, setAll] = useState(false);
  const threads = useInfiniteQuery({
    queryKey: ['threads', 'navigation', view],
    initialPageParam: 0,
    // 最近只显示正常项目；已归档项目集中在归档页，回收站仍包含所有项目。
    queryFn: ({ pageParam, signal }) =>
      api<Thread[]>(
        `/projects/search-threads?state=${view}&limit=50&offset=${pageParam}${view === 'active' ? '&project_state=active' : ''}`,
        { signal },
      ),
    getNextPageParam: (page, _pages, previous) => (page.length === 50 ? previous + 50 : undefined),
    refetchInterval: 5000,
  });
  const rows = threads.data?.pages.flat() || [];
  const visible = visibleThreads(
    rows,
    selectedThread?.state === view &&
      !(view === 'active' && selectedThread.project_state === 'archived')
      ? selectedThread
      : undefined,
    all ? undefined : recentThreadPreview,
  );
  return (
    <section
      className="sidebar-thread-section"
      aria-label={
        view === 'active' ? '最近对话' : view === 'archived' ? '已归档对话' : '已删除对话'
      }
    >
      {view !== 'deleted' && (
        <div className="sidebar-section-title">
          <span>{view === 'active' ? '最近对话' : '已归档对话'}</span>
          {view === 'active' && (
            <button
              className="project-hover-action"
              aria-label="新建对话"
              title="新建独立对话"
              onClick={() => {
                if (startConversation()) onNavigate();
              }}
            >
              <Plus size={15} />
            </button>
          )}
        </div>
      )}
      <ErrorText error={threads.error} />
      {threads.isPending && <p className="muted sidebar-empty">正在读取对话…</p>}
      {visible.map((row) =>
        renderThread(row, row.project_state === 'archived' && row.state !== 'deleted', 'recent'),
      )}
      {!threads.isPending && !rows.length && view !== 'archived' && (
        <p className="muted sidebar-empty">{view === 'deleted' ? '回收站为空' : '从新对话开始'}</p>
      )}
      {!all && rows.length > recentThreadPreview && (
        <button className="sidebar-show-more" onClick={() => setAll(true)}>
          展开显示
        </button>
      )}
      {all && threads.hasNextPage && (
        <button
          className="sidebar-show-more"
          disabled={threads.isFetchingNextPage}
          onClick={() => void threads.fetchNextPage()}
        >
          {threads.isFetchingNextPage && <LoaderCircle size={12} className="spin" />}加载更多
        </button>
      )}
      {all && (
        <button className="sidebar-show-more" onClick={() => setAll(false)}>
          收起显示
        </button>
      )}
    </section>
  );
}
