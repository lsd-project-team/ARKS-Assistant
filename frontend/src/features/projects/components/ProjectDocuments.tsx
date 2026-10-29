import { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Plus, Upload, Trash2, RotateCcw } from 'lucide-react';
import { api, jsonBody, query } from '../../../app/api/client';
import type { ProjectMaterial } from '../../../shared/types/api';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { MaterialEditor } from './MaterialEditor';
import { MaterialViewer } from './MaterialViewer';
import { toast } from '../../../shared/utils/toasts';
import { useDebouncedValue } from '../../../shared/hooks/useDebouncedValue';

export function ProjectDocuments({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  const [filter, setFilter] = useState('');
  const [state, setState] = useState('active');
  const [editor, setEditor] = useState<{
    material?: ProjectMaterial;
    content?: string;
    sourceName?: string;
  }>();
  const [viewing, setViewing] = useState<ProjectMaterial>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const file = useRef<HTMLInputElement>(null);
  const settled = useDebouncedValue(filter);
  const listing = useQuery({
    queryKey: ['project-materials', state, settled],
    queryFn: ({ signal }) =>
      api<ProjectMaterial[]>(
        `/projects/${projectId}/materials?state=${state}&query=${query(settled)}`,
        { signal },
      ),
  });
  async function open(item: ProjectMaterial, edit = false) {
    setError(undefined);
    try {
      const saved = await api<ProjectMaterial>(`/projects/${projectId}/materials/${item.id}`);
      if (edit) setEditor({ material: saved });
      else setViewing(saved);
    } catch (reason) {
      setError(reason);
    }
  }
  async function change(item: ProjectMaterial) {
    setPending(true);
    setError(undefined);
    try {
      await api(`/projects/${projectId}/materials/${item.id}`, {
        method: 'PATCH',
        body: jsonBody({ version: item.version, state: state === 'active' ? 'deleted' : 'active' }),
      });
      toast(state === 'active' ? '资料已移入回收站，历史引用仍保留' : '资料已恢复');
    } catch (reason) {
      setError(reason);
    } finally {
      setPending(false);
    }
  }
  async function upload(selected: File) {
    setError(undefined);
    try {
      if (!/\.(md|txt|markdown|csv|json|yaml|yml)$/i.test(selected.name))
        throw new Error('请选择 Markdown 或文本文件（TXT、CSV、JSON、YAML）');
      if (selected.size > 1500000) throw new Error('文档超过 1.5 MB，请拆分后添加');
      const bytes = await selected.arrayBuffer();
      let text: string;
      try {
        text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
      } catch {
        text = new TextDecoder('gb18030', { fatal: true }).decode(bytes);
      }
      if (text.includes('\0') || text.length > 500000)
        throw new Error('请选择不超过 50 万字的文本资料');
      setEditor({ content: text, sourceName: selected.name });
    } catch (reason) {
      setError(reason);
    }
  }
  return (
    <article>
      <div className="material-heading">
        <h2>
          <FileText size={16} />
          项目资料
        </h2>
        <button
          className="material-trash-toggle"
          onClick={() => setState(state === 'active' ? 'deleted' : 'active')}
        >
          {state === 'active' ? '回收站' : '返回资料'}
        </button>
      </div>
      <p className="muted">
        文档和已确认的结论供本项目的对话检索，并附资料来源。关闭对话中的“本地知识资料”后，本轮不检索这些内容。
      </p>
      <div className="material-tools">
        <input
          aria-label="搜索项目资料"
          placeholder="搜索资料标题或正文…"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        />
        {state === 'active' && !readOnly && (
          <>
            <Button onClick={() => setEditor({})}>
              <Plus size={14} />
              文档
            </Button>
            <Button onClick={() => file.current?.click()}>
              <Upload size={14} />
              导入文件
            </Button>
          </>
        )}
      </div>
      <input
        ref={file}
        hidden
        type="file"
        accept=".md,.markdown,.txt,.csv,.json,.yaml,.yml"
        onChange={(event) => {
          const selected = event.target.files?.[0];
          if (selected) void upload(selected);
          event.target.value = '';
        }}
      />
      <ErrorText error={error || listing.error} />
      {listing.isPending ? (
        <p className="muted">正在读取资料…</p>
      ) : !listing.data?.length ? (
        <p className="muted">
          {state === 'active' ? '还没有项目资料，可以添加文档或导入文件。' : '资料回收站为空。'}
        </p>
      ) : (
        listing.data.map((item) => (
          <div className="material-row" key={item.id}>
            <button
              className="material-title"
              disabled={state === 'deleted'}
              onClick={() => void open(item)}
            >
              <strong>{item.title}</strong>
              <small>
                {item.kind === 'conclusion' ? '共享结论' : '文档'} · 版本 {item.version}
                {item.source_name ? ` · ${item.source_name}` : ''}
              </small>
            </button>
            {!readOnly && (
              <div className="material-row-actions">
                {state === 'active' && (
                  <Button disabled={pending} onClick={() => void open(item, true)}>
                    编辑
                  </Button>
                )}
                <Button
                  disabled={pending}
                  title={state === 'active' ? '移入资料回收站' : '恢复资料'}
                  onClick={() => void change(item)}
                >
                  {state === 'active' ? <Trash2 size={14} /> : <RotateCcw size={14} />}
                </Button>
              </div>
            )}
          </div>
        ))
      )}
      {editor && (
        <MaterialEditor
          projectId={projectId}
          material={editor.material}
          initialContent={editor.content}
          sourceName={editor.sourceName}
          onClose={() => setEditor(undefined)}
        />
      )}
      {viewing && <MaterialViewer material={viewing} onClose={() => setViewing(undefined)} />}
    </article>
  );
}
