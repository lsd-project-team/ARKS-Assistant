import { useState } from 'react';
import { FileCode2, X } from 'lucide-react';
import type { Selection, SourceOptions } from '../../../shared/types/api';
import { resolvedSources } from '../../settings/lib/sourceOptions';
import { SourceOptionsControl } from './SourceOptionsControl';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { SelectionPreview } from './SelectionPreview';

export function QuestionEditor({
  title,
  content,
  selections,
  sourceOptions,
  submitLabel,
  onSubmit,
  onClose,
}: {
  title: string;
  content: string;
  selections: Selection[];
  sourceOptions?: Partial<SourceOptions>;
  submitLabel: string;
  onSubmit: (
    content: string,
    selections: Selection[],
    sourceOptions: SourceOptions,
  ) => Promise<unknown>;
  onClose: () => void;
}) {
  const [text, setText] = useState(content);
  const [included, setIncluded] = useState(selections);
  const [sources, setSources] = useState(() => resolvedSources(sourceOptions));
  const [preview, setPreview] = useState<Selection>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [discarding, setDiscarding] = useState(false);
  const dirty =
    text !== content ||
    included.length !== selections.length ||
    JSON.stringify(sources) !== JSON.stringify(resolvedSources(sourceOptions));
  function close() {
    if (busy) return;
    if (dirty) setDiscarding(true);
    else onClose();
  }
  async function save() {
    if (busy || !text.trim()) return;
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit(text.trim(), included, sources);
      onClose();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      open
      onClose={close}
      title={title}
      className="question-editor-dialog"
    >
      <div className="dialog-body question-editor">
        <SourceOptionsControl value={sources} onChange={setSources} disabled={busy} />
        <label>
          问题内容
          <textarea
            autoFocus
            aria-label="编辑问题内容"
            value={text}
            rows={6}
            disabled={busy}
            onChange={(event) => {
              setText(event.target.value);
              setDiscarding(false);
            }}
          />
        </label>
        {included.map((selection, index) => (
          <div className="question-selection" key={`${selection.path}:${index}`}>
            <button onClick={() => setPreview(selection)} title={selection.path}>
              <FileCode2 size={13} />
              {selection.path}
              <small>
                L{selection.start_line}–{selection.end_line}
              </small>
            </button>
            <button
              disabled={busy}
              aria-label={`移除选区 ${selection.path}`}
              onClick={() => setIncluded(included.filter((_, i) => i !== index))}
            >
              <X size={13} />
            </button>
          </div>
        ))}
        {!included.length && <p className="muted">此问题不附带代码选区。</p>}
        <ErrorText error={error} />
        {discarding && (
          <div className="discard-question" role="alert">
            修改尚未保存。<Button onClick={() => setDiscarding(false)}>继续编辑</Button>
            <Button onClick={onClose}>放弃修改</Button>
          </div>
        )}
      </div>
      <div className="modal-footer">
        <Button disabled={busy} onClick={close}>
          取消
        </Button>
        <Button className="primary" disabled={busy || !text.trim()} onClick={() => void save()}>
          {busy ? '正在保存…' : submitLabel}
        </Button>
      </div>
      {preview && <SelectionPreview selection={preview} onClose={() => setPreview(undefined)} />}
    </Modal>
  );
}
