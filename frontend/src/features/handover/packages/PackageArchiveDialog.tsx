import { useState } from 'react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { HandoverModal } from '../shared/HandoverModal';
import type { Client } from '../shared/client';
import type { HandoverRecord } from '../shared/types';

export function PackageArchiveDialog({
  row,
  client,
  actor,
  onActor,
  onClose,
  onChanged,
}: {
  row: HandoverRecord;
  client: Client;
  actor: string;
  onActor: (actor: string) => void;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [opinion, setOpinion] = useState('');
  const [role, setRole] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const restoring = row.state === 'archived';
  const label = restoring ? '恢复交接包' : '归档交接包';
  async function save() {
    setBusy(true);
    setError(undefined);
    try {
      await client.send(`/records/${row.id}/${restoring ? 'restore' : 'archive'}`, {
        version: row.version,
        actor,
        role,
        opinion,
      });
      onChanged();
      onClose();
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <HandoverModal
      title={label}
      description={row.title}
      className="package-archive"
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
          <Button type="submit" className="primary" disabled={busy}>
            {busy ? '正在处理…' : label}
          </Button>
        </>
      }
    >
      <ErrorText error={error} reveal />
      <fieldset disabled={busy}>
        <div className="handover-fields">
          <label>
            <span>操作人</span>
            <input
              required
              maxLength={120}
              value={actor}
              onChange={(event) => onActor(event.target.value)}
            />
          </label>
          <label>
            <span>职责</span>
            <input maxLength={120} value={role} onChange={(event) => setRole(event.target.value)} />
          </label>
          <label className="handover-field-wide">
            <span>{restoring ? '恢复说明' : '归档说明'}</span>
            <textarea
              required
              rows={3}
              maxLength={2000}
              value={opinion}
              onChange={(event) => setOpinion(event.target.value)}
            />
          </label>
        </div>
      </fieldset>
    </HandoverModal>
  );
}
