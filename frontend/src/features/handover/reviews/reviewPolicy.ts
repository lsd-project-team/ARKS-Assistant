import type { HandoverRecord } from '../shared/types';

export function canReviewRecord(row: HandoverRecord, historical = false) {
  return (
    !historical &&
    !['task', 'candidate', 'job'].includes(row.kind) &&
    ['draft', 'needs_review'].includes(row.state)
  );
}
