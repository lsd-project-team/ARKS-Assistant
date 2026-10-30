import { useEffect, useRef } from 'react';
import type { HandoverRecord } from '../../shared/types';
import { handoverDocumentText } from '../../../knowledge/lib/knowledgeReference';
import { Modal } from '../../../../shared/ui/ui';

export function HandoverMaterialViewer({
  row,
  start,
  end,
  onClose,
}: {
  row: HandoverRecord;
  start: number;
  end: number;
  onClose: () => void;
}) {
  const content = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const frame = requestAnimationFrame(() =>
      content.current?.querySelector('.cited')?.scrollIntoView({ block: 'center' }),
    );
    return () => cancelAnimationFrame(frame);
  }, [row.id, start]);
  return (
    <Modal
      open
      onClose={onClose}
      title={row.title}
      description={`交接资料 · 引用版本 ${row.version}${row.state === 'archived' ? ' · 已归档' : ''}`}
      className="historical-source-dialog"
    >
      {row.payload.parse_status === 'partial' && (
        <p className="muted">此附件仅部分解析，以下为已提取的正文。</p>
      )}
      <div ref={content} className="historical-source-lines material-view-lines">
        {handoverDocumentText(row)
          .split('\n')
          .map((line, index) => (
            <div key={index} className={index + 1 >= start && index + 1 <= end ? 'cited' : ''}>
              <span>{index + 1}</span>
              <code>{line || ' '}</code>
            </div>
          ))}
      </div>
    </Modal>
  );
}
