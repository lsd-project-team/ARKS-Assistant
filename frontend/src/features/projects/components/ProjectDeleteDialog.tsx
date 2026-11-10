import { useId, useRef, useState } from 'react';
import { api } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import type { Project } from '../../../shared/types/api';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { toast } from '../../../shared/utils/toasts';
import { invalidateProjectCaches, projectCache } from '../lib/projectCache';

export function ProjectDeleteDialog({
  project,
  onClose,
}: {
  project: Project;
  onClose: () => void;
}) {
  const choicesId = useId();
  const [disposition, setDisposition] = useState<'independent' | 'trash'>('independent');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const submitting = useRef(false);

  async function remove() {
    // 同步锁避免请求状态完成渲染前重复点击，失败后允许重试。
    if (submitting.current) return;
    submitting.current = true;
    setPending(true);
    setError(undefined);
    try {
      await api(`/projects/${project.id}?disposition=${disposition}`, { method: 'DELETE' });
    } catch (reason) {
      setError(reason);
      setPending(false);
      submitting.current = false;
      return;
    }
    useWorkspace.getState().removeProject(project.id, disposition);
    projectCache(project.id).clear();
    void invalidateProjectCaches(['projects', 'project', 'threads', 'project-threads', 'thread']);
    onClose();
    toast(
      disposition === 'trash' ? '项目已删除，对话已移入回收站' : '项目已删除，对话已移至独立对话',
    );
  }

  return (
    <Modal
      open
      title="删除项目"
      onClose={() => !pending && onClose()}
      className="confirmation-dialog project-delete-dialog"
    >
      <div className="dialog-body">
        <p>删除“{project.name}”后，项目将从列表移除。请选择项目内对话的处理方式：</p>
        <fieldset
          className="project-delete-options"
          disabled={pending}
          aria-label="项目内对话的处理方式"
        >
          <label className="project-delete-option">
            <input
              type="radio"
              name={choicesId}
              checked={disposition === 'independent'}
              onChange={() => setDisposition('independent')}
            />
            <span>
              <strong>保留对话，移至独立对话</strong>
              <small>保留消息和引用，已删除的对话仍在回收站。</small>
            </span>
          </label>
          <label className="project-delete-option">
            <input
              type="radio"
              name={choicesId}
              checked={disposition === 'trash'}
              onChange={() => setDisposition('trash')}
            />
            <span>
              <strong>对话移入回收站</strong>
              <small>之后可在回收站恢复对话。</small>
            </span>
          </label>
        </fieldset>
        <p className="muted">
          源码文件和交接工作台资料不受影响，未发送的新对话草稿会保留到独立对话。
        </p>
        <ErrorText error={error} />
      </div>
      <div className="modal-footer">
        <Button disabled={pending} onClick={onClose}>
          取消
        </Button>
        <Button className="danger-button" disabled={pending} onClick={() => void remove()}>
          {pending ? '正在删除…' : '删除项目'}
        </Button>
      </div>
    </Modal>
  );
}
