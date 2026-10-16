import { useEffect, useState } from 'react';
import { jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useProjectApi } from '../hooks/useProjectApi';
import { useAuth } from '../../auth/AuthContext';
import { browserDraftStorage, readCodeFileDraft, writeCodeFileDraft } from '../lib/codeFileDraft';
import {
  codeWorkError,
  contentHash,
  filePatchRequest,
  normalizeChangePath,
} from '../lib/codeWorkRules';
import type { ChangeFile, CodeChange } from '../types/codeWork';

export function ChangeFileEditor({
  changeId,
  projectId,
  selectedPath,
  disabled,
  onSaved,
  onDirtyChange,
}: {
  changeId: string;
  projectId: string;
  selectedPath: string;
  disabled: boolean;
  onSaved: (change: CodeChange) => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const api = useProjectApi();
  const accountId = useAuth().session?.user.id || '';
  const scope = { accountId, projectId, changeId };
  const [restored] = useState(() => readCodeFileDraft(browserDraftStorage(), scope));
  const [restoredNotice, setRestoredNotice] = useState(!!restored);
  const [draftStorageError, setDraftStorageError] = useState(false);
  const [path, setPath] = useState(restored?.file.path || selectedPath);
  const [file, setFile] = useState<ChangeFile | undefined>(restored?.file);
  const [draft, setDraft] = useState(restored?.draft || '');
  const [hashes, setHashes] = useState({ before: '', after: '' });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const dirty = !!file && draft !== file.content;

  function updateDraft(value: string, baseline = file) {
    setDraft(value);
    if (baseline)
      setDraftStorageError(
        !writeCodeFileDraft(browserDraftStorage(), scope, { file: baseline, draft: value }),
      );
  }

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  useEffect(() => {
    if (selectedPath) setPath(selectedPath);
  }, [selectedPath]);
  useEffect(() => {
    onDirtyChange(dirty);
  }, [dirty, onDirtyChange]);
  useEffect(() => {
    let active = true;
    setHashes({ before: '', after: '' });
    if (file)
      void Promise.all([contentHash(file.content), contentHash(draft)])
        .then(([before, after]) => {
          if (active) setHashes({ before, after });
        })
        .catch(() => {
          /* 文件版本仍由服务器校验；浏览器不支持摘要时不伪造 hash。 */
        });
    return () => {
      active = false;
    };
  }, [file, draft]);

  async function readFile() {
    if (pending || dirty) return;
    setPending(true);
    setError(undefined);
    try {
      const requested = normalizeChangePath(path);
      const loaded = await api<ChangeFile>(
        `/code-changes/${encodeURIComponent(changeId)}/file?path=${encodeURIComponent(requested)}`,
      );
      setFile(loaded);
      updateDraft(loaded.content, loaded);
      setRestoredNotice(false);
    } catch (reason) {
      setError(codeWorkError(reason));
    } finally {
      setPending(false);
    }
  }

  async function save() {
    if (!file || disabled || pending || !dirty) return;
    setPending(true);
    setError(undefined);
    try {
      const next = await api<CodeChange>(`/code-changes/${encodeURIComponent(changeId)}/file`, {
        method: 'PATCH',
        body: jsonBody(filePatchRequest(file, draft)),
      });
      onSaved(next);
      // 保存后重新读取版本；失败时保留原草稿，用户仍可复制和处理冲突。
      const loaded = await api<ChangeFile>(
        `/code-changes/${encodeURIComponent(changeId)}/file?path=${encodeURIComponent(file.path)}`,
      );
      setFile(loaded);
      updateDraft(loaded.content, loaded);
      setRestoredNotice(false);
    } catch (reason) {
      setError(codeWorkError(reason));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="code-work-file-editor">
      <h3>编辑副本文件</h3>
      <form
        className="code-work-inline"
        onSubmit={(event) => {
          event.preventDefault();
          void readFile();
        }}
      >
        <input
          aria-label="副本文件路径"
          placeholder="相对路径，例如 src/Program.cs"
          value={path}
          onChange={(event) => setPath(event.target.value)}
          disabled={pending}
          maxLength={1000}
        />
        <Button type="submit" disabled={pending || dirty || !path.trim()}>
          读取文件
        </Button>
      </form>
      {dirty && <p className="muted">当前修改尚未保存。保存或放弃本次编辑后，可以重新读取文件。</p>}
      {restoredNotice && (
        <p className="muted">已恢复本账号在此项目和副本中的会话草稿；保存时仍会核对原读取版本。</p>
      )}
      {dirty && (
        <p className="muted">
          {draftStorageError
            ? '当前浏览器无法暂存草稿，请先保存或复制后离开。'
            : '草稿仅暂存在当前浏览器会话，关闭会话后不保留。'}
        </p>
      )}
      <ErrorText error={error} />
      {file && (
        <>
          <p className="code-work-source-version">
            正在编辑：{file.path}
            <br />
            读取版本：{file.exists === false ? '新文件（副本中尚不存在）' : file.version}
          </p>
          <div className="code-work-editor-columns">
            <label>
              读取时的正文
              <textarea
                aria-label="修改前文件正文"
                value={file.content}
                readOnly
                rows={12}
                spellCheck={false}
              />
            </label>
            <label>
              修改后的正文
              <textarea
                aria-label="修改后文件正文"
                value={draft}
                onChange={(event) => updateDraft(event.target.value)}
                rows={12}
                spellCheck={false}
                disabled={disabled || pending}
                maxLength={2000000}
              />
            </label>
          </div>
          <dl className="code-work-hashes">
            <dt>修改前正文 UTF-8 SHA-256</dt>
            <dd>{hashes.before || '正在计算或浏览器不支持'}</dd>
            <dt>修改后正文 UTF-8 SHA-256</dt>
            <dd>{hashes.after || '正在计算或浏览器不支持'}</dd>
          </dl>
          <p className="muted">
            上方预览摘要按正文 UTF-8 计算；文件字节的实际 SHA-256
            以读取版本和已保存差异中的版本为准。
          </p>
          <div className="code-work-actions">
            <Button
              className="primary"
              disabled={disabled || pending || !dirty}
              onClick={() => void save()}
            >
              {pending
                ? '处理中…'
                : file.exists === false
                  ? '创建文件至隔离副本'
                  : '保存至隔离副本'}
            </Button>
            <Button
              disabled={pending || !dirty}
              onClick={() => {
                updateDraft(file.content);
                setRestoredNotice(false);
                setError(undefined);
              }}
            >
              放弃本次编辑
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
