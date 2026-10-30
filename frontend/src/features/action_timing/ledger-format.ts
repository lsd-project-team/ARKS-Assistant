import type { ActionValues } from './ledger-types';

export function durationText(value: number | null | undefined) {
  return value == null
    ? '待填写'
    : new Intl.NumberFormat('zh-CN', { maximumSignificantDigits: 15 }).format(value);
}

export function actionValues(
  name: string,
  categoryId: string,
  duration: string,
  notes: string,
): ActionValues {
  if (!name.trim()) throw new Error('请填写动作名称');
  const value = duration.trim() === '' ? null : Number(duration);
  if (value !== null && (!Number.isFinite(value) || value < 0))
    throw new Error('耗时须为非负数，或暂时留空');
  return {
    name: name.trim(),
    category_id: categoryId || null,
    duration_seconds: value,
    notes: notes.trim(),
  };
}

export function importSummary(counts: { add: number; update: number; skip: number }) {
  return `新增 ${counts.add}，更新 ${counts.update}，跳过 ${counts.skip}`;
}
