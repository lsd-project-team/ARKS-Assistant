import { useState, type FormEvent } from 'react';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { Select } from '../../shared/ui/Select';
import { ledgerClient } from './ledger-client';
import { actionValues } from './ledger-format';
import type { TimingAction, TimingCategory } from './ledger-types';
import { useLedgerOperation } from './useLedgerOperation';

export function ActionEditor({
  scope,
  categories,
  action,
  categoryId,
  onSaved,
  onClose,
}: {
  scope: string;
  categories: TimingCategory[];
  action?: TimingAction | null;
  categoryId: string;
  onSaved: (message: string) => Promise<void>;
  onClose: () => void;
}) {
  const [name, setName] = useState(action?.name || '');
  const [category, setCategory] = useState(action?.category_id || categoryId);
  const [duration, setDuration] = useState(
    action?.duration_seconds == null ? '' : String(action.duration_seconds),
  );
  const [notes, setNotes] = useState(action?.notes || '');
  const operation = useLedgerOperation();
  async function submit(event: FormEvent) {
    event.preventDefault();
    const saved = await operation.run(async (signal) => {
      await ledgerClient(scope).saveAction(
        actionValues(name, category, duration, notes),
        action,
        signal,
      );
      await onSaved(action ? '动作已更新' : '动作已添加');
    });
    if (saved) onClose();
  }
  return (
    <Modal
      open
      title={action ? '编辑动作' : '添加动作'}
      description="耗时以秒为单位，可留空，后续填写或导入。"
      className="ledger-dialog"
      onClose={() => !operation.busy && onClose()}
    >
      <form onSubmit={(event) => void submit(event)} aria-busy={operation.busy}>
        <div className="dialog-body ledger-fields">
          <label>
            动作名称（必填）
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              maxLength={120}
              autoFocus
            />
          </label>
          <label>
            分类
            <Select aria-label="动作所属分类" value={category} onValueChange={setCategory}>
              <option value="">未分类</option>
              {categories.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </Select>
          </label>
          <label>
            耗时（秒）
            <input
              type="number"
              min="0"
              step="any"
              value={duration}
              placeholder="暂未确定可留空"
              onChange={(event) => setDuration(event.target.value)}
            />
          </label>
          <label>
            备注
            <textarea
              rows={3}
              value={notes}
              maxLength={1000}
              placeholder="选填"
              onChange={(event) => setNotes(event.target.value)}
            />
          </label>
          <ErrorText error={operation.error} reveal />
        </div>
        <div className="modal-footer">
          <Button type="button" disabled={operation.busy} onClick={onClose}>
            取消
          </Button>
          <Button type="submit" className="primary" disabled={operation.busy}>
            {operation.busy ? '保存中…' : '保存'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function DeleteActionDialog({
  scope,
  action,
  onSaved,
  onClose,
}: {
  scope: string;
  action: TimingAction;
  onSaved: (message: string) => Promise<void>;
  onClose: () => void;
}) {
  const operation = useLedgerOperation();
  async function remove() {
    if (
      await operation.run(async (signal) => {
        await ledgerClient(scope).deleteAction(action, signal);
        await onSaved('动作已删除');
      })
    )
      onClose();
  }
  return (
    <Modal
      open
      title="删除动作"
      description={`确定删除“${action.name}”吗？删除后无法恢复。`}
      className="ledger-dialog"
      onClose={() => !operation.busy && onClose()}
    >
      <div className="dialog-body">
        <ErrorText error={operation.error} reveal />
      </div>
      <div className="modal-footer">
        <Button disabled={operation.busy} onClick={onClose}>
          取消
        </Button>
        <Button className="danger" disabled={operation.busy} onClick={() => void remove()}>
          {operation.busy ? '删除中…' : '删除动作'}
        </Button>
      </div>
    </Modal>
  );
}
