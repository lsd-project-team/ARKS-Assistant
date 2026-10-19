import type { Payload } from '../shared/types';

export interface DebugImage {
  id: string;
  name: string;
  recorded_at: string;
}

export function debugImages(payload: Payload): DebugImage[] {
  if (!Array.isArray(payload.images)) return [];
  // 使用记录中的位置顺序；相同图片再次出现时也要保留。
  return payload.images.filter(
    (image): image is DebugImage =>
      !!image && typeof image === 'object' && typeof image.id === 'string',
  );
}

export function debugImageUrl(id: string, version: number, index: number) {
  return `/api/handover/debug-issues/${encodeURIComponent(id)}/images/${version}/${index}`;
}
