import { useQuery } from '@tanstack/react-query';
import { api } from '../../../app/api/client';
import type { KnowledgeReference } from '../../../shared/types/api';
import type { HandoverRecord } from '../../handover/shared/types';
import { DebugIssueImages } from '../../handover/debug_issues/DebugIssueImages';
import { ErrorText } from '../../../shared/ui/ui';
import '../styles/record-answer.css';

function DebugIssueSource({ reference }: { reference: KnowledgeReference }) {
  const record = useQuery({
    queryKey: ['debug-source', reference.id, reference.version],
    queryFn: () =>
      api<HandoverRecord>(
        `/handover/records/${encodeURIComponent(reference.id)}?version=${reference.version}`,
      ),
    staleTime: Infinity,
  });
  return (
    <section className="debug-source-images" aria-label={`原图：${reference.title}`}>
      {record.isPending && <p role="status">正在加载原图…</p>}
      <ErrorText error={record.error} />
      {record.data && <DebugIssueImages row={record.data} />}
    </section>
  );
}

export function originalDebugReferences(references: KnowledgeReference[]) {
  return [
    ...new Map(
      references
        .filter(
          (row) =>
            row.kind === 'debug_issue' &&
            (row.image_count ?? 0) > 0 &&
            row.compatibility?.status !== 'mismatch',
        )
        .map((row) => [`${row.id}:${row.version}`, row]),
    ).values(),
  ];
}

export function DebugIssueSources({ references }: { references: KnowledgeReference[] }) {
  return originalDebugReferences(references).map((reference) => (
    <DebugIssueSource key={`${reference.id}:${reference.version}`} reference={reference} />
  ));
}
