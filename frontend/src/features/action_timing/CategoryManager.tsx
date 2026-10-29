import { useRef, useState, type FormEvent } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import { Select } from '../../shared/ui/Select';
import { ledgerClient } from './ledger-client';
import type { TimingCategory } from './ledger-types';
import { useLedgerOperation } from './useLedgerOperation';

type Props = {
  scope: string;
  categories: TimingCategory[];
  onSaved: (message: string) => Promise<void>;
  onClose: () => void;
};

export function CategoryManager({ scope, categories, onSaved, onClose }: Props) {
  const [editing, setEditing] = useState<TimingCategory | null>(null);
  const [deleting, setDeleting] = useState<TimingCategory | null>(null);
  const [name, setName] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const operation = useLedgerOperation();
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (
      await operation.run(async (signal) => {
        await ledgerClient(scope).saveCategory(name, editing, signal);
        await onSaved(editing ? '分类已重命名' : '分类已添加');
      })
    ) {
      setEditing(null);
      setName('');
      input.current?.focus();
    }
  }
  return (
    <Modal
      open
      title="分类管理"
      description="新增、重命名或删除分类，动作可在编辑时调整分类。"
      className="ledger-dialog"
      onClose={() => !operation.busy && onClose()}
    >
      <div className="dialog-body ledger-fields">
        <form onSubmit={(event) => void submit(event)} className="ledger-category-form">
          <label htmlFor="ledger-category-name">{editing ? '分类名称' : '新增分类'}</label>
          <div>
            <input
              ref={input}
              id="ledger-category-name"
              required
              maxLength={60}
              autoFocus
              value={name}
              placeholder="输入分类名称"
              disabled={operation.busy}
              onChange={(event) => setName(event.target.value)}
            />
            <Button type="submit" className="primary" disabled={operation.busy}>
              {!editing && <Plus size={15} />}
              {operation.busy ? '保存中…' : editing ? '保存修改' : '添加分类'}
            </Button>
            {editing && (
              <Button
                type="button"
                disabled={operation.busy}
                onClick={() => {
                  setEditing(null);
                  setName('');
                  operation.clearError();
                }}
              >
                取消
              </Button>
            )}
          </div>
        </form>
        <ErrorText error={operation.error} reveal />
        <ul className="ledger-category-list">
          {categories.map((category) => (
            <li key={category.id}>
              <span>
                {category.name}
                <small>{category.count} 个动作</small>
              </span>
              <Button
                className="icon-button"
                title={`重命名${category.name}`}
                aria-label={`重命名${category.name}`}
                disabled={operation.busy}
                onClick={() => {
                  setEditing(category);
                  setName(category.name);
                  operation.clearError();
                  input.current?.focus();
                }}
              >
                <Pencil size={15} />
              </Button>
              <Button
                className="icon-button"
                title={`删除分类${category.name}`}
                aria-label={`删除分类${category.name}`}
                disabled={operation.busy}
                onClick={() => setDeleting(category)}
              >
                <Trash2 size={15} />
              </Button>
            </li>
          ))}
        </ul>
        {!categories.length && <p className="ledger-muted">还没有自定义分类，可以在上方添加。</p>}
        <p className="ledger-muted">“未分类”为默认分组，无需创建。</p>
      </div>
      <div className="modal-footer">
        <Button disabled={operation.busy} onClick={onClose}>
          完成
        </Button>
      </div>
      {deleting && (
        <DeleteCategoryDialog
          scope={scope}
          categories={categories}
          category={deleting}
          onSaved={async (message) => {
            await onSaved(message);
            if (editing?.id === deleting.id) {
              setEditing(null);
              setName('');
            }
          }}
          onClose={() => setDeleting(null)}
        />
      )}
    </Modal>
  );
}

function DeleteCategoryDialog({
  scope,
  categories,
  category,
  onSaved,
  onClose,
}: Props & { category: TimingCategory }) {
  const [target, setTarget] = useState('');
  const operation = useLedgerOperation();
  async function remove() {
    if (
      await operation.run(async (signal) => {
        await ledgerClient(scope).deleteCategory(category, target, signal);
        await onSaved('分类已删除，动作已移至所选分类');
      })
    )
      onClose();
  }
  return (
    <Modal
      open
      title="删除分类"
      description={`删除“${category.name}”后，该分类下的动作会移动到所选分类。`}
      className="ledger-dialog"
      onClose={() => !operation.busy && onClose()}
    >
      <div className="dialog-body ledger-fields">
        <label>
          将动作移至
          <Select
            aria-label="删除分类后动作移至"
            value={target}
            onValueChange={setTarget}
            disabled={operation.busy}
          >
            <option value="">未分类</option>
            {categories
              .filter((item) => item.id !== category.id)
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
          </Select>
        </label>
        <p className="ledger-muted">
          动作及其耗时会保留。如果目标分类有同名动作，会提示冲突并保留原分类。
        </p>
        <ErrorText error={operation.error} reveal />
      </div>
      <div className="modal-footer">
        <Button disabled={operation.busy} onClick={onClose}>
          取消
        </Button>
        <Button className="danger" disabled={operation.busy} onClick={() => void remove()}>
          {operation.busy ? '处理中…' : '删除分类'}
        </Button>
      </div>
    </Modal>
  );
}
