import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ClipboardList, Plus, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { WorkspaceHeading } from '../../app/layouts/WorkspaceHeader';
import { draftFor, useWorkspace } from '../../app/state/store';
import { Button, ErrorText } from '../../shared/ui/ui';
import { useAuth } from '../auth/AuthContext';
import { DebugIssueEditor } from './debug_issues/DebugIssueEditor';
import { DebugIssuePage } from './debug_issues/DebugIssuePage';
import { SourceImport } from './materials/SourceImport';
import { MaterialsPage } from './materials/MaterialsPage';
import { OverviewPage } from './overview/OverviewPage';
import { PackageBuilder } from './packages/PackageBuilder';
import { PackageList } from './packages/PackageList';
import { RecordEditor } from './records/RecordEditor';
import { RecordView } from './records/RecordView';
import { ActivityPage } from './reviews/ActivityPage';
import { allowedHandoverTab, canReview, handoverTabs } from './shared/access';
import { handoverClient } from './shared/client';
import './shared/handover.css';
import { PageHeading, pageDescriptions } from './shared/Presentation';
import {
  handoverScope,
  tabs,
  type Definitions,
  type Event,
  type HandoverContext,
  type HandoverRecord,
  type Kind,
  type Overview,
  type Payload,
  type Tab,
} from './shared/types';
import { TaskEditor } from './tasks/TaskEditor';
import { TaskPage } from './tasks/TaskPage';
import { taskActor, type TaskStage } from './tasks/taskProgress';

