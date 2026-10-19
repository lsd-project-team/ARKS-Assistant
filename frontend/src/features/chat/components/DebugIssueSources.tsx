import { useQuery } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { api } from '../../../app/api/client';
import type { KnowledgeReference } from '../../../shared/types/api';
import type { HandoverRecord } from '../../handover/shared/types';
import { text } from '../../handover/shared/types';
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
  const payload = record.data?.payload;
  const originalText = text(payload?.original_text);
  const recordText = text(payload?.problem) || originalText;
  const attribution = [text(payload?.recorded_by), text(payload?.recorded_at)]
    .filter(Boolean)
    .join(' · ');
  return (
    <section className="debug-source-record" aria-label={`检索原文：${reference.title}`}>
      <header>
        <span className="debug-source-label">
          <FileText size={14} aria-hidden="true" />
          记录文字
        </span>
        {attribution && <span className="debug-source-attribution">{attribution}</span>}
      </header>
      <p className="debug-source-title">{reference.title}</p>
      {record.isPending && <p role="status">正在加载原文与原图…</p>}
      <ErrorText error={record.error} />
      {record.data && (
        <>
          <blockquote className="debug-source-text">{recordText}</blockquote>
          {originalText && originalText !== recordText && (
            <details className="debug-source-original">
              <summary>查看录入原文</summary>
              <blockquote className="debug-source-text">{originalText}</blockquote>
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
