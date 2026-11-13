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
import { OverflowText } from '../../../shared/ui/OverflowText';
import { useSidebarDrag } from '../../chat/components/sidebarDrag';

type ThreadRenderer = (thread: Thread) => ReactNode;

export function ProjectNavigation({
  onNavigate,
  renderThread,
  selectedThread,
}: {
  onNavigate: () => void;
  renderThread: ThreadRenderer;
  selectedThread?: Thread;
}) {
  const projects = useProjects();
  const currentId = useWorkspace((state) => state.projectId);
  const [all, setAll] = useState(false);
  const [editor, setEditor] = useState<Project>();
  const rows = projects.data?.projects || [];
  // 项目多时仍保留当前项目的入口，其余项目可展开查看。
  const visible = all
    ? rows
    : rows.filter((project, index) => index < 5 || project.id === currentId);
  return (
    <section className="project-navigation" aria-label="项目">
      <ErrorText error={projects.error} />
      {projects.isPending && <p className="muted sidebar-empty">正在读取项目…</p>}
      {!projects.isPending && !rows.length && <p className="muted sidebar-empty">暂无项目</p>}
      {visible.map((project) => (
        <ProjectGroup
          key={project.id}
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
  const drag = useSidebarDrag();
  const pinnedGroup = project.pinned_order !== null ? 'pinned' : 'normal';
  const dragging = drag?.state?.kind === 'project' && drag.state.id === project.id;
  const dropTarget = drag?.state?.overProjectId === project.id;
  const projectDrag = drag?.state?.kind === 'project';
  const dropBefore = dropTarget && projectDrag && drag?.state?.beforeId === project.id;
  const dropAfter = dropTarget && projectDrag && drag?.state?.beforeId !== project.id;
  useEffect(() => {
    if (current && expandedProjects[project.id] === undefined) setProjectExpanded(project.id, true);
  }, [current, expandedProjects, project.id, setProjectExpanded]);
  const [all, setAll] = useState(false);
  const limit = all ? 50 : projectThreadPreview + 1;
  const threads = useInfiniteQuery({
    queryKey: ['project-threads', project.id, limit],
    initialPageParam: 0,
    queryFn: async ({ pageParam, signal }) => {
      return api<Thread[]>(`/threads?limit=${limit}&offset=${pageParam}`, { signal }, project.id);
    },
    getNextPageParam: (page, _pages, previous) =>
      page.length === limit ? previous + limit : undefined,
    enabled: expanded,
    refetchInterval: 5000,
  });
  const rows = projectThreadOrder(threads.data?.pages.flat() || []);
  const matchingSelected =
    selectedThread &&
    threadProject(selectedThread) === project.id &&
    selectedThread.state === 'active'
      ? selectedThread
      : undefined;
  const visible = visibleThreads(rows, matchingSelected, all ? undefined : projectThreadPreview);
  return (
    <div
      className={`project-group ${current ? 'current' : ''} ${dragging ? 'dragging' : ''} ${dropTarget ? 'drop-target' : ''} ${dropBefore ? 'drop-before' : ''} ${dropAfter ? 'drop-after' : ''}`}
      data-project-id={project.id}
      data-pinned={pinnedGroup === 'pinned' ? 'true' : 'false'}
      onDragOver={(event) => {
        if (!drag?.state) return;
        event.preventDefault();
        event.stopPropagation();
        if (drag.state.kind === 'thread') {
          event.dataTransfer.dropEffect = 'none';
          drag.hoverNone();
          return;
        }
        if (drag.state.id === project.id || drag.state.group !== pinnedGroup) {
          event.dataTransfer.dropEffect = 'none';
          drag.hoverNone();
          return;
        }
        const rows = Array.from(
          document.querySelectorAll<HTMLElement>(
            `[data-project-id][data-pinned="${pinnedGroup === 'pinned' ? 'true' : 'false'}"]`,
          ),
        );
        const index = rows.indexOf(event.currentTarget);
        const rect = event.currentTarget.getBoundingClientRect();
        const after = event.clientY > rect.top + rect.height / 2;
        const beforeId = after ? (rows[index + 1]?.dataset.projectId ?? null) : project.id;
        event.dataTransfer.dropEffect = 'move';
        drag.hoverProject(project.id, beforeId);
      }}
      onDrop={(event) => {
        if (!drag?.state) return;
        event.preventDefault();
        event.stopPropagation();
        void drag.drop();
      }}
    >
      <div className="project-navigation-row">
        <button
          className="project-name"
          draggable
          onDragStart={(event) => {
            event.stopPropagation();
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', project.id);
            drag?.start('project', project.id, pinnedGroup);
          }}
          onDragEnd={() => drag?.end()}
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
          <OverflowText className="project-title">{project.name}</OverflowText>
          {project.pinned_order !== null && <Pin size={10} />}
        </button>
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
          {visible.map((thread) => renderThread(thread))}
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
