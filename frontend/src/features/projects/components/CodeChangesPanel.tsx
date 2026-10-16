import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { GitBranch, RefreshCw } from 'lucide-react';
import { apiUrl, jsonBody } from '../../../app/api/client';
import { sessionFetch } from '../../auth/session';
import { Button, ErrorText, Modal } from '../../../shared/ui/ui';
import { Select } from '../../../shared/ui/Select';
import { useProjectApi } from '../hooks/useProjectApi';
import {
  changeCanEdit,
  changeCanVerify,
  changeCanRecordExperience,
  changeStatusLabels,
  codeWorkError,
} from '../lib/codeWorkRules';
import type { ChangeDiff, CodeChange, VerificationProfile } from '../types/codeWork';
import { ChangeFileEditor } from './ChangeFileEditor';
import { VerificationProfiles } from './VerificationProfiles';
import { ChangeExperience } from './ChangeExperience';
import { ChangeDelivery } from './ChangeDelivery';
import { ChangeRequirements } from './ChangeRequirements';
import { executionLabel, requirementsPayload } from '../lib/codeReadiness';

const verificationLabels = {
  running: '运行中',
  passed: '通过',
  failed: '失败',
  timed_out: '超时',
  cancelled: '已取消',
  interrupted: '已中断',
};

