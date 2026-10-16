import type { Memory } from '../../../shared/types/api.ts';

export type DraftMemory = Partial<Memory> & { name: string; content: string; scope: string };
export const blankMemory = (): DraftMemory => ({
  name: '',
  content: '',
  scope: 'project',
  sources: [],
});
export const memorySignature = (draft: DraftMemory) =>
  JSON.stringify([draft.name, draft.scope, draft.content, draft.lifecycle || 'valid']);

export function validateMemory(draft: DraftMemory): string[] {
  const errors = [];
  if (!/^[\p{L}\p{N}_-]{1,80}\.md$/u.test(draft.name))
    errors.push('名称需为 1–80 个文字、数字、下划线或短横线，并以 .md 结尾');
  if (!draft.content.trim()) errors.push('记忆内容不能为空');
  if (draft.content.length > 50000) errors.push('记忆内容最多 50000 字');
  return errors;
}
