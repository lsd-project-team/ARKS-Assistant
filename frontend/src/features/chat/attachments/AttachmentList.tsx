import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, X, Download } from 'lucide-react';
import { api, apiUrl } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import type { ChatAttachment } from '../../../shared/types/api';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import './attachments.css';

interface AttachmentPage extends ChatAttachment {
  content: string;
  offset: number;
  next_offset: number | null;
}

function AttachmentPreview({
  attachment,
  onClose,
}: {
  attachment: ChatAttachment;
  onClose: () => void;
}) {
  const projectId = useWorkspace((state) => state.projectId);
  const [offsets, setOffsets] = useState([0]);
  const offset = offsets.at(-1)!;
  const page = useQuery({
    queryKey: ['chat-attachment', projectId, attachment.id, offset],
    queryFn: () =>
      api<AttachmentPage>(`/attachments/${attachment.id}?offset=${offset}`, undefined, projectId),
  });
  return (
    <Modal
      open
      onClose={onClose}
      title={attachment.filename}
      className="attachment-preview"
      description="上传文档的可读取正文"
    >
      <div className="attachment-preview-body">
        <p className="attachment-notes">{attachment.parse_notes}</p>
        <a
          className="button"
          href={apiUrl(`/attachments/${attachment.id}/download`, projectId)}
          download
        >
          <Download size={14} /> 下载原文件
        </a>
        <ErrorText error={page.error} />
        {page.isPending ? <p role="status">正在读取文档…</p> : <pre>{page.data?.content}</pre>}
        <div className="attachment-pages">
          <Button
            disabled={offsets.length === 1 || page.isFetching}
            onClick={() => setOffsets((value) => value.slice(0, -1))}
          >
            上一段
          </Button>
          <span>
            第 {offsets.length} 段 · 共 {attachment.characters.toLocaleString()} 字
          </span>
          <Button
            disabled={page.data?.next_offset == null || page.isFetching}
            onClick={() => {
              if (page.data?.next_offset != null)
                setOffsets((value) => [...value, page.data!.next_offset!]);
            }}
          >
            下一段
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export function AttachmentList({
  attachments,
  onRemove,
  disabled = false,
}: {
  attachments: ChatAttachment[];
  onRemove?: (id: string) => void;
  disabled?: boolean;
}) {
  const [preview, setPreview] = useState<ChatAttachment>();
  if (!attachments.length) return null;
  return (
    <div className="chat-attachments" aria-label="附加文档">
      {attachments.map((attachment) => (
        <div className="chat-attachment" key={attachment.id}>
          <FileText size={17} />
          <button
            type="button"
            className="attachment-name"
            title={attachment.parse_notes}
            onClick={() => setPreview(attachment)}
          >
            <span>{attachment.filename}</span>
            <small>
              {Math.max(1, Math.ceil(attachment.size / 1024))} KB ·{' '}
              {attachment.parse_status === 'partial' ? '部分内容可读' : '可读取'}
            </small>
          </button>
          {onRemove && (
            <button
              type="button"
              disabled={disabled}
              aria-label={`移除附件 ${attachment.filename}`}
              onClick={() => onRemove(attachment.id)}
            >
              <X size={13} />
            </button>
          )}
        </div>
      ))}
      {preview && (
        <AttachmentPreview
          key={preview.id}
          attachment={preview}
          onClose={() => setPreview(undefined)}
        />
      )}
    </div>
  );
}
