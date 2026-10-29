import { useRef, useState, type FormEvent } from 'react';
import { Pencil, Plus } from 'lucide-react';
import { Button, ErrorText, Modal } from '../../shared/ui/ui';
import type { TimingProject } from './ledger-types';
import { timingProjects } from './project-client';
import { useLedgerOperation } from './useLedgerOperation';

export function TimingProjectManager({
  projects,
  onSaved,
  onClose,
}: {
  projects: TimingProject[];
  onSaved: (project: TimingProject, created: boolean) => Promise<void>;
  onClose: () => void;
}) {
  const [editing, setEditing] = useState<TimingProject | null>(null);
  const [name, setName] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const operation = useLedgerOperation();
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (
      await operation.run(async (signal) => {
        const project = await timingProjects.save(name, editing, signal);
        await onSaved(project, !editing);
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
      title="耗时项目管理"
      className="ledger-dialog"
      onClose={() => !operation.busy && onClose()}
    >
      <div className="dialog-body ledger-fields">
        <form className="ledger-category-form" onSubmit={(event) => void submit(event)}>
          <label htmlFor="timing-project-name">{editing ? '耗时项目名称' : '新增耗时项目'}</label>
          <div>
            <input
              ref={input}
              id="timing-project-name"
              autoFocus
              required
              maxLength={120}
              value={name}
              placeholder="例如：智芯2200"
              disabled={operation.busy}
              onChange={(event) => setName(event.target.value)}
            />
            <Button type="submit" className="primary" disabled={operation.busy}>
              {!editing && <Plus size={15} />}
              {operation.busy ? '保存中…' : editing ? '保存修改' : '添加项目'}
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
          {projects.map((project) => (
            <li key={project.id}>
              <span>{project.name}</span>
              <Button
                className="icon-button"
                aria-label={`重命名耗时项目${project.name}`}
                title={`重命名${project.name}`}
                disabled={operation.busy}
                onClick={() => {
                  setEditing(project);
                  setName(project.name);
                  operation.clearError();
                  input.current?.focus();
                }}
              >
                <Pencil size={15} />
              </Button>
            </li>
          ))}
        </ul>
      </div>
      <div className="modal-footer">
        <Button disabled={operation.busy} onClick={onClose}>
          完成
        </Button>
      </div>
    </Modal>
  );
}
