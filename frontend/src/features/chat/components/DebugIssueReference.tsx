import { useRef, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../../app/api/client';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import type { HandoverRecord } from '../../handover/shared/types';
import { ids, text } from '../../handover/shared/types';
import {
  debugIssueFields,
  debugRecordType,
  debugStatus,
  debugVisiblePayload,
  debugMetadataFields,
} from '../../handover/debug_issues/debugIssues';
import { DebugIssueImages } from '../../handover/debug_issues/DebugIssueImages';
import '../../handover/debug_issues/debug-issues.css';
import '../styles/debug-issue-reference.css';

export function DebugIssueReferenceContent({ row }: { row: HandoverRecord }) {
  const payload = debugVisiblePayload(row.payload);
  return (
    <>
      <p className="debug-issue-reference-meta">
        {debugRecordType(payload).label} · {debugStatus(payload)}
      </p>
      <dl className="debug-issue-detail-fields">
        {debugIssueFields
          .filter(({ key }) => text(payload[key]))
          .map(({ key, label }) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd>{text(payload[key])}</dd>
            </div>
          ))}
        {!!ids(payload.keywords).length && (
          <div>
            <dt>关键词</dt>
            <dd>{ids(payload.keywords).join('、')}</dd>
          </div>
        )}
      </dl>
      <details className="debug-issue-additional">
        <summary>记录信息</summary>
        <dl className="debug-issue-detail-fields">
          {debugMetadataFields
            .filter(({ key }) => text(payload[key]))
            .map(({ key, label }) => (
              <div key={key}>
                <dt>{label}</dt>
                <dd>{text(payload[key])}</dd>
              </div>
            ))}
        </dl>
      </details>
      <DebugIssueImages row={row} />
      {text(payload.original_text) && (
        <details className="debug-issue-original">
          <summary>查看录入原文</summary>
          <pre>{text(payload.original_text)}</pre>
        </details>
      )}
    </>
  );
}

export function DebugIssueReference({
  id,
  version,
  label,
  children,
  className = 'source-link',
}: {
  id: string;
  version: number;
  label: string;
  children: ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const record = useQuery({
    queryKey: ['debug-source', id, version],
    queryFn: async () => {
      const row = await api<HandoverRecord>(
        `/handover/records/${encodeURIComponent(id)}?version=${version}`,
        undefined,
        '',
      );
      // 标题可简化，读取仍对应回答引用的原记录，不能静默替换成最新内容。
      if (row.kind !== 'debug_issue' || row.id !== id || row.version !== version)
        throw new Error('无法读取这条引用记录，请重试。');
      return row;
    },
    enabled: open,
    staleTime: Infinity,
    retry: false,
  });
  return (
    <>
      <button
        ref={trigger}
        type="button"
        className={className}
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        {children}
      </button>
      {open && (
        <Modal
          open
          title={record.data?.title || label || '记录信息'}
          onClose={() => {
            setOpen(false);
            requestAnimationFrame(() => trigger.current?.focus());
          }}
          className="debug-issue-reference"
        >
          <div className="debug-issue-reference-body">
            {record.isPending && <p role="status">正在加载记录…</p>}
            <ErrorText error={record.error} />
            {record.isError && <Button onClick={() => void record.refetch()}>重新加载</Button>}
            {record.data && <DebugIssueReferenceContent row={record.data} />}
          </div>
        </Modal>
      )}
    </>
  );
}
