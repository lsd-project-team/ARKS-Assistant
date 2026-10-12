import { useState } from 'react';
import { api, jsonBody } from '../lib/api';
import { Button, ErrorText, Modal } from './ui';
import { toast } from '../lib/toasts';
import type { ProjectMaterial } from '../types';

export function MaterialEditor({
  projectId,
  material,
  initialContent = '',
  sourceName = '',
  kind = 'document',
  originMessageId,
  onClose,
}: {
  projectId: string;
  material?: ProjectMaterial;
  initialContent?: string;
  sourceName?: string;
  kind?: 'document' | 'conclusion';
  originMessageId?: string;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(material?.title || sourceName || '');
  const [content, setContent] = useState(material?.content || initialContent);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const conclusion = (material?.kind || kind) === 'conclusion';
  async function save() {
    setPending(true);
    setError(undefined);
    try {
      await api(`/projects/${projectId}/materials${material ? `/${material.id}` : ''}`, {
        method: material ? 'PATCH' : 'POST',
        body: jsonBody(
          material
            ? { title, content, version: material.version }
            : { title, content, kind, source_name: sourceName, origin_message_id: originMessageId },
        ),
      });
      toast(conclusion ? '共享结论已保存到此项目' : '项目资料已保存');
      onClose();
    } catch (reason) {
      setError(reason);
    } finally {
      setPending(false);
    }
  }
  return (
    <Modal
      open
      title={material ? '编辑项目资料' : conclusion ? '确认并保存共享结论' : '添加项目文档'}
      description={
        conclusion
          ? '请核对并整理正文，保存后可供此项目的其他对话参考。'
          : '文档会用于此项目的资料检索。'
      }
      onClose={() => !pending && onClose()}
      className="project-editor material-editor"
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <div className="dialog-body project-form">
          <label>
            标题
            <input
              autoFocus
              required
              maxLength={200}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={conclusion ? '例如：报警处理的已确认结论' : '文档标题'}
            />
          </label>
          <label>
            正文
            <textarea
              required
              rows={14}
              maxLength={500000}
              value={content}
              onChange={(event) => setContent(event.target.value)}
              placeholder="粘贴或整理资料正文，支持 Markdown。"
            />
          </label>
          {sourceName && <p className="muted form-hint">来源文件：{sourceName}</p>}
          <ErrorText error={error} />
        </div>
        <div className="modal-footer">
          <Button type="button" disabled={pending} onClick={onClose}>
            取消
          </Button>
          <Button
            type="submit"
            className="primary"
            disabled={pending || !title.trim() || !content.trim()}
          >
            {pending ? '正在保存…' : conclusion ? '确认并保存' : '保存'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
