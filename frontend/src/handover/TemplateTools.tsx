import { useState } from 'react';
import { Button, ErrorText } from '../components/ui';
import type { Client } from './client';
import type { Definitions, HandoverRecord, Kind } from './types';

export function TemplateTools({
  client,
  definitions,
  actor,
  onActor,
  readOnly,
  onSaved,
}: {
  client: Client;
  definitions: Definitions;
  actor: string;
  readOnly: boolean;
  onSaved: (row: HandoverRecord) => void;
  onActor: (actor: string) => void;
}) {
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  async function importFile(file?: File) {
    if (!file) return;
    setBusy(true);
    setError(undefined);
    try {
      if (file.size > 500000) throw new Error('模板文件不能超过 500 KB');
      const content = JSON.parse(await file.text());
      const row = await client.send<HandoverRecord>('/templates/import', {
        kind: content.kind,
        title: content.title,
        payload: content.payload,
        actor,
      });
      onSaved(row);
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="handover-panel">
      <h3>交接模板</h3>
      <p className="handover-muted">
        Word 模板用于线下记录，可回填模板用于整理后导入为待确认记录。填写后的 Word
        可从资料页上传并审核提取。
      </p>
      <ErrorText error={error} />
      {(['interview', 'task', 'plan'] as Kind[]).map((kind) => (
        <div className="handover-actions handover-template-row" key={kind}>
          <span>{definitions.kinds[kind]}</span>
          <Button
            onClick={() =>
              void client
                .download(`/templates/${kind}`, `${definitions.kinds[kind]}模板.docx`)
                .catch(setError)
            }
          >
            下载 Word 模板
          </Button>
          <Button
            onClick={() =>
              void client
                .download(`/templates/${kind}?format=json`, `${definitions.kinds[kind]}模板.json`)
                .catch(setError)
            }
          >
            下载可回填模板
          </Button>
        </div>
      ))}
      {!readOnly && (
        <div className="handover-fields">
          <label>
            <span>整理人</span>
            <input
              maxLength={120}
              value={actor}
              onChange={(event) => onActor(event.target.value)}
            />
          </label>
          <label>
            <span>导入填写的可回填模板</span>
            <input
              type="file"
              accept=".json"
              disabled={busy || !actor.trim()}
              onChange={(event) => void importFile(event.target.files?.[0])}
            />
          </label>
        </div>
      )}
    </section>
  );
}