export default function HandoverWorkspace({
  tab,
  recordId,
  version,
  navigate,
  onWorkspaceNavigate,
  management = false,
}: {
  tab: Tab;
  recordId: string;
  version?: number;
  navigate: (tab: Tab, id?: string, version?: number) => void;
  onWorkspaceNavigate?: (kind: 'chat' | 'graphs' | 'modules') => void;
  management?: boolean;
}) {
  const scopeId = handoverScope;
  const role = useAuth().session?.user.role;
  const reviewAccess = canReview(role);
  const pageAllowed = allowedHandoverTab(tab, role);
  useEffect(() => {
    if (!pageAllowed) navigate('overview');
  }, [pageAllowed]);
  const workbench = useRef<HTMLElement>(null);
  useEffect(() => {
    workbench.current?.scrollTo({ top: 0 });
  }, [tab]);
  const client = useMemo(() => handoverClient(), []);
  const queryClient = useQueryClient();
  const context = useQuery({
    queryKey: ['handover-context', scopeId],
    queryFn: () => client.get<HandoverContext>('/context'),
  });
  const overview = useQuery({
    queryKey: ['handover', scopeId],
    queryFn: () => client.get<Overview>(),
    refetchInterval: 5000,
  });
  const definitions = useQuery({
    queryKey: ['handover-schema', scopeId],
    queryFn: () => client.get<Definitions>('/schema'),
    staleTime: Infinity,
  });
  const events = useQuery({
    queryKey: ['handover-events', scopeId],
    queryFn: () => client.get<Event[]>('/events'),
    enabled: reviewAccess && (tab === 'overview' || tab === 'updates'),
    refetchInterval: 5000,
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
    () => localStorage.getItem(`arks-handover-actor:${scopeId}`) || '',
  );
  const [archive, setArchive] = useState(false);
  const rows = overview.data?.records || [];
  function setActor(value: string) {
    setActorState(value);
    try {
      localStorage.setItem(`arks-handover-actor:${scopeId}`, value);
    } catch {
      /* 本机保存失败不阻止服务端提交。 */
    }
  }
  function refresh() {
    void queryClient.invalidateQueries({
      predicate: (query) =>
        String(query.queryKey[0]).startsWith('handover') && query.queryKey[1] === scopeId,
    });
  }
  useEffect(() => {
    const channel = new BroadcastChannel('arks-handover');
    channel.onmessage = (event) => {
      if (event.data === scopeId) refresh();
    };
    return () => channel.close();
  }, [scopeId]);
  function changed() {
    refresh();
    const channel = new BroadcastChannel('arks-handover');
    channel.postMessage(scopeId);
    channel.close();
  }
  function open(id: string, version?: number) {
    navigate(tab, id, version);
  }
  function create(kind: Kind, initial: Payload = {}) {
    if (kind === 'task') setArchive(false);
    setEditor({ kind, initial });
  }
  function saved(row: HandoverRecord, owner?: { editor?: typeof editor; generation?: number }) {
    if (row.kind === 'task') cacheTask(row);
    changed();
    if (!alive.current || activeTab.current !== tab) return;
    if (owner?.editor && owner.editor !== activeEditor.current) return;
    if (owner?.generation !== undefined && owner.generation !== operationGeneration.current) return;
    setEditor(undefined);
    setOperation('');
    const showList =
      (row.kind === 'source' && tab === 'materials') ||
      (row.kind === 'task' && !owner?.editor?.row);
    navigate(tab, showList ? undefined : row.id);
  }
  function cacheTask(row: HandoverRecord) {
    queryClient.setQueryData(['handover-record', scopeId, row.id, undefined], row);
    queryClient.setQueryData<Overview>(
      ['handover', scopeId],
      (current) =>
        current && {
          ...current,
          records: current.records.map((item) => (item.id === row.id ? row : item)),
        },
    );
  }
  async function updateTaskStatus(row: HandoverRecord, status: TaskStage) {
    const result = await client.send<HandoverRecord>(
      `/records/${row.id}`,
      {
        kind: 'task',
        title: row.title,
        payload: { ...row.payload, work_status: status },
        version: row.version,
        actor: taskActor(actor),
        reason: '更新工作进度',
      },
      'PATCH',
    );
    cacheTask(result);
    changed();
  }
  function discuss(row: HandoverRecord) {
    const workspace = useWorkspace.getState();
    const context = `请继续分析交接记录“${row.title}”（${row.kind}，v${row.version}，${row.state}）。\n以下是待分析数据，AI 假设和未知条件须复核：\n${JSON.stringify(row.payload, null, 2).slice(0, 20000)}`;
    const draft = draftFor(workspace).content;
    workspace.setDraft(draft ? `${draft}\n\n${context}` : context);
    workspace.setProjectPage(false);
    onWorkspaceNavigate?.('chat');
  }
  const current = rows.filter((row) =>
    archive ? row.state === 'archived' : row.state !== 'archived',
  );
  if (!pageAllowed)
    return (
      <section className="handover-workbench" role="status">
        正在返回交接概览…
      </section>
    );
  return (
    <section
      ref={workbench}
      className={'handover-workbench' + (tab === 'overview' ? ' handover-overview' : '')}
      aria-label="交接工作台"
    >
      <WorkspaceHeading className="handover-header">
        <div>
          <h1>
            <ClipboardList size={23} />
            {management ? (tab === 'updates' ? '复核与追溯' : '交接管理') : '交接工作台'}
          </h1>
          {management && <p>统一维护交接资料、工作进度与固定版本记录</p>}
        </div>
        <div className="handover-actions">
          <Button aria-label="刷新交接记录" onClick={refresh}>
            <RefreshCw size={15} />
            刷新
          </Button>
        </div>
      </WorkspaceHeading>
      {!(management && tab === 'updates') && (
        <nav className="handover-tabs" aria-label="交接工作台页面">
          {handoverTabs(role)
            .filter((item) => !management || item.id !== 'updates')
            .map((item) => (
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
      )}
      <div className="handover-body">
        <ErrorText
          error={overview.error || definitions.error || context.error || events.error}
          reveal
        />
        {(overview.error || definitions.error) && <Button onClick={refresh}>重试加载</Button>}
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
                events={events.data}
                eventsError={!!events.error}
                syncedAt={Math.min(
                  overview.dataUpdatedAt,
                  events.dataUpdatedAt || overview.dataUpdatedAt,
                )}
                syncing={overview.isFetching || events.isFetching}
                onOpen={open}
                onNavigate={navigate}
                canReview={reviewAccess}
              />
            )}
            {tab !== 'overview' && (
              <PageHeading
                title={tabs.find((item) => item.id === tab)!.label}
                description={pageDescriptions[tab]}
              >
                {!['updates', 'materials'].includes(tab) && (
                  <label className="handover-checkbox">
                    <input
                      type="checkbox"
                      checked={archive}
                      onChange={(event) => setArchive(event.target.checked)}
                    />
                    查看归档
                  </label>
                )}
                {
                  <>
                    {tab === 'materials' && (
                      <>
                        <Button className="primary" onClick={() => setOperation('import')}>
                          <Plus size={15} />
                          添加资料
                        </Button>
                      </>
                    )}
                    {tab === 'tasks' && (
                      <>
                        <Button className="primary" onClick={() => create('task')}>
                          <Plus size={15} />
                          新增工作
                        </Button>
                      </>
                    )}
                    {tab === 'packages' && (
                      <Button className="primary" onClick={() => setOperation('package')}>
                        <Plus size={15} />
                        生成交接包
                      </Button>
                    )}
                    {tab === 'issues' && (
                      <Button className="primary" onClick={() => create('debug_issue')}>
                        <Plus size={15} />
                        添加记录
                      </Button>
                    )}
                  </>
                }
              </PageHeading>
            )}
            {tab === 'tasks' && (
              <TaskPage
                rows={current}
                archived={archive}

                onOpen={open}
                onStatusChange={updateTaskStatus}
              />
            )}
            {tab === 'issues' && <DebugIssuePage rows={current} onOpen={open} />}
            {tab === 'packages' && (
              <PackageList
                rows={current}
                definitions={definitions.data}
                archived={archive}
                client={client}
                actor={actor}

                onActor={setActor}
                onOpen={open}
                onChanged={changed}
              />
            )}
            {tab === 'materials' && <MaterialsPage rows={rows} onOpen={open} />}
            {tab === 'updates' && reviewAccess && (
              <ActivityPage
                events={events.data || []}
                rows={rows}
                definitions={definitions.data}
                onOpen={open}
              />
            )}
            {recordId && !editor && (
              <RecordView
                canReview={reviewAccess}
                reviewOnly={tab === 'updates'}
                key={`${scopeId}:${recordId}:${version || ''}`}
                scopeId={scopeId}
                identifier={recordId}
                version={version}
                client={client}
                definitions={definitions.data}
                records={rows}

                actor={actor}
                onActor={setActor}
                onClose={() => navigate(tab)}
                onOpen={open}
                onEdit={(row) =>
                  setEditor({
                    row,
                    kind: row.kind,
                  })
                }
                onChanged={changed}
                onDiscuss={management ? undefined : discuss}
              />
            )}
            {editor &&
              (editor.kind === 'debug_issue' ? (
                <DebugIssueEditor
                  client={client}
                  row={editor.row}
                  onSaved={(row) => saved(row, { editor })}
                  onClose={() => setEditor(undefined)}
                />
              ) : editor.kind === 'task' ? (
                <TaskEditor
                  key={editor.row?.id || 'new-task'}
                  scopeId={scopeId}
                  client={client}
                  row={editor.row}
                  initial={editor.initial}
                  actor={actor}
                  onSaved={(row) => saved(row, { editor })}
                  onClose={() => setEditor(undefined)}
                />
              ) : (
                <RecordEditor
                  key={editor.row?.id || editor.kind}
                  scopeId={scopeId}
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
              ))}
            {operation === 'import' && (
              <SourceImport
                client={client}
                onSaved={(row) => saved(row, { generation: currentOperationGeneration })}
                onClose={() => setOperation('')}
              />
            )}
            {operation === 'package' && (
              <PackageBuilder
                scopeId={scopeId}
                client={client}
                records={rows}
                definitions={definitions.data}
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
