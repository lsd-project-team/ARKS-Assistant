import type { SourceFlow, SourceOutcome, SourceStep } from '../sourceGuides';

export const outcome = (label: string, text: string, ...refs: string[]): SourceOutcome => ({
  label,
  text,
  refs,
});
export const step = (
  id: string,
  title: string,
  text: string,
  refs: string[],
  outcomes: SourceOutcome[] = [],
): SourceStep => ({ id, title, text, refs, outcomes });
export const flow = (
  id: string,
  title: string,
  text: string,
  refs: string[],
  steps: SourceStep[],
): SourceFlow => ({ id, title, text, refs, steps });

// 模式比较与互斥返回是并列阅读项，不能用箭头暗示全部依次执行。
export const choices = (...args: Parameters<typeof flow>): SourceFlow => {
  const item = flow(...args);
  item.sequential = false;
  return item;
};
