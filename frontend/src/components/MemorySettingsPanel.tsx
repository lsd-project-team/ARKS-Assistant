import { Brain, Plus, Save, Trash2, FileCode2 } from 'lucide-react';
import { Button, ErrorText } from './ui';
import { useWorkspace } from '../lib/store';
import type { useMemoryDraft } from '../hooks/useMemoryDraft';
import { blankMemory } from '../lib/memoryDraft';
import { ConfirmationNotice } from './ConfirmationNotice';
import { MemoryHistory } from './MemoryHistory';
import { MemoryReview } from './MemoryReview';
import { Select } from './Select';

export function MemorySettingsPanel({
  controller,
  onNavigate,
}: {
  controller: ReturnType<typeof useMemoryDraft>;
  onNavigate: (action: () => void) => void;
}) {
  const { draft, setDraft, memories, error, busy } = controller;
  const openFile = useWorkspace((state) => state.openFile);
  const selectThread = useWorkspace((state) => state.selectThread);
  return (
    <section className="settings-memory-panel" aria-label="长期记忆管理">
      <p className="muted">跨对话保留偏好与项目事实，可以查看、编辑或删除。</p>
      <div className="memory-layout">
        <div className="memory-list">
          <Button disabled={busy} onClick={() => controller.select(blankMemory())}>
            <Plus size={14} />
            新增记忆
          </Button>
          {memories.data?.map((memory) => (
            <button
              key={`${memory.scope}/${memory.name}`}
              className={
                draft.name === memory.name && draft.scope === memory.scope ? 'selected' : ''
              }
              disabled={busy}
              onClick={() => controller.select(memory)}
            >
              <Brain size={13} />
              <span>
                {memory.name}
                <small>
                  {memory.deleted
                    ? '已删除 · 可恢复'
                    : memory.scope === 'project'
                      ? '项目记忆'
                      : '用户偏好'}
                </small>
                <small>
                  {memory.lifecycle === 'invalid'
                    ? '失效 · 不带入回答'
                    : memory.lifecycle === 'needs_review'
                      ? '待复核'
                      : '有效'}
                </small>
              </span>
            </button>
          ))}
        </div>
        <div className="memory-editor">
          {draft.deleted && (
            <p className="muted">此记忆已删除，后续回答不会带入。可在历史版本中恢复。</p>
          )}
          <fieldset className="settings-content" disabled={busy || draft.deleted}>
            <div className="field-pair">
              <label>
                名称
                <input
                  value={draft.name}
                  disabled={busy || !!draft.version}
                  placeholder="例如：项目结构.md"
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                />
              </label>
              <label>
                范围
                <Select
                  aria-label="记忆范围"
                  disabled={busy || !!draft.version}
                  value={draft.scope}
                  onValueChange={(scope) => setDraft({ ...draft, scope })}
                >
                  <option value="project">当前项目</option>
                  <option value="user">用户偏好</option>
                </Select>
              </label>
            </div>
            <label>
              记忆状态
              <Select
                aria-label="记忆状态"
                value={draft.lifecycle || 'valid'}
                onValueChange={(lifecycle) =>
                  setDraft({
                    ...draft,
                    lifecycle: lifecycle as 'valid' | 'needs_review' | 'invalid',
                  })
                }
              >
                <option value="valid">有效</option>
                <option value="needs_review">待复核</option>
                <option value="invalid">失效（不带入回答）</option>
              </Select>
            </label>
            <label>
              内容
              <textarea
                rows={13}
                value={draft.content}
                onChange={(e) => setDraft({ ...draft, content: e.target.value })}
                placeholder="写下需要在后续对话中记住的信息…"
              />
            </label>
            {draft.source_thread_id && draft.source_thread_status !== 'deleted' && (
              <button
                className="memory-source"
                onClick={() => onNavigate(() => selectThread(draft.source_thread_id!))}
              >
                打开来源对话 · {draft.source_thread_id.slice(0, 8)}
              </button>
            )}
            {draft.source_thread_status === 'deleted' && (
              <p className="muted">来源对话已删除 · 记忆内容仍保留</p>
            )}
            {!!draft.updated_at && (
              <p className="muted">
                更新于 {new Date(draft.updated_at * 1000).toLocaleString('zh-CN')}
              </p>
            )}
            {draft.sources?.map((source) => (
              <button
                className="memory-source"
                key={source.path}
                onClick={() => onNavigate(() => openFile(source.path))}
              >
                <FileCode2 size={12} />
                {source.path}
                {source.stale && <span>源码已变化 · 需核对</span>}
              </button>
            ))}
          </fieldset>
          <ErrorText error={error || memories.error} reveal={!!error} />
          {!!error && (
            <Button disabled={busy} onClick={controller.reload}>
              读取最新记忆
            </Button>
          )}
          {controller.dirty && !!controller.errors.length && (
            <ul className="settings-validation" role="alert">
              {controller.errors.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          )}
          <MemoryReview
            rows={controller.review}
            restoring={controller.restoring}
            busy={busy}
            onOpen={controller.openRelated}
            onConfirm={() => void controller.confirmReview()}
            onCancel={controller.cancelReview}
          />
          {controller.deleting && (
            <ConfirmationNotice>
              <span>确认删除“{draft.name}”？后续回答不再带入，历史版本仍可恢复。</span>
              <Button disabled={busy} onClick={() => controller.setDeleting(false)}>
                取消
              </Button>
              <Button disabled={busy} onClick={() => void controller.remove()}>
                确认删除记忆
              </Button>
            </ConfirmationNotice>
          )}
          <div className="button-row">
            <Button
              className="primary"
              disabled={busy || draft.deleted || !controller.dirty || !!controller.errors.length}
              onClick={() => void controller.save()}
            >
              <Save size={14} />
              保存记忆
            </Button>
            {draft.version && (
              <Button
                className="danger"
                disabled={busy}
                onClick={() => controller.setDeleting(true)}
              >
                <Trash2 size={14} />
                删除
              </Button>
            )}
          </div>
          {(draft.version || draft.deleted) && (
            <MemoryHistory
              name={draft.name}
              scope={draft.scope}
              busy={busy}
              onRestore={controller.prepareRestore}
            />
          )}
        </div>
      </div>
    </section>
  );
}
