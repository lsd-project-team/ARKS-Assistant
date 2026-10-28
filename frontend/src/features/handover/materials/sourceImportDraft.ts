import { draftStorageKey, type Draft } from '../shared/drafts';
import { text } from '../shared/types';

function previousDraftKey(scopeId: string, recordId?: string) {
  return draftStorageKey(scopeId, recordId ? `source-update:${recordId}` : 'import');
}

export function previousSourceDraft(scopeId: string, recordId?: string): Draft | undefined {
  try {
    const key = previousDraftKey(scopeId, recordId);
    const draft = JSON.parse(localStorage.getItem(key) || 'null');
    if (
      draft &&
      typeof draft.title === 'string' &&
      draft.payload &&
      typeof draft.payload === 'object' &&
      !Array.isArray(draft.payload)
    )
      return draft;
  } catch {
    // 旧草稿损坏或本机存储不可读，不阻止继续上传文件。
  }
}

export function clearPreviousFileDraft(scopeId: string, previous: Draft, recordId?: string) {
  try {
    // 只清除本次已迁移的文件说明，别的窗口后来填写的草稿继续保留。
    if (JSON.stringify(previousSourceDraft(scopeId, recordId)) === JSON.stringify(previous))
      localStorage.removeItem(previousDraftKey(scopeId, recordId));
  } catch {
    // 本机草稿清理失败不影响已完成的服务器保存。
  }
}

export function downloadTextDraft(draft: Draft) {
  const address = URL.createObjectURL(
    new Blob([text(draft.payload.content)], { type: 'text/plain;charset=utf-8' }),
  );
  const anchor = document.createElement('a');
  anchor.href = address;
  anchor.download = `${(draft.title || '未保存文本草稿').replace(/[\\/:*?"<>|\r\n]/g, '_')}.txt`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(address), 1000);
}
