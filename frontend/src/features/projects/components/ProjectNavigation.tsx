import { useEffect, useState, type ReactNode } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { Folder, Plus, Pin, LoaderCircle } from 'lucide-react';
import { useProjects } from '../hooks/useProjects';
import { useNewConversation } from '../../chat/hooks/useNewConversation';
import { api } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import {
  projectThreadOrder,
  projectThreadPreview,
  visibleThreads,
  threadProject,
} from '../../chat/lib/sidebarNavigation';
import type { Project, Thread } from '../../../shared/types/api';
import { ProjectEditor } from './ProjectEditor';
import { ErrorText } from '../../../shared/ui/ui';
import { ProjectMenu } from './ProjectMenu';

type ThreadRenderer = (thread: Thread, readOnly?: boolean) => ReactNode;

export function ProjectNavigation({
  view,
  onNavigate,
  renderThread,
  selectedThread,
}: {
  view: 'active' | 'archived';
  onNavigate: () => void;
  renderThread: ThreadRenderer;
  selectedThread?: Thread;
}) {
  const projects = useProjects(view);
  const currentId = useWorkspace((state) => state.projectId);
  const [all, setAll] = useState(false);
  const [editor, setEditor] = useState<Project>();
  const rows = projects.data?.projects || [];
  // 项目多时仍保留当前项目的入口，其余项目可展开查看。
  const visible = all
    ? rows
    : rows.filter((project, index) => index < 5 || project.id === currentId);
  return (
    <section
      className="project-navigation"
      aria-label={view === 'archived' ? '已归档项目' : '项目'}
    >
      <ErrorText error={projects.error} />
      {projects.isPending && <p className="muted sidebar-empty">正在读取项目…</p>}
      {!projects.isPending && !rows.length && (
        <p className="muted sidebar-empty">{view === 'archived' ? '暂无归档项目' : '暂无项目'}</p>
      )}
      {visible.map((project) => (
        <ProjectGroup
          key={`${view}:${project.id}`}
          project={project}
          onNavigate={onNavigate}
          onEdit={() => setEditor(project)}
          renderThread={renderThread}
          selectedThread={selectedThread}
        />
      ))}
      {!all && visible.length < rows.length && (
        <button className="sidebar-show-more" onClick={() => setAll(true)}>
          展开显示
        </button>
      )}
      {all && rows.length > 5 && (
        <button className="sidebar-show-more" onClick={() => setAll(false)}>
          收起显示
        </button>
      )}
      {editor && <ProjectEditor project={editor} onClose={() => setEditor(undefined)} />}
    </section>
  );
}

function ProjectGroup({
  project,
  onNavigate,
  onEdit,
  renderThread,
  selectedThread,
}: {
  project: Project;
  onNavigate: () => void;
  onEdit: () => void;
  renderThread: ThreadRenderer;
  selectedThread?: Thread;
}) {
  const { projectId, expandedProjects, setProjectExpanded } = useWorkspace();
  const startConversation = useNewConversation();
  const current = projectId === project.id;
  const expanded = expandedProjects[project.id] ?? current;
  useEffect(() => {
    if (current && expandedProjects[project.id] === undefined) setProjectExpanded(project.id, true);
  }, [current, expandedProjects, project.id, setProjectExpanded]);
  const [all, setAll] = useState(false);
  const limit = all ? 50 : projectThreadPreview + 1;
  const threads = useInfiniteQuery({
    queryKey: ['project-threads', project.id, project.state, limit],
    initialPageParam: 0,
    queryFn: async ({ pageParam, signal }) => {
      const states = project.state === 'archived' ? ['active', 'archived'] : ['active'];
      const pages = await Promise.all(
        states.map((state) =>
          api<Thread[]>(
            `/threads?state=${state}&limit=${limit}&offset=${pageParam}`,
            { signal },
            project.id,
          ),
        ),
      );
      return { rows: pages.flat(), hasMore: pages.some((page) => page.length === limit) };
    },
    getNextPageParam: (page, _pages, previous) => (page.hasMore ? previous + limit : undefined),
    enabled: expanded,
    refetchInterval: 5000,
  });
  const rows = projectThreadOrder(threads.data?.pages.flatMap((page) => page.rows) || []);
  const matchingSelected =
    selectedThread &&
    threadProject(selectedThread) === project.id &&
    (selectedThread.state === 'active' ||
      (project.state === 'archived' && selectedThread.state === 'archived'))
      ? selectedThread
      : undefined;
  const visible = visibleThreads(rows, matchingSelected, all ? undefined : projectThreadPreview);
  return (
    <div className={`project-group ${current ? 'current' : ''}`}>
      <div className="project-navigation-row">
        <button
          className="project-name"
          title={project.name}
          aria-expanded={expanded}
          aria-controls={`project-conversations-${project.id}`}
          onClick={(event) => {
            // 双击只处理第一次点击，避免列表连续收放。
            if (event.detail > 1) return;
            setProjectExpanded(project.id, !expanded);
          }}
        >
          <Folder size={15} strokeWidth={1.5} />
          <span>{project.name}</span>
          {project.pinned_order !== null && <Pin size={10} />}
        </button>
        {project.state === 'active' && (
          <button
            className="project-hover-action"
            aria-label={`新建对话：${project.name}`}
            title="在此项目中新建对话"
            onClick={() => {
              if (startConversation(project.id)) onNavigate();
            }}
          >
            <Plus size={14} />
          </button>
        )}
        <ProjectMenu project={project} onEdit={onEdit} />
      </div>
      {expanded && (
        <div
          id={`project-conversations-${project.id}`}
          className="project-conversations"
          aria-label={`${project.name}的对话`}
        >
          <ErrorText error={threads.error} />
          {threads.isPending && <span className="muted project-no-chats">正在读取…</span>}
          {visible.map((thread) => renderThread(thread, project.state === 'archived'))}
          {threads.isSuccess && !rows.length && (
            <span className="muted project-no-chats">暂无对话</span>
          )}
          {!all && (rows.length > projectThreadPreview || threads.hasNextPage) && (
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
        </div>
      )}
    </div>
  );
}
