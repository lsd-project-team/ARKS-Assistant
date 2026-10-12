import { useProjectApi } from '../hooks/useProjectApi';
import { useState } from 'react';
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query';
import { Folder, Plus, Settings2, Pin, Archive, Trash2, Search, FileText } from 'lucide-react';
import { useCurrentProject, useProjects } from '../hooks/useProjects';
import { useNewConversation } from '../hooks/useNewConversation';
import { useWorkspace } from '../lib/store';
import { apiUrl, jsonBody, query } from '../lib/api';
import type { Memory, Thread } from '../types';
import { Button, ErrorText, Modal } from './ui';
import { ProjectEditor } from './ProjectEditor';
import { MoveThreadsDialog } from './MoveThreadsDialog';
import { Select } from './Select';
import { toast } from '../lib/toasts';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { ProjectDocuments } from './ProjectDocuments';

export function ProjectHome({ onMaterials }: { onMaterials: () => void }) {
  const api = useProjectApi();
  const current = useCurrentProject();
  const projects = useProjects();
  const startConversation = useNewConversation();
  const { projectId, selectThread, switchProject } = useWorkspace();
  const [tab, setTab] = useState<'chats' | 'materials'>('chats');
  const [filter, setFilter] = useState('');
  const [state, setState] = useState('active');
  const [editor, setEditor] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [disposition, setDisposition] = useState('independent');
  const [selected, setSelected] = useState<string[]>([]);
  const [moving, setMoving] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const cache = useQueryClient();
  const project = current.data;
  const settled = useDebouncedValue(filter.trim());
  const threads = useInfiniteQuery({
    queryKey: ['threads', 'project-home', state, settled],
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) =>
      api<Thread[]>(
        `/threads?state=${state}&query=${query(settled)}&limit=50&offset=${pageParam}`,
        { signal },
        projectId,
      ),
    getNextPageParam: (rows, _pages, previous) => (rows.length === 50 ? previous + 50 : undefined),
  });
  const rows = filter.trim() === settled ? threads.data?.pages.flat() || [] : [];
  const memories = useQuery({
    queryKey: ['memories'],
    queryFn: () => api<Memory[]>('/memories'),
    enabled: tab === 'materials',
  });
  async function update(changes: unknown) {
    setPending(true);
    setError(undefined);
    try {
      await api(`/projects/${projectId}`, { method: 'PATCH', body: jsonBody(changes) });
      await Promise.all([
        cache.invalidateQueries({ queryKey: ['project'] }),
        cache.invalidateQueries({ queryKey: ['projects'] }),
      ]);
      toast('项目已更新');
    } catch (reason) {
      setError(reason);
    } finally {
      setPending(false);
    }
  }
  async function remove() {
    setPending(true);
    setError(undefined);
    try {
      await api(`/projects/${projectId}?disposition=${disposition}`, { method: 'DELETE' });
      await cache.invalidateQueries({ queryKey: ['projects'] });
      const next = projects.data?.projects.find((item) => item.id !== projectId);
      switchProject(next?.id || 'independent', !!next);
      toast('项目已移除，源码文件保留');
    } catch (reason) {
      setError(reason);
    } finally {
      setPending(false);
    }
  }
  async function exportProject() {
    setPending(true);
    setError(undefined);
    try {
      const response = await fetch(apiUrl(`/projects/${projectId}/export`));
      if (!response.ok) throw new Error('导出失败，请稍后重试');
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = `${(project?.name || '项目').replace(/[<>:"/\\|?*]/g, '_')}.zip`;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
      toast('项目归档已导出');
    } catch (reason) {
      setError(reason);
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="project-home" aria-label="项目首页">
      <div className="project-home-content">
        <header className="project-home-header">
          <div>
            <div className="project-eyebrow">
              <Folder size={16} />
              项目{project?.state === 'archived' ? ' · 已归档' : ''}
            </div>
            <h1>{project?.name || '正在读取项目…'}</h1>
            <p>{project?.description || '把相关对话、源码和资料放在一起。'}</p>
          </div>
          <div className="project-home-actions">
            <Button
              className="icon-button"
              aria-label={project?.pinned_order === null ? '置顶项目' : '取消置顶项目'}
              disabled={pending || !project}
              onClick={() => void update({ pinned: project?.pinned_order === null })}
            >
              <Pin size={16} />
            </Button>
            <Button disabled={!project} onClick={() => setEditor(true)}>
              <Settings2 size={15} />
              项目设置
            </Button>
          </div>
        </header>
        <ErrorText error={current.error || error} />
        <div className="project-home-bar">
          <div className="project-home-tabs">
            <button aria-pressed={tab === 'chats'} onClick={() => setTab('chats')}>
              对话
            </button>
            <button aria-pressed={tab === 'materials'} onClick={() => setTab('materials')}>
              资料与指令
            </button>
          </div>
          {project?.state === 'archived' ? (
            <Button
              className="primary"
              disabled={pending}
              onClick={() => void update({ state: 'active' })}
            >
              恢复项目
            </Button>
          ) : (
            <Button
              className="primary"
              disabled={!project}
              onClick={() => startConversation(projectId)}
            >
              <Plus size={15} />
              新对话
            </Button>
          )}
        </div>
        {tab === 'chats' ? (
          <>
            <div className="project-chat-tools">
              <label className="search-box">
                <Search size={15} />
                <input
                  aria-label="搜索项目对话"
                  placeholder="搜索此项目的对话…"
                  value={filter}
                  onChange={(event) => {
                    setFilter(event.target.value);
                    setSelected([]);
                  }}
                />
              </label>
              <Select
                value={state}
                onValueChange={(value) => {
                  setState(value);
                  setSelected([]);
                }}
                aria-label="项目对话状态"
              >
                <option value="active">最近对话</option>
                <option value="archived">已归档</option>
                <option value="deleted">回收站</option>
              </Select>
            </div>
            {!!selected.length && (
              <div className="project-batch-bar">
                <span>已选 {selected.length} 个对话</span>
                <Button onClick={() => setMoving(true)}>移动至项目</Button>
                <Button onClick={() => setSelected([])}>取消选择</Button>
              </div>
            )}
            <ErrorText error={threads.error} />
            <div className="project-chat-list">
              {rows.map((thread) => (
                <div className="project-chat-row" key={thread.id}>
                  <input
                    type="checkbox"
                    aria-label={`选择对话：${thread.title}`}
                    checked={selected.includes(thread.id)}
                    disabled={thread.state === 'deleted'}
                    onChange={(event) =>
                      setSelected(
                        event.target.checked && selected.length < 200
                          ? [...selected, thread.id]
                          : selected.filter((id) => id !== thread.id),
                      )
                    }
                  />
                  <button
                    disabled={thread.state === 'deleted'}
                    onClick={() => selectThread(thread.id)}
                  >
                    <strong>{thread.title}</strong>
                    <small>
                      {thread.message_count || 0} 条消息 ·{' '}
                      {new Date(thread.updated_at).toLocaleDateString('zh-CN')}
                      {thread.latest_status === 'running' ? ' · 正在回复' : ''}
                    </small>
                  </button>
                </div>
              ))}
            </div>
            {threads.hasNextPage && (
              <Button
                disabled={threads.isFetchingNextPage}
                onClick={() => void threads.fetchNextPage()}
              >
                {threads.isFetchingNextPage ? '正在读取…' : '加载更多对话'}
              </Button>
            )}
            {threads.isSuccess && filter.trim() === settled && !rows.length && (
              <div className="project-empty">
                <Folder size={28} />
                <h2>{filter ? '没有匹配的对话' : '从这个项目的新对话开始'}</h2>
                <p>项目中的对话各自保留历史，共享你设置的指令和资料。</p>
                {!filter && state === 'active' && project?.state === 'active' && (
                  <Button onClick={() => startConversation(projectId)}>新对话</Button>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="project-materials">
            <ProjectDocuments
              projectId={projectId}
              readOnly={project?.state === 'archived' || !project}
            />
            <article>
              <h2>
                <Folder size={16} />
                源码目录
              </h2>
              <p className="project-directory">{project?.source_root || '尚未关联源码目录'}</p>
              {project?.source_folders?.map((folder) => (
                <p className="project-directory" key={folder.source_id}>
                  <strong>{folder.label}</strong>
                  <br />
                  {folder.root}
                </p>
              ))}
              <Button onClick={() => setEditor(true)}>
                {project?.source_root ? '修改关联' : '关联源码'}
              </Button>
            </article>
            <article>
              <h2>
                <Settings2 size={16} />
                项目指令
              </h2>
              <p className="project-instructions">
                {project?.instructions || '尚未设置。你可以指定回答语言、分析习惯和项目目标。'}
              </p>
              <Button onClick={() => setEditor(true)}>编辑指令</Button>
            </article>
            <article>
              <h2>
                <FileText size={16} />
                已保存的项目知识
              </h2>
              <ErrorText error={memories.error} />
              {memories.data
                ?.filter((memory) => memory.scope === 'project')
                .map((memory) => (
                  <div className="project-memory" key={memory.name}>
                    <strong>{memory.name}</strong>
                    <p>{memory.content.slice(0, 180)}</p>
                  </div>
                ))}
              {!memories.data?.some((memory) => memory.scope === 'project') && (
                <p className="muted">在对话中保存的项目知识会出现在这里。</p>
              )}
              <Button onClick={onMaterials}>管理知识与记忆</Button>
            </article>
            {project?.knowledge_available && (
              <article>
                <h2>流程图谱与功能说明</h2>
                <p>此源码项目保留了已复核的生产流程和功能资料。</p>
              </article>
            )}
          </div>
        )}
        <footer className="project-home-footer">
          <Button disabled={pending || !project} onClick={() => void exportProject()}>
            导出项目
          </Button>
          <Button
            disabled={pending}
            onClick={() =>
              void update({ state: project?.state === 'archived' ? 'active' : 'archived' })
            }
          >
            <Archive size={14} />
            {project?.state === 'archived' ? '恢复项目' : '归档项目'}
          </Button>
          <Button disabled={pending} onClick={() => setRemoving(true)}>
            <Trash2 size={14} />
            移除项目
          </Button>
        </footer>
        {editor && project && <ProjectEditor project={project} onClose={() => setEditor(false)} />}
        {moving && (
          <MoveThreadsDialog
            ids={selected}
            onClose={() => setMoving(false)}
            onMoved={() => setSelected([])}
          />
        )}
        <Modal
          open={removing}
          onClose={() => !pending && setRemoving(false)}
          title="移除项目"
          description="源码文件和已保存的记忆保留。"
          className="project-move-dialog"
        >
          <div className="dialog-body project-form">
            <p>移除“{project?.name}”后，项目中的对话如何处理？</p>
            <Select
              value={disposition}
              onValueChange={setDisposition}
              aria-label="移除项目后的对话处理"
            >
              <option value="independent">保留为独立对话</option>
              <option value="trash">移入回收站，可单独恢复</option>
            </Select>
            <ErrorText error={error} />
          </div>
          <div className="modal-footer">
            <Button disabled={pending} onClick={() => setRemoving(false)}>
              取消
            </Button>
            <Button disabled={pending} onClick={() => void remove()}>
              移除项目
            </Button>
          </div>
        </Modal>
      </div>
    </section>
  );
}
