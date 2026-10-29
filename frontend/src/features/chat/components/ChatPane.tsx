import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { X, FileCode2, ChevronDown, RotateCcw, Folders } from 'lucide-react';
import { api as request, jsonBody } from '../../../app/api/client';
import { useWorkspace, draftFor, draftKey, type ConversationDraft } from '../../../app/state/store';
import { useRunStream } from '../hooks/useRunStream';
import type {
  ModelPreference,
  QueuedQuestion,
  Run,
  SourceOptions,
} from '../../../shared/types/api';
import { AnswerMarkdown } from './AnswerMarkdown';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useChatScroll } from '../hooks/useChatScroll';
import { MessageBubble } from './MessageBubble';
import { ToolActivity } from './ToolActivity';
import { ContextDialog } from './ContextDialog';
import { ChatComposer } from './ChatComposer';
import { ComposerContext } from './ComposerContext';
import { matchingCommands, type ComposerCommand } from '../lib/composerCommands';
import { useConversation } from '../hooks/useConversation';
import { ReplyVersions } from './ReplyVersions';
import { SelectionPreview } from './SelectionPreview';
import type { Selection } from '../../../shared/types/api';
import { useQuestionQueue } from '../hooks/useQuestionQueue';
import { QuestionQueuePanel } from './QuestionQueue';
import { resolvedSources } from '../../settings/lib/sourceOptions';
import { RunActivity } from './RunActivity';
import { RunFeedback } from './RunFeedback';
import { persistedFeedback } from '../lib/runFeedback';
import { toast } from '../../../shared/utils/toasts';
import { activeRun } from '../lib/activeRun';
import { MessageArchive } from './MessageArchive';
import { RunArchive } from './RunArchive';
import { ModelPicker } from '../../settings/components/ModelPicker';
import { ChatWelcome } from './ChatWelcome';
import { KnowledgeFeedback } from './RunKnowledgeSummary';
import { useCurrentProject } from '../../projects/hooks/useProjects';
import { WorkspaceHeading } from '../../../app/layouts/WorkspaceHeader';
import { groupReplies } from '../lib/replyHistory';
import { ReansweredQuestion } from './ReansweredQuestion';

