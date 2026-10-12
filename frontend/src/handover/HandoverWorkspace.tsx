import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ClipboardList, Plus, RefreshCw } from 'lucide-react';
import { Button, ErrorText } from '../components/ui';
import { useCurrentProject } from '../hooks/useProjects';
import { draftFor, useWorkspace } from '../lib/store';
import { handoverClient } from './client';
import { RecordEditor } from './RecordEditor';
import { RecordCard, RecordView } from './RecordView';
import { AIOperation, PackageBuilder, SourceImport } from './Operations';
import { ActivityPage, OverviewPage, TaskPage } from './Pages';
import { TemplateTools } from './TemplateTools';
import {
  ids,
  tabs,
  text,
  type Definitions,
  type Event,
  type HandoverRecord,
  type Kind,
  type Overview,
  type Payload,
  type Tab,
} from './types';
import './handover.css';

export default function HandoverWorkspace({
  tab,
  recordId,
  version,
  navigate,
  onLegacyNavigate,
}: {
  tab: Tab;
  recordId: string;
  version?: number;
  navigate: (tab: Tab, id?: string, version?: number) => void;
  onLegacyNavigate: (kind: 'chat' | 'graphs' | 'modules') => void;
}) {
  const projectId = useWorkspace((state) => state.projectId);
  const project = useCurrentProject();
  const client = useMemo(() => handoverClient(projectId), [projectId]);
  const queryClient = useQueryClient();
  useEffect(() => {
    const narrow = window.matchMedia('(max-width: 800px)');
    const fit = () => {
      if (narrow.matches) useWorkspace.getState().setLayout({ collapsed: true });
    };
    fit();
    narrow.addEventListener('change', fit);
    return () => narrow.removeEventListener('change', fit);
  }, []);
  const usable = !!projectId && projectId !== 'independent';
  const overview = useQuery({
    queryKey: ['handover', projectId],
    queryFn: () => client.get<Overview>(),
    enabled: usable,
    refetchInterval: 5000,
  });
  const definitions = useQuery({
    queryKey: ['handover-schema', projectId],
    queryFn: () => client.get<Definitions>('/schema'),
    enabled: usable,
    staleTime: Infinity,
  });
  const events = useQuery({
    queryKey: ['handover-events', projectId],
    queryFn: () => client.get<Event[]>('/events'),
    enabled: usable && tab === 'updates',
  });
  const [editor, setEditor] = useState<{ kind: Kind; row?: HandoverRecord; initial?: Payload }>();
  const [operation, setOperationValue] = useState('');
  const alive = useRef(true);
  const activeTab = useRef(tab);
  activeTab.current = tab;
  const activeEditor = useRef(editor);
  activeEditor.current = editor;
  const operationGeneration = useRef(0);
  const currentOperationGeneration = operationGeneration.current;
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  function setOperation(value: string) {
    operationGeneration.current += 1;
    setOperationValue(value);
  }
  const [actor, setActorState] = useState(
    () => localStorage.getItem(`arks-handover-actor:${projectId}`) || '',
  );
  const [error, setError] = useState<unknown>();
  const [archive, setArchive] = useState(false);
  const rows = overview.data?.records || [];
  const readOnly = project.data?.state !== 'active';
  function setActor(value: string) {
    setActorState(value);
    try {
      localStorage.setItem(`arks-handover-actor:${projectId}`, value);
    } catch {
      /* 本机保存失败不阻止服务端提交。 */
    }
  }
  function refresh() {
    void queryClient.invalidateQueries({
      predicate: (query) =>
        String(query.queryKey[0]).startsWith('handover') && query.queryKey[1] === projectId,
    });
  }
  useEffect(() => {
    const channel = new BroadcastChannel('arks-handover');
    channel.onmessage = (event) => {
      if (event.data === projectId) refresh();
    };
    return () => channel.close();
  }, [projectId]);
  function changed() {
    refresh();
    const channel = new BroadcastChannel('arks-handover');
    channel.postMessage(projectId);
    channel.close();
  }
  function open(id: string, version?: number) {
    navigate(tab, id, version);
  }
  function create(kind: Kind, initial: Payload = {}) {
    setEditor({ kind, initial });
  }
  function saved(row: HandoverRecord, owner?: { editor?: typeof editor; generation?: number }) {
    changed();
    if (
      !alive.current ||
      useWorkspace.getState().projectId !== projectId ||
      activeTab.current !== tab
    )
      return;
    if (owner?.editor && owner.editor !== activeEditor.current) return;
    if (owner?.generation !== undefined && owner.generation !== operationGeneration.current) return;
    setEditor(undefined);
    setOperation('');
    navigate(tab, row.id);
  }
  function discuss(row: HandoverRecord) {
    const workspace = useWorkspace.getState();
    if (workspace.projectId !== row.project_id) return;
    const context = `请继续分析交接记录“${row.title}”（${row.kind}，v${row.version}，${row.state}）。\n以下是待分析数据，AI 假设和未知条件须复核：\n${JSON.stringify(row.payload, null, 2).slice(0, 20000)}`;
    const draft = draftFor(workspace).content;
    workspace.setDraft(draft ? `${draft}\n\n${context}` : context);
    workspace.setProjectPage(false);
    onLegacyNavigate('chat');
  }
  async function openCurrentSource(row: HandoverRecord) {
    const result = await client.get<{ changed: boolean }>(`/sources/${row.id}/compare`);
    if (!alive.current || useWorkspace.getState().projectId !== projectId) return;
    if (result.changed) throw new Error('当前源码已变化，请先查看固定快照，或重新捕获并复核来源。');
    const workspace = useWorkspace.getState();
    workspace.openFile(text(row.payload.path));
    workspace.setWorkspaceOpen(true);
    workspace.setProjectPage(false);
    workspace.setMobile('code');
    onLegacyNavigate('chat');
  }
  async function jobAction(row: HandoverRecord, cancel: boolean) {
    try {
      if (cancel) await client.send(`/ai/${row.id}/cancel`, {});
      else
        await client.send('/ai', {
          action: row.payload.action,
          record_ids: ids(row.payload.record_ids),
          actor,
        });
      changed();
    } catch (error) {
      setError(error);
    }
  }
  if (!usable)
    return (
      <section className="handover-workbench">
        <div className="handover-empty">
          <ClipboardList size={30} />
          <h1>交接工作台</h1>
          <p>先在左侧选择或创建项目，交接资料和工作项会按项目保存。</p>
        </div>
      </section>
    );
  const current = rows.filter((row) =>
    archive ? row.state === 'archived' : row.state !== 'archived',
  );
  const groups: Record<Tab, Kind[]> = {
    overview: [],
    materials: ['source', 'interview', 'candidate'],
    tasks: ['task'],
    design: ['decision', 'constraint', 'baseline', 'framework', 'training', 'issue'],
    packages: ['package', 'receipt'],
    updates: [],
  };
  return (
    <section className="handover-workbench" aria-label="交接工作台">
      <header className="handover-header">
        <div>
          <span className="handover-eyebrow">{project.data?.name || '当前项目'}</span>
          <h1>
            <ClipboardList size={23} />
            交接工作台
          </h1>
          <p>把未完成工作、设计依据与设备条件交给下一位接手人</p>
        </div>
        <div className="handover-actions">
          <Button aria-label="刷新交接记录" onClick={refresh}>
            <RefreshCw size={15} />
            刷新
          </Button>
          {!readOnly && (
            <Button className="primary" onClick={() => create('task')}>
              <Plus size={15} />
              新增工作
            </Button>
          )}
        </div>
      </header>
      <nav className="handover-tabs" aria-label="交接工作台页面">
        {tabs.map((item) => (
          <button
            key={item.id}
            aria-current={tab === item.id ? 'page' : undefined}
            className={tab === item.id ? 'active' : ''}
            onClick={() => {
              navigate(item.id);
            }}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <div className="handover-body">
        <ErrorText error={error || overview.error || definitions.error || events.error} reveal />
        {(overview.error || definitions.error) && <Button onClick={refresh}>重试加载</Button>}
        {readOnly && project.data && (
          <p className="handover-notice">此项目已归档，交接内容只读。</p>
        )}
        {(overview.isPending || definitions.isPending) && (
          <p className="handover-empty" role="status">
            正在加载交接工作台…
          </p>
        )}
        {overview.data && definitions.data && (
          <>
            {tab === 'overview' && (
              <OverviewPage
                overview={overview.data}
                definitions={definitions.data}
                onOpen={open}
                onNavigate={navigate}
                onNew={create}
                onImport={() => setOperation('import')}
                onKnowledge={onLegacyNavigate}
                knowledgeAvailable={!!project.data?.knowledge_available}
                readOnly={readOnly}
              />
            )}
            {tab !== 'overview' && tab !== 'updates' && (
              <div className="handover-toolbar">
                <h2>{tabs.find((item) => item.id === tab)?.label}</h2>
                <label className="handover-checkbox">
                  <input
                    type="checkbox"
                    checked={archive}
                    onChange={(event) => setArchive(event.target.checked)}
                  />
                  查看归档
                </label>
                {!readOnly && (
                  <>
                    {tab === 'materials' && (
                      <>
                        <Button onClick={() => setOperation('import')}>添加资料</Button>
                        <Button onClick={() => create('interview')}>记录访谈</Button>
                        <Button onClick={() => setOperation('extract')}>AI 提取候选</Button>
                      </>
                    )}
                    {tab === 'design' && (
                      <>
                        {(
                          ['decision', 'constraint', 'framework', 'training', 'issue'] as Kind[]
                        ).map((kind) => (
                          <Button key={kind} onClick={() => create(kind)}>
                            新增{definitions.data!.kinds[kind]}
                          </Button>
                        ))}
                        <Button onClick={() => setOperation('framework')}>AI 整理框架</Button>
                        <Button onClick={() => setOperation('training')}>AI 整理培训</Button>
                      </>
                    )}
                    {tab === 'tasks' && (
                      <Button onClick={() => setOperation('plan')}>AI 起草接续计划</Button>
                    )}
                    {tab === 'packages' && (
                      <Button className="primary" onClick={() => setOperation('package')}>
                        生成交接包
                      </Button>
                    )}
                  </>
                )}
              </div>
            )}
            {tab === 'tasks' && (
              <TaskPage
                rows={current}
                definitions={definitions.data}
                blocks={overview.data.blocks}
                onOpen={open}
              />
            )}
            {['materials', 'design', 'packages'].includes(tab) && (
              <>
                {groups[tab].map((kind) => (
                  <section className="handover-group" key={kind}>
                    <h3>{definitions.data!.kinds[kind]}</h3>
                    <div className="handover-cards">
                      {current
                        .filter((row) => row.kind === kind)
                        .map((row) => (
                          <RecordCard
                            key={row.id}
                            row={row}
                            definitions={definitions.data!}
                            onOpen={open}
                          />
                        ))}
                    </div>
                    {!current.some((row) => row.kind === kind) && (
                      <p className="handover-empty handover-empty-small">
                        暂无{definitions.data!.kinds[kind]}记录。
                      </p>
                    )}
                  </section>
                ))}
              </>
            )}
            {tab === 'materials' && (
              <section className="handover-panel">
                <h3>AI 作业</h3>
                {rows
                  .filter((row) => row.kind === 'job')
                  .sort((a, b) => b.created_at.localeCompare(a.created_at))
                  .map((row) => (
                    <div className="handover-job" key={row.id}>
                      <div>
                        <strong>{row.title}</strong>
                        <p>
                          {
                            (
                              {
                                queued: '等待运行',
                                running: '正在分析',
                                succeeded: ids(row.payload.result_ids).length
                                  ? '候选已生成，请审核'
                                  : '分析完成，未找到有来源支持的候选',
                                failed: '运行失败',
                                cancelled: '已取消',
                                interrupted: '服务重启中断',
                              } as Record<string, string>
                            )[text(row.payload.status)]
                          }
                        </p>
                        <small>{text(row.payload.error)}</small>
                      </div>
                      {!readOnly && (
                        <Button
                          disabled={
                            !actor.trim() &&
                            !['running', 'queued'].includes(text(row.payload.status))
                          }
                          onClick={() =>
                            void jobAction(
                              row,
                              ['running', 'queued'].includes(text(row.payload.status)),
                            )
                          }
                        >
                          {['running', 'queued'].includes(text(row.payload.status))
                            ? '取消运行'
                            : '使用当前版本重新生成'}
                        </Button>
                      )}
                    </div>
                  ))}
                {!rows.some((row) => row.kind === 'job') && (
                  <p className="handover-empty handover-empty-small">尚未运行 AI 分析。</p>
                )}
              </section>
            )}
            {tab === 'updates' && (
              <ActivityPage
                events={events.data || []}
                rows={rows}
                definitions={definitions.data}
                onOpen={open}
              />
            )}
            {tab === 'packages' && (
              <TemplateTools
                client={client}
                definitions={definitions.data}
                actor={actor}
                onActor={setActor}
                readOnly={readOnly}
                onSaved={saved}
              />
            )}
            {recordId && !editor && (
              <RecordView
                key={`${projectId}:${recordId}:${version || ''}`}
                projectId={projectId}
                identifier={recordId}
                version={version}
                client={client}
                definitions={definitions.data}
                records={rows}
                blocks={overview.data.blocks[recordId] || []}
                readOnly={readOnly}
                actor={actor}
                onActor={setActor}
                onClose={() => navigate(tab)}
                onOpen={open}
                onEdit={(row) =>
                  setEditor({
                    row,
                    kind:
                      row.kind === 'candidate' ? (text(row.payload.target_kind) as Kind) : row.kind,
                  })
                }
                onNew={create}
                onChanged={changed}
                onDiscuss={discuss}
                onCurrentSource={openCurrentSource}
              />
            )}
            {editor && !readOnly && (
              <RecordEditor
                key={editor.row?.id || editor.kind}
                projectId={projectId}
                client={client}
                definitions={definitions.data}
                records={rows}
                kind={editor.kind}
                row={editor.row}
                initial={editor.initial}
                actor={actor}
                onActor={setActor}
                onSaved={(row) => saved(row, { editor })}
                onClose={() => setEditor(undefined)}
              />
            )}
            {operation === 'import' && !readOnly && (
              <SourceImport
                records={rows}
                projectId={projectId}
                client={client}
                actor={actor}
                onActor={setActor}
                onSaved={(row) => saved(row, { generation: currentOperationGeneration })}
                onClose={() => setOperation('')}
              />
            )}
            {['extract', 'plan', 'framework', 'training'].includes(operation) && !readOnly && (
              <AIOperation
                client={client}
                records={rows}
                definitions={definitions.data}
                action={operation}
                actor={actor}
                onActor={setActor}
                onSaved={() => {
                  changed();
                  if (
                    !alive.current ||
                    useWorkspace.getState().projectId !== projectId ||
                    activeTab.current !== tab ||
                    operationGeneration.current !== currentOperationGeneration
                  )
                    return;
                  setOperation('');
                  navigate('materials');
                }}
                onClose={() => setOperation('')}
              />
            )}
            {operation === 'package' && !readOnly && (
              <PackageBuilder
                projectId={projectId}
                client={client}
                records={rows}
                definitions={definitions.data}
                actor={actor}
                onActor={setActor}
                onSaved={(row) => saved(row, { generation: currentOperationGeneration })}
                onClose={() => setOperation('')}
              />
            )}
          </>
        )}
      </div>
    </section>
  );
}
