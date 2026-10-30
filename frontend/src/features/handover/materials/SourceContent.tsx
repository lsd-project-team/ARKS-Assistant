import { text, type HandoverRecord } from '../shared/types';
import './source-detail.css';

export function SourceContent({ row }: { row: HandoverRecord }) {
  const content = text(row.payload.content);
  const notes = text(row.payload.notes);
  const organizer = text(row.created_by);
  const status = text(row.payload.parse_status);
  return (
    <div className="source-detail-content">
      {organizer.trim() && (
        <p className="source-detail-organizer">
          <span>整理人</span>
          {organizer}
        </p>
      )}
      {notes.trim() && (
        <section className="source-detail-notes">
          <h3>来源说明</h3>
          <p>{notes}</p>
        </section>
      )}
      {status === 'partial' && (
        <p className="source-detail-preview-note" role="status">
          当前仅展示部分内容，完整内容请下载原始附件查看。
        </p>
      )}
      {status === 'needs_ocr' && (
        <p className="source-detail-preview-note" role="status">
          这份资料暂时无法显示文字内容，请下载原始附件查看。
        </p>
      )}
      {content.trim() ? (
        <section className="source-detail-text" aria-label="资料内容">
          <pre>{content}</pre>
        </section>
      ) : (
        status !== 'needs_ocr' && (
          <p className="handover-muted">暂无可展示的文字，请下载原始附件查看。</p>
        )
      )}
    </div>
  );
}
