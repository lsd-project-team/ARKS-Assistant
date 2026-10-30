import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import type { Project } from '../../../shared/types/api';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { toast } from '../../../shared/utils/toasts';
import { useProjects } from '../hooks/useProjects';
import { useProjectAssociation } from '../hooks/useProjectAssociation';
import { useAuth } from '../../auth/AuthContext';

export function ProjectEditor({
  project,
  onClose,
  onCreated,
}: {
  project?: Project;
  onClose: () => void;
  onCreated?: () => void;
}) {
  const canConfigureSource = useAuth().session?.user.role === 'admin';
  const availableProjects = useProjects();
  const [name, setName] = useState(project?.name || '');
  const [root, setRoot] = useState(project?.source_root || '');
  // 精简表单不再编辑附加目录，保存时保留已有项目的关联。
  const folders = project?.source_folders || [];
  const [wiki, setWiki] = useState(project?.deepwiki_repo || '');
  const [automatic, setAutomatic] = useState(!project);
  const effectiveRoot =
    root ||
    (!project && !canConfigureSource
      ? availableProjects.data?.default_source?.source_root || ''
      : '');
  const association = useProjectAssociation(
    effectiveRoot,
    folders.map((folder) => folder.root),
    automatic,
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const cache = useQueryClient();
  async function save() {
    setPending(true);
    setError(undefined);
    try {
      const saved = await api<Project>(project ? `/projects/${project.id}` : '/projects', {
        method: project ? 'PATCH' : 'POST',
        body: jsonBody({
          name: name.trim(),
          source_root: effectiveRoot.trim() || null,
          source_folders: folders.map((folder) => ({
            root: folder.root.trim(),
            label: folder.label.trim(),
          })),
          deepwiki_repo: automatic ? '' : wiki.trim(),
          auto_associate: automatic,
        }),
      });
      await cache.invalidateQueries({ queryKey: ['projects'] });
      await cache.invalidateQueries({ queryKey: ['project', saved.id] });
      if (
        project &&
        (project.source_root !== saved.source_root ||
          JSON.stringify(project.source_folders) !== JSON.stringify(saved.source_folders))
      ) {
        // 更换源码目录后清理该项目的阅读状态，旧消息的引用仍按原目录打开。
        useWorkspace.getState().resetProjectSource(saved.id);
        if (useWorkspace.getState().projectId === saved.id) {
          await cache.invalidateQueries({ queryKey: ['files'] });
          cache.removeQueries({ queryKey: ['source'] });
        }
      }
      onClose();
      if (!project) {
        useWorkspace.getState().setSidebarView('active');
        useWorkspace.getState().setProjectExpanded(saved.id, true);
        useWorkspace.getState().switchProject(saved.id);
        onCreated?.();
      }
      toast(project ? '项目已保存' : '项目已创建');
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
      title={project ? '项目设置' : '新建项目'}
      className="project-editor"
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <div className="dialog-body project-form">
          <input
            aria-label="项目名称"
            autoFocus
            required
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="项目名称"
          />
          <label>
            主源码目录
            <input
              value={effectiveRoot}
              readOnly={!canConfigureSource}
              maxLength={1024}
              onChange={(event) => setRoot(event.target.value)}
              placeholder={'本机目录，如 D:\\projects\\ZX2200'}
            />
          </label>
          <label>
            DeepWiki 仓库 <span className="muted">可选</span>
            <input
              aria-label="DeepWiki 仓库"
              value={automatic ? association.data?.deepwiki_repo || '' : wiki}
              readOnly={automatic}
              maxLength={200}
              onChange={(event) => setWiki(event.target.value)}
              placeholder={automatic ? '根据源码目录自动识别' : 'owner/repository 或 GitHub 地址'}
            />
          </label>
          <label className="project-association-toggle">
            <input
              type="checkbox"
              checked={automatic}
              onChange={(event) => {
                if (!event.target.checked && association.data?.deepwiki_repo)
                  setWiki(association.data.deepwiki_repo);
                setAutomatic(event.target.checked);
              }}
            />
            自动关联 DeepWiki 仓库
          </label>
          <ErrorText error={error || (automatic ? association.error : undefined)} />
        </div>
        <div className="modal-footer">
          <Button type="button" disabled={pending} onClick={onClose}>
            取消
          </Button>
          <Button
            type="submit"
            className="primary"
            disabled={pending || !name.trim() || association.detecting}
          >
            {pending ? '正在保存…' : project ? '保存' : '创建项目'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
