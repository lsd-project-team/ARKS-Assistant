import type { RefObject } from 'react';
import type { ChatAttachment } from '../../../shared/types/api';
import { ACCEPTED_ATTACHMENTS } from './files';
import { AttachmentList } from './AttachmentList';
import type { useAttachments } from './useAttachments';

export function AttachmentUpload({
  uploader,
  attachments,
  sending,
  inputRef,
}: {
  uploader: ReturnType<typeof useAttachments>;
  attachments: ChatAttachment[];
  sending: boolean;
  inputRef: RefObject<HTMLInputElement | null>;
}) {
  return (
    <div className="attachment-upload">
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED_ATTACHMENTS}
        hidden
        aria-label="选择上传文档"
        onChange={(event) => {
          const files = Array.from(event.target.files || []);
          event.target.value = '';
          if (files.length) void uploader.upload(files);
        }}
      />
      <AttachmentList
        attachments={attachments}
        onRemove={uploader.remove}
        disabled={sending || uploader.busy}
      />
      {uploader.jobs.map((job) => (
        <div
          className="attachment-job"
          key={job.id}
          role={job.status === 'failed' ? 'alert' : 'status'}
        >
          <span>
            {job.file.name} ·{' '}
            {job.status === 'failed'
              ? job.error
              : job.status === 'uploading'
                ? '正在上传并解析…'
                : '等待上传…'}
          </span>
          {job.status === 'failed' && (
            <>
              <button
                type="button"
                disabled={uploader.busy || sending}
                onClick={() => void uploader.upload([job.file], job.id)}
              >
                重试
              </button>
              <button type="button" disabled={sending} onClick={() => uploader.discard(job.id)}>
                移除
              </button>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
