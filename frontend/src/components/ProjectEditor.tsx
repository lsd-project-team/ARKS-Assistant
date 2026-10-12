import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../lib/api';
import { useWorkspace } from '../lib/store';
import type { Project } from '../types';
import { Button, ErrorText, Modal } from './ui';
import { toast } from '../lib/toasts';
import { useProjects } from '../hooks/useProjects';
import { useProjectAssociation } from '../hooks/useProjectAssociation';
import { Select } from './Select';

export function ProjectEditor({ project, onClose }: { project?: Project; onClose: () => void }) {
  const [name, setName] = useState(project?.name || '');
  const [description, setDescription] = useState(project?.description || '');
  const [root, setRoot] = useState(project?.source_root || '');
  const [folders, setFolders] = useState(
    (project?.source_folders || []).map(({ root, label }) => ({ root, label })),
  );
  const [instructions, setInstructions] = useState(project?.instructions || '');
  const [wiki, setWiki] = useState(project?.deepwiki_repo || '');
  const [automatic, setAutomatic] = useState(!project);
  const availableProjects = useProjects();
  const sourceChoices = [
    ...new Map(
      (availableProjects.data?.projects || [])
        .filter((row) => row.source_root)
        .map((row) => [row.source_root!, row]),
    ).values(),
  ];
  const association = useProjectAssociation(
    root,
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
          description,
          source_root: root.trim() || null,
          source_folders: folders.map((folder) => ({
            root: folder.root.trim(),
            label: folder.label.trim(),
          })),
          instructions,
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
      description="将相关对话和资料放在一起。"
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
            项目说明
            <textarea
              rows={2}
              maxLength={5000}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="这个项目希望解决什么问题？"
            />
          </label>
          <label>
            主源码目录 <span className="muted">可选</span>
            <input
              value={root}
              maxLength={1024}
              onChange={(event) => setRoot(event.target.value)}
              placeholder={'本机目录，如 D:\\projects\\ZX2200'}
            />
          </label>
          {!!sourceChoices.length && (
            <label>
              选择已关联的源码目录
              <Select
                aria-label="选择已关联的源码目录"
                value={sourceChoices.some((row) => row.source_root === root) ? root : '__manual__'}
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
          <p className="muted form-hint">可以先创建空项目，之后再关联源码目录。</p>
          {folders.map((folder, index) => (
            <div className="source-folder-fields" key={index}>
              <label>
                目录显示名称
                <input
                  maxLength={80}
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
                onClick={() => setFolders(folders.filter((_, position) => position !== index))}
              >
                解除此目录关联
              </Button>
            </div>
          ))}
          <Button
            type="button"
            disabled={folders.length >= 8}
            onClick={() => setFolders([...folders, { root: '', label: '' }])}
          >
            添加源码目录
          </Button>
          {!!folders.length && (
            <p className="muted form-hint">
              最多关联 8 个附加目录，文件树分别显示。解除关联保留真实文件和历史引用。
            </p>
          )}
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
              {association.data?.knowledge_available && (
                <p className="muted form-hint">该目录已有的流程与功能资料也会自动关联。</p>
              )}
              <p className="muted form-hint">创建后，源码、仓库和项目资料会跟随项目切换。</p>
              <ErrorText error={association.error} />
            </div>
          )}
          <label>
            项目指令
            <textarea
              rows={4}
              maxLength={20000}
              value={instructions}
              onChange={(event) => setInstructions(event.target.value)}
              placeholder="例如：使用中文回答；分析报警时列出触发条件和源码行号。"
            />
          </label>
          <p className="muted form-hint">适用于此项目中的所有对话，保存后从下一次回复开始生效。</p>
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
