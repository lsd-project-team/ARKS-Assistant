import { useQuery } from '@tanstack/react-query';
import { api } from '../../../app/api/client';
import type { KnowledgeReference } from '../../../shared/types/api';
import type { HandoverRecord } from '../../handover/shared/types';
import { text } from '../../handover/shared/types';
import { DebugIssueImages } from '../../handover/debug_issues/DebugIssueImages';
import { ErrorText } from '../../../shared/ui/ui';

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
    <section className="debug-source-record" aria-label={`检索原文：${reference.title}`}>
      <header>
        <strong>{reference.title}</strong>
        <small>原文与原图 · v{reference.version}</small>
      </header>
      {record.isPending && <p role="status">正在加载原文与原图…</p>}
      <ErrorText error={record.error} />
      {record.data && (
        <>
          <pre>{text(record.data.payload.problem)}</pre>
          {text(record.data.payload.original_text) &&
            record.data.payload.original_text !== record.data.payload.problem && (
              <details>
                <summary>查看录入原文</summary>
                <pre>{text(record.data.payload.original_text)}</pre>
              </details>
            )}
          <DebugIssueImages row={record.data} />
        </>
      )}
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
            row.image_count !== undefined &&
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
