import { parseHandoverHash } from '../handover/navigation.ts';
import { parseTimingHash } from '../action_timing/navigation.ts';

/** 直接解析当前地址，避免两个路由订阅先后更新时误判成无效地址。 */
export function adminRoute(hash: string) {
  const handover = parseHandoverHash(hash);
  const timing = parseTimingHash(hash);
  const match = /^#admin\/(overview|users|questions|settings|data)(?:\/([^?]+))?$/.exec(hash);
  const page = timing.open
    ? 'action-timing'
    : handover.open && handover.tab !== 'overview'
      ? handover.tab === 'updates'
        ? 'reviews'
        : 'handover'
      : match?.[1] || 'overview';
  return {
    page,
    questionId: match?.[1] === 'questions' ? match[2] : undefined,
    valid: !!match || handover.open || timing.open,
    handover,
  };
}
