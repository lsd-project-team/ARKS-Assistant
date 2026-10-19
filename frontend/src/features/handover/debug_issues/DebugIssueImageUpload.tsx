import { useState } from 'react';
import type { Client } from '../shared/client';
import type { HandoverRecord } from '../shared/types';
import { ErrorText } from '../../../shared/ui/ui';

export function DebugIssueImageUpload({
  row,
  client,
  onChanged,
}: {
  row: HandoverRecord;
  client: Client;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  async function upload(files: File[]) {
    if (!files.length) return;
    setBusy(true);
    setError(undefined);
    let current = row;
    try {
      for (const file of files) {
        current = await client.uploadDebugImage<HandoverRecord>(current.id, current.version, file);
      }
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
      onChanged();
    }
  }
  return (
    <div className="debug-image-upload">
      <label>
        {busy ? '正在保存原图…' : '添加原图'}
        <input
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          multiple
          disabled={busy}
          onChange={(event) => {
            const files = Array.from(event.target.files || []);
            event.target.value = '';
            void upload(files);
          }}
        />
      </label>
      <ErrorText error={error} reveal />
    </div>
  );
}
