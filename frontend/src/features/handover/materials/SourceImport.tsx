import { useRef } from 'react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useAuth } from '../../auth/AuthContext';
import type { Client } from '../shared/client';
import { HandoverModal } from '../shared/HandoverModal';
import { useMaterialUploads } from './useMaterialUploads';

const uploadLabels = {
  pending: '待上传',
  uploading: '正在上传…',
  uploaded: '上传成功',
  failed: '上传失败',
  invalid: '无法上传',
};

export function SourceImport({
  client,
  onSaved,
  onClose,
}: {
  client: Client;
  onSaved: () => void;
  onClose: () => void;
}) {
  const user = useAuth().session?.user;
  const fileInput = useRef<HTMLInputElement>(null);
  const upload = useMaterialUploads(client, onSaved, onClose);
  const { items, busy, pending } = upload;
  const succeeded = items.filter((item) => item.state === 'uploaded').length;
  const failuresOnly = pending > 0 && !items.some((item) => item.state === 'pending');
  const complete = items.length > 0 && succeeded === items.length;
  return (
    <HandoverModal
      title="添加资料"
      onClose={upload.close}
      onSubmit={(event) => {
        event.preventDefault();
        if (user) void upload.save();
      }}
      footer={
        <>
          <Button type="button" disabled={busy} onClick={upload.close}>
            {succeeded ? '关闭' : '取消'}
          </Button>
          <Button
            className="primary"
            type={complete ? 'button' : 'submit'}
            onClick={complete ? () => fileInput.current?.click() : undefined}
            disabled={busy || (!pending && !complete) || !user}
          >
            {busy
              ? `正在上传（${succeeded}/${items.length}）…`
              : complete
                ? '继续选择文件'
                : failuresOnly
                  ? `重试失败文件（${pending}）`
                  : pending
                    ? `上传（${pending}）`
                    : '上传'}
          </Button>
        </>
      }
    >
      <label className="handover-field-wide">
        <span>文件</span>
        <input
          ref={fileInput}
          multiple
          disabled={busy}
          type="file"
          aria-label="文件"
          onClick={(event) => {
            event.currentTarget.value = '';
          }}
          onChange={(event) => {
            if (event.target.files?.length) upload.select(Array.from(event.target.files));
          }}
        />
        <small>可多选，单个文件不超过 32 MB。</small>
      </label>
      {complete && (
        <p className="handover-notice" role="status">
          文件已保存，可以继续选择文件上传。
        </p>
      )}
      {items.length > 0 && (
        <>
          <p className="material-upload-summary" role="status">
            已选 {items.length} 个文件，已上传 {succeeded} 个
          </p>
          <ul className="material-upload-list" aria-label="所选文件">
            {items.map((item, index) => (
              <li key={index}>
                <div>
                  <strong>{item.file.name}</strong>
                  <span>{uploadLabels[item.state]}</span>
                  <ErrorText error={item.error} />
                </div>
                {!busy && item.state !== 'uploaded' && (
                  <Button
                    type="button"
                    aria-label={`移除 ${item.file.name}`}
                    onClick={() => upload.remove(index)}
                  >
                    移除
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </HandoverModal>
  );
}
