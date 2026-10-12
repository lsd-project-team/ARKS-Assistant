import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Button, ErrorText, Modal } from '../components/ui';
import type { Client } from './client';
import { useHandoverDraft } from './drafts';
import type { Definitions, HandoverRecord } from './types';
import { ids, text } from './types';

export function SourceImport({
  projectId,
  client,
  actor,
  onActor,
  onSaved,
  onClose,
  records,
}: {
  projectId: string;
  client: Client;
  actor: string;
  onActor: (value: string) => void;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
  records: HandoverRecord[];
}) {
  const [mode, setMode] = useState('file');
  const [file, setFile] = useState<File>();
  const { draft, setDraft, clear, restored, warning } = useHandoverDraft(projectId, 'import', {
    title: '',
    payload: {
      provider: '',
      source_version: '',
      device: '',
      path: '',
      material_id: '',
      supersedes: '',
    },
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const materials = useQuery({
    queryKey: ['handover-existing-materials', projectId],
    queryFn: async () => {
      const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/materials`);
      if (!response.ok) throw new Error('无法读取现有项目资料');
      return response.json() as Promise<{ id: string; title: string; version: number }[]>;
    },
    enabled: mode === 'material',
  });
  async function save() {
    setBusy(true);
    setError(undefined);
    try {
      const metadata = Object.fromEntries(
        ['provider', 'source_version', 'device', 'supersedes'].map((key) => [
          key,
          text(draft.payload[key]),
        ]),
      );
      let row: HandoverRecord;
      if (mode === 'file') {
        if (!file) throw new Error('请选择资料文件');
        row = await client.upload(file, { ...metadata, actor });
      } else if (mode === 'source')
        row = await client.send('/sources/capture', {
          ...metadata,
          actor,
          path: text(draft.payload.path),
        });
      else {
        const material = materials.data?.find((row) => row.id === draft.payload.material_id);
        if (!material) throw new Error('请选择现有资料');
        row = await client.send(`/sources/material/${material.id}`, {
          actor,
          version: material.version,
          opinion: '捕获现有项目资料的固定版本',
          supersedes: text(draft.payload.supersedes),
        });
      }
      clear();
      onSaved(row);
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      open
      title="添加交接资料"
      description="保存原件及 SHA256，文本解析用于分析，设备验证须另外记录。"
      className="handover-modal"
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <ErrorText error={error || materials.error || warning} reveal />
        {restored && <p className="handover-notice">已恢复填写的信息，请重新选择本机附件。</p>}
        <fieldset disabled={busy}>
          <div className="handover-fields">
            <label className="handover-field-wide">
              <span>替换哪一份资料</span>
              <select
                aria-label="替换哪一份资料"
                value={text(draft.payload.supersedes)}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    payload: { ...draft.payload, supersedes: event.target.value },
                  })
                }
              >
                <option value="">作为独立的新资料</option>
                {records
                  .filter((row) => row.kind === 'source' && row.state !== 'archived')
                  .map((row) => (
                    <option value={row.id} key={row.id}>
                      {row.title} · {text(row.payload.source_version)} · v{row.version}
                    </option>
                  ))}
              </select>
              <small>替换会保留旧原件，并将引用旧资料的内容标为待重新复核。</small>
            </label>
            <label>
              <span>资料来源</span>
              <select
                aria-label="资料来源"
                value={mode}
                onChange={(event) => setMode(event.target.value)}
              >
                <option value="file">上传文件</option>
                <option value="source">捕获当前项目源码</option>
                <option value="material">引用现有项目资料</option>
              </select>
            </label>
            <label>
              <span>整理人</span>
              <input
                required
                maxLength={120}
                value={actor}
                onChange={(event) => onActor(event.target.value)}
              />
            </label>
            {mode === 'file' && (
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
            )}
            {mode === 'source' && (
              <label className="handover-field-wide">
                <span>项目内相对路径</span>
                <input
                  required
                  maxLength={2000}
                  placeholder="例如：src/MotionController.cs"
                  value={text(draft.payload.path)}
                  onChange={(event) =>
                    setDraft({ ...draft, payload: { ...draft.payload, path: event.target.value } })
                  }
                />
              </label>
            )}
            {mode === 'material' && (
              <label className="handover-field-wide">
                <span>现有项目资料</span>
                <select
                  aria-label="现有项目资料"
                  required
                  value={text(draft.payload.material_id)}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      payload: { ...draft.payload, material_id: event.target.value },
                    })
                  }
                >
                  <option value="">{materials.isPending ? '正在读取…' : '选择资料'}</option>
                  {materials.data?.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.title} · v{row.version}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {mode !== 'material' &&
              Object.entries({
                provider: '提供者',
                source_version: '资料版本或快照标识',
                device: '适用设备',
              }).map(([key, label]) => (
                <label key={key}>
                  <span>{label}</span>
                  <input
                    maxLength={2000}
                    value={text(draft.payload[key])}
                    onChange={(event) =>
                      setDraft({
                        ...draft,
                        payload: { ...draft.payload, [key]: event.target.value },
                      })
                    }
                  />
                </label>
              ))}
          </div>
        </fieldset>
        <div className="handover-form-footer">
          <Button type="button" disabled={busy} onClick={onClose}>
            关闭并保留草稿
          </Button>
          <Button className="primary" disabled={busy || !actor.trim()} type="submit">
            {busy ? '正在解析并保存…' : '保存资料'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function AIOperation({
  client,
  records,
  definitions,
  action,
  actor,
  onActor,
  onSaved,
  onClose,
}: {
  client: Client;
  records: HandoverRecord[];
  definitions: Definitions;
  action: string;
  actor: string;
  onActor: (value: string) => void;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const eligible = records.filter(
    (row) => !['job', 'candidate', 'package'].includes(row.kind) && row.state !== 'archived',
  );
  const labels: Record<string, string> = {
    extract: '提取交接候选',
    plan: '生成接续计划候选',
    framework: '整理软件框架候选',
    training: '整理培训候选',
  };
  return (
    <Modal
      open
      title={labels[action]}
      description="仅分析选择的固定版本，结果进入候选区；AI 不执行源码和设备操作。"
      className="handover-modal"
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setBusy(true);
          void client
            .send<HandoverRecord>('/ai', { action, record_ids: selected, actor })
            .then(onSaved)
            .catch(setError)
            .finally(() => setBusy(false));
        }}
      >
        <ErrorText error={error} reveal />
        <label className="handover-file-select">
          <span>发起人</span>
          <input
            required
            maxLength={120}
            value={actor}
            onChange={(event) => onActor(event.target.value)}
          />
        </label>
        <p className="handover-muted">
          选择 1–20 条资料。生成接续计划时选一个工作项，并附上对应的基线、资料与约束。
        </p>
        <div className="handover-selection-list">
          {eligible.map((row) => (
            <label key={row.id}>
              <input
                type="checkbox"
                checked={selected.includes(row.id)}
                disabled={busy || (!selected.includes(row.id) && selected.length >= 20)}
                onChange={(event) =>
                  setSelected(
                    event.target.checked
                      ? [...selected, row.id]
                      : selected.filter((id) => id !== row.id),
                  )
                }
              />
              <span>
                {row.title}
                <small>
                  {definitions.kinds[row.kind]} · v{row.version} · {definitions.states[row.state]}
                </small>
              </span>
            </label>
          ))}
        </div>
        {!eligible.length && <p className="handover-empty">先添加资料、访谈或工作项。</p>}
        <div className="handover-form-footer">
          <span>已选 {selected.length} 条</span>
          <Button
            type="submit"
            className="primary"
            disabled={busy || !selected.length || !actor.trim()}
          >
            {busy ? '正在提交…' : '开始分析'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function PackageBuilder({
  projectId,
  client,
  records,
  definitions,
  actor,
  onActor,
  onSaved,
  onClose,
}: {
  projectId: string;
  client: Client;
  records: HandoverRecord[];
  definitions: Definitions;
  actor: string;
  onActor: (value: string) => void;
  onSaved: (row: HandoverRecord) => void;
  onClose: () => void;
}) {
  const eligible = records.filter(
    (row) => !['package', 'candidate', 'job'].includes(row.kind) && row.state !== 'archived',
  );
  const { draft, setDraft, clear, warning } = useHandoverDraft(projectId, 'package', {
    title: '设备软件交接包',
    payload: { recipient: '', scope: '', gaps: '', record_ids: eligible.map((row) => row.id) },
  });
  const selected = ids(draft.payload.record_ids);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  return (
    <Modal
      open
      title="生成固定版本交接包"
      description="包内内容保留生成时的版本。包含待确认内容时会明确标注，交接包不代表设备操作已获批准。"
      className="handover-modal"
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setBusy(true);
          void client
            .send<HandoverRecord>('/packages', { ...draft.payload, title: draft.title, actor })
            .then((row) => {
              clear();
              onSaved(row);
            })
            .catch(setError)
            .finally(() => setBusy(false));
        }}
      >
        <ErrorText error={error || warning} reveal />
        <fieldset disabled={busy}>
          <div className="handover-fields">
            <label>
              <span>标题</span>
              <input
                required
                maxLength={200}
                value={draft.title}
                onChange={(event) => setDraft({ ...draft, title: event.target.value })}
              />
            </label>
            <label>
              <span>整理人</span>
              <input
                required
                maxLength={120}
                value={actor}
                onChange={(event) => onActor(event.target.value)}
              />
            </label>
            {Object.entries({
              recipient: '接收对象',
              scope: '交接范围',
              gaps: '缺项与尚未确认的条件',
            }).map(([key, label]) => (
              <label className="handover-field-wide" key={key}>
                <span>{label}</span>
                <textarea
                  aria-label={label}
                  rows={3}
                  value={text(draft.payload[key])}
                  onChange={(event) =>
                    setDraft({ ...draft, payload: { ...draft.payload, [key]: event.target.value } })
                  }
                />
              </label>
            ))}
          </div>
          <h3>包内记录</h3>
          <div className="handover-selection-list">
            {eligible.map((row) => (
              <label key={row.id}>
                <input
                  type="checkbox"
                  checked={selected.includes(row.id)}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      payload: {
                        ...draft.payload,
                        record_ids: event.target.checked
                          ? [...selected, row.id]
                          : selected.filter((id) => id !== row.id),
                      },
                    })
                  }
                />
                <span>
                  {row.title}
                  <small>
                    {definitions.kinds[row.kind]} · v{row.version} · {definitions.states[row.state]}
                  </small>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="handover-form-footer">
          <span>已选 {selected.length} 条</span>
          <Button
            type="submit"
            className="primary"
            disabled={busy || !selected.length || !actor.trim()}
          >
            {busy ? '正在生成…' : '保存交接包快照'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
