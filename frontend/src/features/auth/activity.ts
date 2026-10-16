/** 只累计真实前台活动；使用单调时钟，休眠、失焦和长时间空闲不补时长。 */
export function activeSlice(
  elapsed: number,
  sinceInteraction: number,
  visible: boolean,
  focused: boolean,
) {
  if (!visible || !focused || elapsed <= 0 || elapsed > 2500) return 0;
  return Math.max(0, Math.min(elapsed, 60000 - Math.max(0, sinceInteraction - elapsed)));
}
