import { FileText } from 'lucide-react';
import { useState } from 'react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { Client } from '../shared/client';
import { HandoverModal } from '../shared/HandoverModal';
import { localTime } from '../shared/format';
import { text, type HandoverRecord } from '../shared/types';
import { materialName } from './materialRecords';
import { PdfOriginal } from './PdfOriginal';
import './materials.css';

export function OriginalMaterialViewer({
  row,
  client,
  onClose,
}: {
  row: HandoverRecord;
  client: Client;
  onClose: () => void;
}) {
  const [error, setError] = useState<unknown>();
  const name = materialName(row);
  const original = `/sources/${encodeURIComponent(row.id)}/original`;
  const legacyText =
    !row.original_file &&
    text(row.kind === 'interview' ? row.payload.transcript : row.payload.content);
  return (
    <HandoverModal
      title={name}
      description="查看原文件"
      onClose={onClose}
      className="material-original-dialog"
      footer={
        <>
          <Button
            className="primary"
            onClick={() =>
              void client
                .download(original, row.original_file ? name : `${row.title}.txt`)
                .catch(setError)
            }
          >
            下载原文件
          </Button>
          <Button onClick={onClose}>关闭</Button>
        </>
      }
    >
      <ErrorText error={error} reveal />
      <div className="material-original-meta">
        {row.created_by && <span>上传人：{row.created_by}</span>}
        <time dateTime={row.created_at}>{localTime(row.created_at)}</time>
      </div>
      {row.original_file?.previewable ? (
        name.toLowerCase().endsWith('.pdf') ? (
          <PdfOriginal source={`/api/handover${original}`} />
        ) : (
          <iframe
            className="material-original-frame"
            title={`原文件：${name}`}
            src={`/api/handover${original}?inline=true`}
          />
        )
      ) : legacyText ? (
        <>
          <p className="muted">这条历史资料没有附件，以下为原有文本。</p>
          <pre className="material-original-text">{legacyText}</pre>
        </>
      ) : (
        <div className="material-original-fallback">
          <FileText size={38} />
          <p>此格式暂不支持在线预览，请下载原文件查看。</p>
        </div>
      )}
    </HandoverModal>
  );
}
