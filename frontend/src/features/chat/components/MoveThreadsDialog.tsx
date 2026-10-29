import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { useProjects } from '../../projects/hooks/useProjects';
import { useWorkspace } from '../../../app/state/store';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { Select } from '../../../shared/ui/Select';
import { toast } from '../../../shared/utils/toasts';

export function MoveThreadsDialog({
  ids,
  onClose,
  onMoved,
}: {
  ids: string[];
  onClose: () => void;
  onMoved?: () => void;
}) {
  const projects = useProjects();
  const current = useWorkspace((state) => state.projectId);
  const [destination, setDestination] = useState('independent');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const cache = useQueryClient();
  async function move() {
    setPending(true);
    try {
      await api('/projects/move-threads', {
        method: 'POST',
        body: jsonBody({ ids, project_id: destination === 'independent' ? null : destination }),
      });
      const state = useWorkspace.getState();
      if (state.projectId === current && ids.includes(state.threadId)) state.selectThread('');
      await cache.invalidateQueries({ queryKey: ['threads'] });
      await cache.invalidateQueries({ queryKey: ['projects'] });
      onMoved?.();
      onClose();
      toast(`已移动 ${ids.length} 个对话`);
    } catch (reason) {
      setError(reason);
    } finally {
      setPending(false);
    }
  }
  return (
    <Modal
      open
      onClose={() => !pending && onClose()}
      title="移动对话"
      className="project-move-dialog"
    >
      <div className="dialog-body project-form">
        <label>
          移至
          <Select value={destination} onValueChange={setDestination} aria-label="目标项目">
            <option value="independent">独立对话</option>
            {(projects.data?.projects || [])
              .filter((project) => project.id !== current)
              .map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
          </Select>
        </label>
        <p className="muted">
          目标项目的指令和资料会用于后续回复。正在运行或有待发问题的对话需要先处理完。
        </p>
        <ErrorText error={error || projects.error} />
      </div>
      <div className="modal-footer">
        <Button disabled={pending} onClick={onClose}>
          取消
        </Button>
        <Button
          className="primary"
          disabled={pending || destination === current}
          onClick={() => void move()}
        >
          {pending ? '正在移动…' : '移动'}
        </Button>
      </div>
    </Modal>
  );
}