export function CodeChangesPanel({
  projectId,
  readOnly,
}: {
  projectId: string;
  readOnly: boolean;
}) {
  const api = useProjectApi();
  const cache = useQueryClient();
  const [selectedId, setSelectedId] = useState('');
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState('');
  const [goal, setGoal] = useState('');
  const [criteria, setCriteria] = useState('');
  const [constraints, setConstraints] = useState('');
  const [allowedPaths, setAllowedPaths] = useState('');
  const [purpose, setPurpose] = useState<'baseline' | 'change'>('change');
  const [profileId, setProfileId] = useState('');
  const [path, setPath] = useState('');
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState('');
  const [discarding, setDiscarding] = useState(false);
  const [error, setError] = useState<unknown>();
  const prefix = ['code-changes', projectId];
  const listing = useQuery({
    queryKey: prefix,
    queryFn: ({ signal }) => api<{ changes: CodeChange[] }>('/code-changes', { signal }),
    refetchInterval: (query) =>
      query.state.data?.changes.some((change) => change.status === 'verifying') ? 2500 : false,
  });
  const profiles = useQuery({
    queryKey: ['code-change-profiles', projectId],
    queryFn: ({ signal }) =>
      api<{ profiles: VerificationProfile[] }>('/code-changes/profiles', { signal }),
  });
  const id = selectedId || listing.data?.changes[0]?.id || '';
  const detail = useQuery({
    queryKey: [...prefix, id],
    queryFn: ({ signal }) => api<CodeChange>(`/code-changes/${encodeURIComponent(id)}`, { signal }),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.status === 'verifying' ? 1500 : false),
  });
  const change = detail.data;
  const diff = useQuery({
    queryKey: [...prefix, id, 'diff'],
    queryFn: ({ signal }) =>
      api<ChangeDiff>(`/code-changes/${encodeURIComponent(id)}/diff`, { signal }),
    enabled: !!change && change.status !== 'discarded',
  });
  const verification = change?.latest_verification;
  const sourceConflict =
    !!diff.data && (!diff.data.source_unchanged || !!diff.data.conflicts.length);
  const configuredProfile = profiles.data?.profiles.find((profile) => profile.id === profileId);

  function changed(next: CodeChange) {
    cache.setQueryData([...prefix, next.id], next);
    void cache.invalidateQueries({ queryKey: prefix });
    void cache.invalidateQueries({ queryKey: ['code-work-readiness', projectId] });
  }

  async function act(action: 'create' | 'verify' | 'cancel' | 'discard') {
    setBusy(action);
    setError(undefined);
    try {
      if (action === 'create' && (!title.trim() || !goal.trim()))
        throw new Error('请填写修改名称和目标');
      const next = await api<CodeChange>(
        action === 'create' ? '/code-changes' : `/code-changes/${encodeURIComponent(id)}/${action}`,
        {
          method: 'POST',
          ...(action === 'create'
            ? {
                body: jsonBody({
                  title: title.trim(),
                  goal: goal.trim(),
                  ...requirementsPayload(criteria, constraints, allowedPaths),
                }),
              }
            : action === 'verify'
              ? { body: jsonBody({ profile_id: configuredProfile?.id, purpose }) }
              : {}),
        },
      );
      setSelectedId(next.id);
      if (action === 'create') {
        setTitle('');
        setGoal('');
        setCriteria('');
        setConstraints('');
        setAllowedPaths('');
        setCreating(false);
        setPath('');
      }
      if (action === 'discard') setDiscarding(false);
      changed(next);
    } catch (reason) {
      setError(codeWorkError(reason));
    } finally {
      setBusy('');
    }
  }

  async function download(path: string, filename: string, method: 'GET' | 'POST' = 'GET') {
    setBusy('download');
    setError(undefined);
    try {
      // 二进制响应也固定发起时的项目，并使用现有账号会话保护。
      const response = await sessionFetch(apiUrl(path, projectId), { method });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(
          typeof body?.detail === 'string' ? body.detail : `下载失败 (${response.status})`,
        );
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) {
      setError(codeWorkError(reason));
    } finally {
      setBusy('');
    }
  }

  return (
    <section className="code-work-panel" aria-label="隔离修改">
      <div className="code-work-heading">
        <div>
          <h2>
            <GitBranch size={17} />
            隔离修改
          </h2>
          <p className="muted">在独立副本中编辑、查看差异和验证，再导出补丁。</p>
        </div>
        <div className="code-work-actions">
          <Button
            disabled={!!busy}
            onClick={() => {
              void cache.invalidateQueries({ queryKey: prefix });
              void profiles.refetch();
            }}
          >
            <RefreshCw size={14} />
            刷新状态
          </Button>
          <Button disabled={readOnly || !!busy || dirty} onClick={() => setCreating(!creating)}>
            {creating ? '收起' : '新建修改'}
          </Button>
        </div>
      </div>
      {creating && (
        <form
          className="code-work-create"
          onSubmit={(event) => {
            event.preventDefault();
            void act('create');
          }}
        >
          <label>
            修改名称
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
              maxLength={160}
              disabled={!!busy || readOnly}
            />
          </label>
          <label>
            修改目标
            <textarea
              rows={3}
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              required
              maxLength={20000}
              disabled={!!busy || readOnly}
            />
          </label>
          <label>
            验收标准（每行一条；留空仅可导出草稿）
            <textarea
              rows={3}
              value={criteria}
              onChange={(event) => setCriteria(event.target.value)}
              disabled={!!busy || readOnly}
              maxLength={20000}
            />
          </label>
          <label>
            实现约束
            <textarea
              rows={2}
              value={constraints}
              onChange={(event) => setConstraints(event.target.value)}
              disabled={!!busy || readOnly}
              maxLength={10000}
            />
          </label>
          <label>
            允许修改的路径范围（每行一个相对 glob）
            <textarea
              rows={2}
              value={allowedPaths}
              onChange={(event) => setAllowedPaths(event.target.value)}
              disabled={!!busy || readOnly}
              placeholder={'src/**\ntests/**'}
            />
            <small>留空表示项目内未排除文件；路径范围由后端强制检查。</small>
          </label>
          <Button className="primary" type="submit" disabled={!!busy || readOnly}>
            创建隔离副本
          </Button>
        </form>
      )}
      <ErrorText
        error={
          error ||
          listing.error ||
          detail.error ||
          profiles.error ||
          (change?.status !== 'discarded' && diff.error)
        }
      />
      {listing.isPending ? (
        <p className="muted">正在读取修改列表…</p>
      ) : !listing.data?.changes.length ? (
        <p className="code-work-empty">
          还没有隔离修改。创建副本后可按文件路径编辑，并通过差异检查结果。
        </p>
      ) : (
        <>
          <Select
            value={id}
            disabled={dirty || !!busy}
            aria-label="选择隔离修改"
            onValueChange={(value) => {
              setSelectedId(value);
              setPath('');
              setError(undefined);
            }}
          >
            {listing.data.changes.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title} · {changeStatusLabels[item.status]}
              </option>
            ))}
          </Select>
          {change && (
            <>
              <div className="code-work-summary">
                <strong role="status">
                  {sourceConflict && change.status === 'passed'
                    ? '历史命令验证通过（原始源码已变化）'
                    : changeStatusLabels[change.status]}
                </strong>
                <span>修改 {change.files_changed} 个文件</span>
              </div>
              <p className="code-work-prose">{change.goal}</p>
              <ChangeRequirements
                key={`${projectId}:${change.id}`}
                projectId={projectId}
                change={change}
                disabled={readOnly || !!busy || dirty}
                onSaved={changed}
              />
              {!!change.acceptance_criteria?.length && (
                <details>
                  <summary>验收标准与实现约束</summary>
                  <ul>
                    {change.acceptance_criteria.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                  <p className="code-work-prose">{change.constraints}</p>
                  <p>允许路径：{change.allowed_paths?.join('、') || '项目内未排除文件'}</p>
                </details>
              )}
              <ErrorText error={change.error} />
              {change.status === 'discarded' ? (
                <p className="code-work-empty">隔离副本已丢弃，原始源码保留。</p>
              ) : (
                <>
                  <ChangeFileEditor
                    key={id}
                    changeId={id}
                    projectId={projectId}
                    selectedPath={path}
                    disabled={readOnly || !!busy || !changeCanEdit(change)}
                    onSaved={changed}
                    onDirtyChange={setDirty}
                  />
                  <div className="code-work-diff">
                    <div className="code-work-heading">
                      <h3>已保存差异</h3>
                      <Button
                        disabled={
                          !!busy || dirty || !diff.data?.diff || change.status === 'verifying'
                        }
                        onClick={() =>
                          void download(
                            `/code-changes/${encodeURIComponent(id)}/export`,
                            `change-${id}.patch`,
                          )
                        }
                      >
                        下载补丁
                      </Button>
                    </div>
                    {diff.isPending ? (
                      <p className="muted">正在读取差异…</p>
                    ) : (
                      diff.data && (
                        <>
                          {diff.data.source_unchanged ? (
                            <p className="muted">已核对原始源码未变化。</p>
                          ) : (
                            <p className="error-text" role="alert">
                              原始源码已发生变化，请先核对冲突；当前副本仍保留。
                              可下载基于旧源码的补丁以保留成果，应用时需人工合并。
                            </p>
                          )}
                          {!!diff.data.conflicts.length && (
                            <div className="error-text" role="alert">
                              存在冲突：
                              <ul>
                                {diff.data.conflicts.map((conflict, index) => (
                                  <li key={index}>{conflict}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {!!diff.data.files.length && (
                            <ul className="code-work-file-list">
                              {diff.data.files.map((file) => (
                                <li key={file.path}>
                                  <button disabled={dirty} onClick={() => setPath(file.path)}>
                                    {file.path}
                                  </button>
                                  <span>{file.status}</span>
                                  <small>
                                    基线 {file.base_version || '不存在'} → 当前{' '}
                                    {file.current_version || '不存在'}
                                  </small>
                                </li>
                              ))}
                            </ul>
                          )}
                          <pre className="code-work-output" aria-label="补丁差异">
                            {diff.data.diff || '尚无已保存的文件差异。'}
                          </pre>
                        </>
                      )
                    )}
                  </div>
                  <div className="code-work-verification">
                    <h3>配置命令验证</h3>
                    {profiles.isPending ? (
                      <p className="muted">正在读取命令配置…</p>
                    ) : !profiles.data?.profiles.length ? (
                      <p className="code-work-empty">
                        尚未配置验证命令。请管理员先配置需要执行的构建或测试命令。
                      </p>
                    ) : (
                      <>
                        <Select
                          value={profileId}
                          onValueChange={setProfileId}
                          aria-label="选择验证命令"
                          disabled={readOnly || !!busy || change.status === 'verifying'}
                        >
                          <option value="">请选择验证命令</option>
                          {profiles.data.profiles.map((profile) => (
                            <option key={profile.id} value={profile.id}>
                              {profile.name}
                            </option>
                          ))}
                        </Select>
                        {configuredProfile && (
                          <>
                            <p>
                              {executionLabel(configuredProfile.executor)} ·{' '}
                              {configuredProfile.environment_label || '环境未命名'}
                            </p>
                            <code className="code-work-command">
                              {JSON.stringify(configuredProfile.argv)}
                            </code>
                          </>
                        )}
                      </>
                    )}
                    <label>
                      验证对象
                      <Select
                        value={purpose}
                        aria-label="验证对象"
                        onValueChange={(value) => setPurpose(value as 'baseline' | 'change')}
                        disabled={readOnly || !!busy || change.status === 'verifying'}
                      >
                        <option value="change">当前修改版本</option>
                        <option value="baseline">原版本基线（独立临时副本）</option>
                      </Select>
                    </label>
                    <div className="code-work-actions">
                      <Button
                        className="primary"
                        disabled={
                          readOnly ||
                          !!busy ||
                          sourceConflict ||
                          !changeCanVerify(change, configuredProfile?.id || '', dirty)
                        }
                        onClick={() => void act('verify')}
                      >
                        执行所选验证
                      </Button>
                      {change.status === 'verifying' && (
                        <Button disabled={readOnly || !!busy} onClick={() => void act('cancel')}>
                          取消运行
                        </Button>
                      )}
                    </div>
                    {dirty && <p className="muted">请先保存或放弃当前编辑，再执行验证。</p>}
                    {verification && (
                      <div className="code-work-verification-result">
                        <strong>
                          最近一次命令验证：{verificationLabels[verification.status]}
                          {verification.stale ? '（修改后已失效）' : ''}
                          {sourceConflict ? '（原始源码已变化，需重新建立并验证）' : ''}
                        </strong>
                        <p>
                          {verification.purpose === 'baseline'
                            ? '原版本基线验证：不代表修改已通过'
                            : '当前修改验证'}{' '}
                          · {executionLabel(verification.executor)}
                        </p>
                        <ErrorText error={verification.error} />
                        <p className="muted">
                          退出码：{verification.exit_code ?? '尚无'} · 开始时间：
                          {new Date(verification.started_at).toLocaleString('zh-CN')}
                        </p>
                        <code className="code-work-command">
                          {JSON.stringify(verification.argv)}
                        </code>
                        <p className="code-work-source-version">
                          验证的修改版本：{verification.change_version || '未提供'}
                        </p>
                        <pre className="code-work-output" aria-label="验证日志">
                          {verification.output ||
                            (verification.status === 'running'
                              ? '正在运行，等待输出…'
                              : '本次命令没有文本输出。')}
                        </pre>
                        {verification.truncated && (
                          <p className="muted">日志较长，当前显示已截断。</p>
                        )}
                        <Button
                          disabled={!!busy}
                          onClick={() =>
                            void download(
                              `/code-changes/${encodeURIComponent(id)}/verifications/${encodeURIComponent(verification.id)}/log`,
                              `verification-${verification.id}.log`,
                            )
                          }
                        >
                          下载完整日志
                        </Button>
                        <p className="muted">
                          命令结果仅对应上面标记的修改版本；真实设备行为需另行验证。
                        </p>
                      </div>
                    )}
                    <VerificationProfiles
                      disabled={readOnly || !!busy}
                      onSaved={() => void profiles.refetch()}
                    />
                    {verification &&
                      diff.data?.source_unchanged &&
                      !sourceConflict &&
                      changeCanRecordExperience(change) && (
                        <ChangeExperience
                          key={verification.id}
                          changeId={id}
                          verification={verification}
                          disabled={readOnly || !!busy || dirty}
                        />
                      )}
                  </div>
                  <ChangeDelivery
                    key={id}
                    projectId={projectId}
                    change={change}
                    profiles={profiles.data?.profiles || []}
                    disabled={readOnly || !!busy || dirty || change.status === 'verifying'}
                    sourceUnchanged={!!diff.data?.source_unchanged && !sourceConflict}
                    onChanged={changed}
                    onDownload={download}
                  />
                  <div className="code-work-actions code-work-discard">
                    <Button
                      disabled={readOnly || !!busy || dirty || !changeCanEdit(change)}
                      onClick={() => setDiscarding(true)}
                    >
                      丢弃隔离副本
                    </Button>
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}
      <Modal
        open={discarding}
        onClose={() => !busy && setDiscarding(false)}
        title="丢弃隔离副本"
        description="清理这个修改的副本文件，原始源码保留。"
      >
        <div className="dialog-body">
          <p>确定丢弃“{change?.title}”的隔离副本？需要保留的补丁请先下载。</p>
          <ErrorText error={error} />
        </div>
        <div className="modal-footer">
          <Button disabled={!!busy} onClick={() => setDiscarding(false)}>
            取消
          </Button>
          <Button disabled={!!busy} onClick={() => void act('discard')}>
            丢弃副本
          </Button>
        </div>
      </Modal>
    </section>
  );
}
