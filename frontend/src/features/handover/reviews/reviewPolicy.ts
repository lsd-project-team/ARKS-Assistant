import type { HandoverRecord } from '../shared/types';

export function canReviewRecord(row: HandoverRecord, historical = false) {
  if (row.kind === 'package')
    return !historical && ['draft', 'needs_review', 'rejected'].includes(row.state);
  return (
    !historical &&
    !['source', 'interview', 'task', 'candidate', 'job'].includes(row.kind) &&
    ['draft', 'needs_review'].includes(row.state)
  );
}
