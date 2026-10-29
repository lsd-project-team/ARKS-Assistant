import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import type { Project } from '../../../shared/types/api';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { toast } from '../../../shared/utils/toasts';
import { useProjects } from '../hooks/useProjects';
import { useProjectAssociation } from '../hooks/useProjectAssociation';
import { Select } from '../../../shared/ui/Select';
import { useAuth } from '../../auth/AuthContext';

export function ProjectEditor({ project, onClose }: { project?: Project; onClose: () => void }) {
  const canConfigureSource = useAuth().session?.user.role === 'admin';
  const availableProjects = useProjects();
  const [name, setName] = useState(project?.name || '');
  const [root, setRoot] = useState(project?.source_root || '');
  const [folders, setFolders] = useState(
    (project?.source_folders || []).map(({ root, label }) => ({ root, label })),
  );
  const [wiki, setWiki] = useState(project?.deepwiki_repo || '');
  const [automatic, setAutomatic] = useState(!project);
  const effectiveRoot =
    root ||
    (!project && !canConfigureSource
      ? availableProjects.data?.default_source?.source_root || ''
      : '');
  const sourceChoices = [
    ...new Map(
      (availableProjects.data?.projects || [])
        .filter((row) => row.source_root)
        .map((row) => [row.source_root!, row]),
    ).values(),
  ];
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
        useWorkspace.getState().switchProject(saved.id, true);
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
          <label>
            项目名称
            <input
              autoFocus
              required
              maxLength={120}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：ZX2200 软件分析"
            />
          </label>
          <label>
            主源码目录 {canConfigureSource && <span className="muted">可选</span>}
            <input
              value={effectiveRoot}
              readOnly={!canConfigureSource}
              maxLength={1024}
              onChange={(event) => setRoot(event.target.value)}
              placeholder={'本机目录，如 D:\\projects\\ZX2200'}
            />
          </label>
          {!!sourceChoices.length && (
            <label>
              选择已关联的源码目录
              <Select
                disabled={!canConfigureSource}
                aria-label="选择已关联的源码目录"
                value={
                  sourceChoices.some((row) => row.source_root === effectiveRoot)
                    ? effectiveRoot
                    : '__manual__'
                }
                onValueChange={(value) => setRoot(value === '__manual__' ? '' : value)}
              >
                <option value="__manual__">填写其他目录</option>
                {sourceChoices.map((row) => (
                  <option key={row.id} value={row.source_root!}>
                    {row.name} · {row.source_root}
                  </option>
                ))}
              </Select>
            </label>
          )}
          {!canConfigureSource && (
            <p className="muted form-hint">自动关联公司 ZX2200 源码，项目和对话仅自己可见。</p>
          )}
          {folders.map((folder, index) => (
            <div className="source-folder-fields" key={index}>
              <label>
                目录显示名称
                <input
                  maxLength={80}
                  readOnly={!canConfigureSource}
                  value={folder.label}
                  onChange={(event) =>
                    setFolders(
                      folders.map((item, position) =>
                        position === index ? { ...item, label: event.target.value } : item,
                      ),
                    )
                  }
                  placeholder="例如：设备接口"
                />
              </label>
              <label>
                附加源码目录
                <input
                  required
                  maxLength={1024}
                  readOnly={!canConfigureSource}
                  value={folder.root}
                  onChange={(event) =>
                    setFolders(
                      folders.map((item, position) =>
                        position === index ? { ...item, root: event.target.value } : item,
                      ),
                    )
                  }
                  placeholder="本机已存在的绝对目录"
                />
              </label>
              <Button
                type="button"
                disabled={!canConfigureSource}
                onClick={() => setFolders(folders.filter((_, position) => position !== index))}
              >
                解除此目录关联
              </Button>
            </div>
          ))}
          <Button
            type="button"
            disabled={!canConfigureSource || folders.length >= 8}
            onClick={() => setFolders([...folders, { root: '', label: '' }])}
          >
            添加源码目录
          </Button>
          {!!folders.length && <p className="muted form-hint">解除关联保留真实文件和历史引用。</p>}
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
          {automatic && (
            <div className="project-association-summary">
              <p className="muted form-hint">
                {association.detecting
                  ? '正在识别源码关联…'
                  : association.data?.note || '选择源码目录后自动识别，也可以先创建空项目。'}
              </p>
              <ErrorText error={association.error} />
            </div>
          )}
          <ErrorText error={error} />
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
