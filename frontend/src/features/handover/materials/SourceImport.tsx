import { useState } from 'react';
import { FileUp, AlignLeft } from 'lucide-react';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { Client } from '../shared/client';
import { HandoverModal } from '../shared/HandoverModal';
import { useHandoverDraft } from '../shared/drafts';
import { text, type HandoverRecord } from '../shared/types';
import './source-import.css';

const maxCharacters = 100000;

export function SourceImport({
  scopeId,
  client,
  actor,
  onActor,
  onSaved,
  onClose,
  replacing,
}: {
  scopeId: string;
  client: Client;
  actor: string;
  onActor: (value: string) => void;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
  replacing?: HandoverRecord;
}) {
  const [file, setFile] = useState<File>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const { draft, setDraft, clear, restored, warning } = useHandoverDraft(
    scopeId,
    replacing ? `source-update:${replacing.id}` : 'import',
    {
      title: replacing?.title || '',
      payload: {
        mode: replacing?.payload.format === 'text' ? 'text' : 'file',
        content: replacing?.payload.format === 'text' ? text(replacing.payload.content) : '',
        notes: text(replacing?.payload.notes),
      },
    },
  );
  const mode = draft.payload.mode === 'text' ? 'text' : 'file';
  const content = text(draft.payload.content);
  const characterCount = Array.from(content).length;
  const tooLong = characterCount > maxCharacters;
  const canSave =
    !!actor.trim() &&
    (mode === 'text' ? !!draft.title.trim() && !!content.trim() && !tooLong : !!file);

  function field(key: string, value: string) {
    setDraft({ ...draft, payload: { ...draft.payload, [key]: value } });
  }
  function changeMode(next: string) {
    setFile(undefined);
    field('mode', next);
    setError(undefined);
  }
  async function save() {
    if (!canSave || busy) return;
    setBusy(true);
    setError(undefined);
    try {
      // 新资料不提交旧草稿中已隐藏的字段；更新时从指定资料保留历史元信息。
      const metadata = {
        notes: text(draft.payload.notes),
        ...(replacing && {
          supersedes: replacing.id,
          provider: text(replacing.payload.provider),
          source_version: text(replacing.payload.source_version),
          device: text(replacing.payload.device),
        }),
      };
      const row =
        mode === 'text'
          ? await client.send<HandoverRecord>('/sources/text', {
              ...metadata,
              title: draft.title.trim(),
              content,
              actor: actor.trim(),
            })
          : await client.upload<HandoverRecord>(file!, { ...metadata, actor: actor.trim() });
      clear();
      onSaved(row);
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <HandoverModal
      title={replacing ? '更新交接资料' : '添加交接资料'}
      description={
        replacing
          ? `更新“${replacing.title}”，旧原件与历史版本会保留。关联内容需重新复核。`
          : '上传文件或直接输入文本，保存原文后可继续确认与 AI 提取。'
      }
      onClose={onClose}
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
      footer={
        <>
          <Button type="button" disabled={busy} onClick={onClose}>
            关闭并保留草稿
          </Button>
          <Button className="primary" disabled={busy || !canSave} type="submit">
            {busy ? '正在保存…' : '保存资料'}
          </Button>
        </>
      }
    >
      <ErrorText error={error || warning} reveal />
      {restored && (
        <p className="handover-notice">
          已恢复上次填写的信息。{mode === 'file' ? '上传文件请重新选择附件。' : ''}
        </p>
      )}
      <fieldset disabled={busy}>
        <div className="handover-fields">
          <div className="handover-field-wide">
            <span className="source-import-label">添加方式</span>
            <div
              className="handover-view-switch source-import-modes"
              role="group"
              aria-label="添加方式"
            >
              <Button
                type="button"
                aria-pressed={mode === 'file'}
                onClick={() => changeMode('file')}
              >
                <FileUp size={15} />
                上传文件
              </Button>
              <Button
                type="button"
                aria-pressed={mode === 'text'}
                onClick={() => changeMode('text')}
              >
                <AlignLeft size={15} />
                输入文本
              </Button>
            </div>
          </div>
          {mode === 'text' && (
            <label>
              <span>资料标题</span>
              <input
                required
                maxLength={200}
                value={draft.title}
                placeholder="例如：ZX2200 HS（DAF）项目日志"
                onChange={(event) => setDraft({ ...draft, title: event.target.value })}
              />
            </label>
          )}
          <label>
            <span>整理人</span>
            <input
              required
              maxLength={120}
              value={actor}
              onChange={(event) => onActor(event.target.value)}
            />
          </label>
          {mode === 'file' ? (
            <label className="handover-field-wide">
              <span>文件</span>
              <input
                required
                type="file"
                aria-label="文件"
                accept=".docx,.pdf,.zip,.txt,.md,.cs,.cpp,.c,.h,.json,.yaml,.yml,.xml,.ini,.log"
                onChange={(event) => setFile(event.target.files?.[0])}
              />
              <small>
                DOCX、文本 PDF、源码 ZIP 或文本文件，最大 32 MB。扫描 PDF 会标出需补充文字的页。
              </small>
            </label>
          ) : (
            <label className="handover-field-wide">
              <span>文本内容</span>
              {/* 不设置 maxlength，避免粘贴时静默截断；超限提示并阻止提交。 */}
              <textarea
                required
                rows={9}
                value={content}
                aria-label="文本内容"
                aria-invalid={tooLong || undefined}
                placeholder="直接粘贴会议纪要、项目日志、聊天记录或技术说明，保留日期、作者与原文。"
                onChange={(event) => field('content', event.target.value)}
              />
              <div className="source-import-text-meta">
                <small>原文会完整保存，后续可通过“AI 提取候选”整理。</small>
                <small className={tooLong ? 'source-import-limit' : undefined}>
                  {characterCount.toLocaleString('zh-CN')} / 100,000 字符
                </small>
              </div>
              {tooLong && (
                <small className="source-import-limit" role="alert">
                  文本超过 100,000 字符，请按主题拆分后保存；当前内容未被截断。
                </small>
              )}
            </label>
          )}
          <label className="handover-field-wide">
            <span>来源说明（选填）</span>
            <textarea
              rows={2}
              maxLength={2000}
              value={text(draft.payload.notes)}
              placeholder="例如：贺强的项目沟通记录，2026年8月14日至9月2日；保留发布时间与事件日期。"
              onChange={(event) => field('notes', event.target.value)}
            />
          </label>
        </div>
      </fieldset>
    </HandoverModal>
  );
}
