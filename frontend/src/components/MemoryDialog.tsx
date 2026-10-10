import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Brain, Plus, Save, Trash2, FileCode2 } from 'lucide-react';
import { api, query, jsonBody } from '../lib/api';
import type { Memory } from '../types';
import { Modal, Button, ErrorText } from './ui';
import { useWorkspace } from '../lib/store';

type DraftMemory = Partial<Memory> & { name: string; content: string; scope: string };
const blank = (): DraftMemory => ({ name: '', content: '', scope: 'project', sources: [] });
export function MemoryDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const cache = useQueryClient();
  const memories = useQuery({
    queryKey: ['memories'],
    queryFn: () => api<Memory[]>('/memories'),
    enabled: open,
  });
  const [draft, setDraft] = useState<DraftMemory>(blank);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const openFile = useWorkspace((state) => state.openFile);
  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError(undefined);
    setSaved(false);
    try {
      await action();
      await cache.invalidateQueries({ queryKey: ['memories'] });
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="长期记忆"
      description="跨对话保留偏好与项目事实，可以查看、编辑或删除。"
    >
      <div className="memory-layout">
        <div className="memory-list">
          <Button
            onClick={() => {
              setDraft(blank());
              setSaved(false);
            }}
          >
            <Plus size={14} />
            新增记忆
          </Button>
          {memories.data?.map((memory) => (
            <button
              key={`${memory.scope}/${memory.name}`}
              className={
                draft.name === memory.name && draft.scope === memory.scope ? 'selected' : ''
              }
              onClick={() => {
                setDraft(memory);
                setSaved(false);
              }}
            >
              <Brain size={13} />
              <span>
                {memory.name}
                <small>{memory.scope === 'project' ? '项目记忆' : '用户偏好'}</small>
              </span>
            </button>
          ))}
        </div>
        <div className="memory-editor">
          <div className="field-pair">
            <label>
              名称
              <input
                value={draft.name}
                disabled={!!draft.version}
                placeholder="例如：项目结构.md"
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              />
            </label>
            <label>
              范围
              <select
                disabled={!!draft.version}
                value={draft.scope}
                onChange={(e) => setDraft({ ...draft, scope: e.target.value })}
              >
                <option value="project">当前项目</option>
                <option value="user">用户偏好</option>
              </select>
            </label>
          </div>
          <label>
            内容
            <textarea
              rows={13}
              value={draft.content}
              onChange={(e) => setDraft({ ...draft, content: e.target.value })}
              placeholder="写下需要在后续对话中记住的信息…"
            />
          </label>
          {draft.source_thread_id && (
            <p className="muted">来源对话：{draft.source_thread_id.slice(0, 8)}</p>
          )}
          {draft.sources?.map((source) => (
            <button
              className="memory-source"
              key={source.path}
              onClick={() => {
                openFile(source.path);
                onClose();
              }}
            >
              <FileCode2 size={12} />
              {source.path}
              {source.stale && <span>源码已变化 · 需核对</span>}
            </button>
          ))}
          <ErrorText error={error || memories.error} />
          {saved && <p className="success-text">记忆已保存</p>}
          <div className="button-row">
            <Button
              className="primary"
              disabled={busy || !draft.name || !draft.content}
              onClick={() =>
                void perform(async () => {
                  const result = await api<Memory>('/memories', {
                    method: 'PUT',
                    body: jsonBody({
                      ...draft,
                      source_paths: draft.sources?.map((source) => source.path) || [],
                    }),
                  });
                  setDraft(result);
                  setSaved(true);
                })
              }
            >
              <Save size={14} />
              保存记忆
            </Button>
            {draft.version && (
              <Button
                className="danger"
                disabled={busy}
                onClick={() =>
                  void perform(async () => {
                    await api(
                      `/memories/${draft.scope}/${query(draft.name)}?version=${draft.version}`,
                      { method: 'DELETE' },
                    );
                    setDraft(blank());
                  })
                }
              >
                <Trash2 size={14} />
                删除
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