export function ChatPane({
  onUploadFiles,
  onToggleWorkspace,
  onSettings,
  showHeader,
}: {
  onUploadFiles?: () => void;
  onToggleWorkspace: () => void;
  onSettings: (tab: 'model' | 'mcp') => void;
  showHeader: boolean;
}) {
  const {
    projectId,
    threadId,
    attachNewDraft,
    removeSelection,
    setDraft,
    consumeDraft,
    consumeCommand,
    codeOpen,
    explorerOpen,
  } = useWorkspace();
  const conversationDraft = useWorkspace(draftFor);
  const api = <T,>(path: string, options?: RequestInit, id = projectId) =>
    request<T>(path, options, id);
  const project = useCurrentProject();
  const archivedProject = project.data?.state === 'archived';
  const { content: draft, selections } = conversationDraft;
  const [started, setStarted] = useState<Run>();
  const [context, setContext] = useState<{ runId?: string }>();
  const [selectionPreview, setSelectionPreview] = useState<{
    selection: Selection;
    index: number;
  }>();
  const composerInput = useRef<HTMLTextAreaElement>(null);
  const mobile = useWorkspace((state) => state.mobile);
  const cache = useQueryClient();
  const conversation = useConversation(threadId);
  const messageJump = useWorkspace((state) => state.messageJump);
  const modelPreference = useQuery({
    queryKey: ['model-preference'],
    queryFn: () => api<ModelPreference>('/model-preference'),
  });
  const latest = conversation.data?.runs.at(-1);
  const active = activeRun(started, conversation.data, threadId);
  const stream = useRunStream(active);
  const busy = !!active && !stream.finished;
  const queue = useQuestionQueue(threadId, setStarted);
  const scroll = useChatScroll(
    threadId,
    `${conversation.data?.messages.length}:${stream.answer}:${stream.tools.length}`,
    mobile === 'chat' || window.innerWidth > 800,
    !!conversation.data || !threadId,
  );
  useEffect(() => {
    if (
      !threadId ||
      !latest ||
      latest.status !== 'completed' ||
      (mobile !== 'chat' && window.innerWidth <= 800)
    )
      return;
    void api(`/threads/${threadId}/read`, { method: 'POST' })
      .then(() => cache.invalidateQueries({ queryKey: ['threads'] }))
      .catch(() => undefined);
  }, [threadId, latest?.id, latest?.status, mobile, cache]);
  useEffect(() => {
    if (selections.length) composerInput.current?.focus();
  }, [selections.length]);
  const send = useMutation({
    mutationFn: async ({
      key,
      submitted,
      queued,
    }: {
      key: string;
      submitted: ConversationDraft;
      queued: boolean;
    }) => {
      // 新问题由服务端捕获项目默认来源，旧草稿的单轮选择不会覆盖设置。
      if (queued && key !== 'new') {
        const result = await api<{ item: QueuedQuestion; started_run: Run | null }>(
          `/threads/${key}/queue`,
          {
            method: 'POST',
            body: jsonBody({ content: submitted.content.trim(), selections: submitted.selections }),
          },
          projectId,
        );
        return { run: result.started_run, queued: true };
      }
      const run = await api<Run>(
        key === 'new' ? '/threads/start' : `/threads/${key}/runs`,
        {
          method: 'POST',
          body: jsonBody({ content: submitted.content.trim(), selections: submitted.selections }),
        },
        projectId,
      );
      return { run, queued: false };
    },
    onSuccess: ({ run, queued }, { key, submitted }) => {
      const state = useWorkspace.getState();
      if (key === 'new' && run) {
        if (state.projectId === projectId) attachNewDraft(run.thread_id);
        else
          useWorkspace.setState({
            projectSessions: {
              ...state.projectSessions,
              [projectId]: { ...state.projectSessions[projectId], threadId: run.thread_id },
            },
          });
      }
      if (run && state.projectId === projectId) setStarted(run);
      consumeDraft(draftKey(key === 'new' ? '' : key, projectId), submitted);
      if (key === 'new' && run) consumeDraft(run.thread_id, submitted);
      if (run && useWorkspace.getState().threadId === run.thread_id) scroll.toLatest();
      void cache.invalidateQueries({ queryKey: ['thread', run?.thread_id || key] });
      void cache.invalidateQueries({ queryKey: ['queue', run?.thread_id || key] });
      void cache.invalidateQueries({ queryKey: ['threads'] });
      if (queued) toast(run ? '问题已开始发送' : '问题已加入等待队列');
    },
  });
  const submitDraft = () =>
    send.mutate({
      key: threadId || 'new',
      submitted: conversationDraft,
      queued: busy || !!queue.query.data?.items.length,
    });
  const editQuestion = useMutation({
    mutationFn: ({
      id,
      messageId,
      content,
      selections,
      source_options,
    }: {
      id: string;
      messageId: string;
      content: string;
      selections: Selection[];
      source_options: SourceOptions;
    }) =>
      api<Run>(`/threads/${id}/messages/${messageId}/edit`, {
        method: 'POST',
        body: jsonBody({ content, selections, source_options }),
      }),
    onSuccess: (run) => {
      setStarted(run);
      void cache.invalidateQueries({ queryKey: ['thread', run.thread_id] });
      if (useWorkspace.getState().threadId === run.thread_id) scroll.toLatest();
      toast('问题已修改，原始版本保留');
    },
  });
  const resume = useMutation({
    mutationFn: (id: string) => api<Run>(`/runs/${id}/resume`, { method: 'POST' }),
    onSuccess: (run) => {
      setStarted(run);
      void cache.invalidateQueries({ queryKey: ['thread', threadId] });
    },
  });
  const compact = useMutation({
    mutationFn: ({ id }: { id: string; submitted?: ConversationDraft }) =>
      api<Run>(`/threads/${id}/compact`, { method: 'POST' }),
    onSuccess: (run, { id, submitted }) => {
      setStarted(run);
      if (submitted) consumeCommand(draftKey(id, projectId), submitted);
      void cache.invalidateQueries({ queryKey: ['thread', run.thread_id] });
      void cache.invalidateQueries({ queryKey: ['threads'] });
    },
  });
  const regenerate = useMutation({
    mutationFn: (id: string) => api<Run>(`/runs/${id}/regenerate`, { method: 'POST' }),
    onSuccess: (run) => {
      const state = useWorkspace.getState();
      if (state.projectId === projectId && state.threadId === run.thread_id) {
        setStarted(run);
        scroll.toLatest();
      }
      void cache.invalidateQueries({ queryKey: ['thread', run.thread_id] });
      void cache.invalidateQueries({ queryKey: ['threads'] });
    },
  });
  const cancel = useMutation({
    mutationFn: (id: string) => api(`/runs/${id}/cancel`, { method: 'POST' }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['thread', threadId] });
      void cache.invalidateQueries({ queryKey: ['queue', threadId] });
    },
  });
  const messages = conversation.data?.messages || [];
  const showWelcome = !messages.length && !active && (!threadId || !!conversation.data);
  const runs = conversation.data?.runs || [];
  const { replyRuns, versionGroups } = groupReplies(messages, runs);
  const interrupted = latest && ['failed', 'cancelled', 'interrupted'].includes(latest.status);
  const canContext = !!threadId;
  const canCompact =
    canContext && messages.length > 0 && !busy && !send.isPending && !compact.isPending;
  const currentCompact = compact.variables?.id === threadId;
  const compactRun =
    currentCompact && compact.data
      ? runs.find((run) => run.id === compact.data.id) || compact.data
      : undefined;
  const compactStatus =
    currentCompact && compact.isPending
      ? '正在请求压缩…'
      : compactRun && busy && active?.id === compactRun.id
        ? '正在压缩上下文…'
        : compactRun?.status === 'completed'
          ? '压缩请求已完成，可查看上下文结果'
          : compactRun && ['failed', 'cancelled', 'interrupted'].includes(compactRun.status)
            ? '压缩未完成，可在对话中重试或继续'
            : '';
  function executeCommand(command: ComposerCommand) {
    if (command === '记录问题') {
      setDraft('/记录问题 ');
      composerInput.current?.focus();
      return;
    }
    const submitted = matchingCommands(draft).length ? conversationDraft : undefined;
    if (command === 'context' && canContext) {
      if (submitted) consumeCommand(draftKey(threadId, projectId), submitted);
      setContext({});
    } else if (command === 'compact' && canCompact) {
      compact.mutate({ id: threadId, submitted });
    }
  }
  return (
    <section className="chat-pane" data-empty={showWelcome || undefined}>
      <WorkspaceHeading className="chat-heading" active={showHeader}>
        <div>
          {project.data && (
            <span className="chat-project-name" title={project.data.name}>
              {project.data.name}
              <span>/</span>
            </span>
          )}
          <strong title={conversation.data?.title}>
            {conversation.data?.title || (threadId ? '正在打开对话…' : '新对话')}
          </strong>
        </div>
        <div>
          <Button
            className="icon-button workspace-toggle"
            aria-label="工作区"
            title={
              (codeOpen || explorerOpen) && (window.innerWidth > 800 || mobile === 'code')
                ? '收起工作区'
                : '展开工作区'
            }
            aria-pressed={
              (codeOpen || explorerOpen) && (window.innerWidth > 800 || mobile === 'code')
            }
            onClick={onToggleWorkspace}
          >
            <Folders size={17} aria-hidden="true" />
          </Button>
        </div>
      </WorkspaceHeading>
      {conversation.data?.origin_thread_id && (
        <div className="branch-origin">
          此对话来自历史消息的分支 ·{' '}
          <button
            onClick={() =>
              void api<{ project_id: string | null }>(
                `/projects/thread-location/${conversation.data!.origin_thread_id!}`,
              )
                .then((location) => {
                  const state = useWorkspace.getState();
                  state.switchProject(location.project_id || 'independent');
                  state.jumpToMessage(
                    conversation.data!.origin_thread_id!,
                    conversation.data!.origin_message_id!,
                  );
                })
                .catch((error) => toast(error.message, undefined, 'error'))
            }
          >
            查看来源
          </button>
        </div>
      )}
      <div className="chat-scroll" ref={scroll.scrollArea} onScroll={scroll.onScroll}>
        <div className="chat-content">
          {conversation.data?.has_older && (
            <button
              className="load-earlier"
              disabled={conversation.loadOlder.isPending}
              onClick={() => {
                scroll.preserveOnPrepend();
                conversation.loadOlder.mutate();
              }}
            >
              {conversation.loadOlder.isPending ? '正在加载…' : '加载更早的消息'}
            </button>
          )}
          <ErrorText error={conversation.loadOlder.error} />
          {threadId && conversation.isPending && <p className="muted">正在读取对话…</p>}
          {showWelcome && (
            <ChatWelcome
              onQuestion={(question) => {
                setDraft(question);
                composerInput.current?.focus();
              }}
            />
          )}
          {messages.map((message) => {
            const run = replyRuns.get(message.id);
            const versions = run && versionGroups.get(run.message_id);
            if (versions && versions.length > 1) {
              const representative =
                versions.find((version) => version.message.id === messageJump.id) ||
                versions.at(-1)!;
              if (representative.message.id !== message.id) return null;
              return (
                <div key={`${run.message_id}:${messageJump.id}`} data-message-id={message.id}>
                  <MessageArchive message={message} reveal={messageJump.id === message.id}>
                    <ReplyVersions
                      versions={versions}
                      selectedMessage={messageJump.id}
                      canRegenerate={!archivedProject && !busy && !regenerate.isPending}
                      onRegenerate={(id) => regenerate.mutate(id)}
                    />
                  </MessageArchive>
                </div>
              );
            }
            const bubble = message.reanswered_from ? (
              <ReansweredQuestion message={message} />
            ) : (
              <MessageBubble
                message={message}
                run={run}
                canRegenerate={
                  !archivedProject && !busy && !regenerate.isPending && run?.status === 'completed'
                }
                onRegenerate={(id) => regenerate.mutate(id)}
                onEdit={
                  !archivedProject && !busy && conversation.data?.editable_message_id === message.id
                    ? (content) =>
                        editQuestion.mutateAsync({
                          id: message.thread_id || threadId,
                          messageId: message.id,
                          content,
                          // 原位编辑只改正文，继续使用原问题的选区和知识来源。
                          selections: message.selections,
                          source_options: resolvedSources(message.source_options),
                        })
                    : undefined
                }
                recent={run?.id === latest?.id}
              />
            );
            return (
              <div
                key={message.id}
                data-message-id={message.id}
                className={
                  messageJump.id === message.id && !messageJump.restore
                    ? 'message-search-hit'
                    : undefined
                }
              >
                <MessageArchive message={message} reveal={messageJump.id === message.id}>
                  {bubble}
                  {message.role === 'user' && (
                    <RunArchive
                      runs={runs.filter(
                        (run) =>
                          run.message_id === message.id &&
                          run.id !== latest?.id &&
                          ['failed', 'cancelled', 'interrupted'].includes(run.status),
                      )}
                      onSettings={onSettings}
                      onContext={(runId) => setContext({ runId })}
                    />
                  )}
                </MessageArchive>
              </div>
            );
          })}
          {active && (
            <div className="message assistant">
              <div className="message-label">
                ARKS软件智能助手{' '}
                <RunActivity run={active} stage={stream.stage} detail={stream.detail} busy={busy} />
              </div>
              <ToolActivity tools={stream.tools} />
              {stream.answer ? (
                <AnswerMarkdown
                  content={stream.answer}
                  runId={active.id}
                  streaming={!stream.finished}
                />
              ) : (
                <span className="muted">
                  正在思考<span className="typing-dots">…</span>
                </span>
              )}
              {stream.feedback && (
                <RunFeedback
                  feedback={stream.feedback}
                  onSettings={onSettings}
                  onContext={() => setContext({ runId: active.id })}
                />
              )}
              <KnowledgeFeedback
                answer={stream.answer}
                references={stream.references}
                saves={stream.memorySaves}
              />
            </div>
          )}
          {interrupted && (
            <div className="run-recovery">
              <RunActivity run={latest} busy={false} />
              {latest.status === 'cancelled' ? (
                <p className="muted">已停止回复，已生成的内容保留。</p>
              ) : (
                <RunFeedback
                  feedback={persistedFeedback(latest)}
                  onSettings={onSettings}
                  onContext={() => setContext({ runId: latest.id })}
                />
              )}
              {latest.answer && <AnswerMarkdown content={latest.answer} runId={latest.id} />}
              <Button
                onClick={() => resume.mutate(latest.id)}
                disabled={archivedProject || resume.isPending}
              >
                <RotateCcw size={13} />
                {latest.status === 'failed' ? '重试运行' : '继续回复'}
              </Button>
            </div>
          )}
          <ErrorText
            error={
              conversation.error || send.error || resume.error || regenerate.error || cancel.error
            }
          />
          {stream.noticeFeedback?.action ? (
            <RunFeedback
              feedback={stream.noticeFeedback}
              onSettings={onSettings}
              onContext={() => setContext({ runId: active?.id })}
            />
          ) : (
            stream.notice && <div className="stream-notice">{stream.notice}</div>
          )}
        </div>
      </div>
      <div className="composer-area">
        {archivedProject && (
          <div className="project-readonly-notice">
            此项目已归档，历史内容可以查看。可在侧栏项目菜单中恢复后继续对话。
          </div>
        )}
        <QuestionQueuePanel key={`queue:${threadId}`} queue={queue} threadId={threadId} />
        {scroll.showLatest && (
          <button className="back-to-latest" onClick={scroll.toLatest}>
            <ChevronDown size={14} />
            回到最新
          </button>
        )}
        {selections.length > 0 && (
          <div className="selection-list">
            {selections.map((selection, index) => (
              <div className="selection-chip" key={index} title={selection.path}>
                <FileCode2 size={13} />
                <button
                  className="selection-preview-trigger"
                  aria-label={`预览选区 ${selection.path}`}
                  onClick={() => setSelectionPreview({ selection, index })}
                >
                  {selection.path.split('/').at(-1)}
                  <small>
                    L{selection.start_line}–{selection.end_line}
                  </small>
                </button>
                <button aria-label="移除代码选区" onClick={() => removeSelection(index)}>
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
        <ChatComposer
          readOnly={archivedProject}
          key={`composer:${threadId}`}
          inputRef={composerInput}
          draft={draft}
          onChange={setDraft}
          onSend={submitDraft}
          onCommand={executeCommand}
          onStop={() => active && cancel.mutate(active.id)}
          onUploadFiles={onUploadFiles}
          sending={send.isPending}
          busy={busy}
          queueing={!!queue.query.data?.items.length}
          stopping={cancel.isPending}
          canContext={canContext}
          canCompact={!archivedProject && canCompact}
          compactDisabledReason={!messages.length ? '请先发送一条消息' : '请等待当前运行完成'}
          model={
            modelPreference.data?.model_profiles.find(
              (profile) => profile.id === modelPreference.data.active_profile_id,
            )?.model || '配置模型'
          }
          modelControl={
            modelPreference.data && <ModelPicker preference={modelPreference.data} busy={busy} />
          }
          context={
            <ComposerContext
              threadId={threadId}
              liveContext={active ? stream.context : undefined}
              compactStatus={compactStatus}
              compactError={
                currentCompact
                  ? compact.error ||
                    compactRun?.error ||
                    (active?.id === compactRun?.id ? stream.error : undefined)
                  : undefined
              }
              onView={() => setContext({})}
            />
          }
        />
      </div>
      <ContextDialog
        key={`${threadId}:${context?.runId || ''}`}
        open={!!context}
        threadId={threadId}
        runId={context?.runId}
        onClose={() => setContext(undefined)}
      />
      {selectionPreview && (
        <SelectionPreview
          selection={selectionPreview.selection}
          onClose={() => setSelectionPreview(undefined)}
          onRemove={() => removeSelection(selectionPreview.index)}
        />
      )}
    </section>
  );
}
