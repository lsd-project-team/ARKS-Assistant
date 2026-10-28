import { useState } from 'react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useAuth } from '../../auth/AuthContext';
import type { Client } from '../shared/client';
import { HandoverModal } from '../shared/HandoverModal';
import type { HandoverRecord } from '../shared/types';

const maxFileSize = 32 * 1024 * 1024;

export function SourceImport({
  client,
  onSaved,
  onClose,
}: {
  client: Client;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
}) {
  const user = useAuth().session?.user;
  const [file, setFile] = useState<File>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const fileError =
    file && (!file.size ? '文件不能为空。' : file.size > maxFileSize ? '文件不能超过 32 MB。' : '');
  async function save() {
    if (!file || fileError || !user || busy) return;
    setBusy(true);
    setError(undefined);
    try {
      // 上传人由服务端登录会话确定，表单仅提交原文件。
      onSaved(await client.upload<HandoverRecord>(file, {}));
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }
  return (
    <HandoverModal
      title="添加资料"
      description="上传原文件，点击资料即可查看或下载。"
      onClose={onClose}
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
      footer={
        <>
          <Button type="button" disabled={busy} onClick={onClose}>
            取消
          </Button>
          <Button
            className="primary"
            type="submit"
            disabled={busy || !file || !!fileError || !user}
          >
            {busy ? '正在上传…' : '上传'}
          </Button>
        </>
      }
    >
      <ErrorText error={error || fileError} reveal />
      <label className="handover-field-wide">
        <span>文件</span>
        <input
          required
          disabled={busy}
          type="file"
          aria-label="文件"
          onChange={(event) => {
            setFile(event.target.files?.[0]);
            setError(undefined);
          }}
        />
        <small>原样保存，单个文件不超过 32 MB。</small>
      </label>
    </HandoverModal>
  );
}
