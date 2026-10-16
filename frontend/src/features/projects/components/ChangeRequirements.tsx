import { useState } from 'react';
import { jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { useProjectApi } from '../hooks/useProjectApi';
import { requirementsPayload } from '../lib/codeReadiness';
import { codeWorkError } from '../lib/codeWorkRules';
import type { ProjectRequest } from '../lib/projectRequest';
import type { CodeChange } from '../types/codeWork';

interface RequirementsDraft {
  title: string;
  goal: string;
  criteria: string;
  constraints: string;
  paths: string;
}

function initial(change: CodeChange): RequirementsDraft {
  return {
    title: change.title,
    goal: change.goal,
    criteria: change.acceptance_criteria?.join('\n') || '',
    constraints: change.constraints || '',
    paths: change.allowed_paths?.join('\n') || '',
  };
}

export async function writeChangeRequirements(
  api: ProjectRequest,
  projectId: string,
  change: CodeChange,
  draft: RequirementsDraft,
) {
  if (!draft.title.trim() || !draft.goal.trim()) throw new Error('请填写修改名称和目标');
  if (!change.change_version || !change.requirements_version)
    throw new Error('当前副本缺少版本信息，请刷新后重试');
  return api<CodeChange>(
    `/code-changes/${encodeURIComponent(change.id)}/requirements`,
    {
      method: 'PUT',
      body: jsonBody({
        title: draft.title.trim(),
        goal: draft.goal.trim(),
        ...requirementsPayload(draft.criteria, draft.constraints, draft.paths),
        change_version: change.change_version,
        requirements_version: change.requirements_version,
      }),
    },
    projectId,
  );
}

export function ChangeRequirements({
  projectId,
  change,
  disabled,
  onSaved,
}: {
  projectId: string;
  change: CodeChange;
  disabled: boolean;
  onSaved: (change: CodeChange) => void;
}) {
  const api = useProjectApi();
  const [snapshot, setSnapshot] = useState(change);
  const [draft, setDraft] = useState(() => initial(change));
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<unknown>();
  const stale =
    change.change_version !== snapshot.change_version ||
    change.requirements_version !== snapshot.requirements_version;
  const blocked = disabled || pending || ['verifying', 'discarded'].includes(change.status);
  const missingVersion = !snapshot.change_version || !snapshot.requirements_version;

  function update(key: keyof RequirementsDraft, value: string) {
    setDraft((previous) => ({ ...previous, [key]: value }));
    setSaved(false);
  }

  async function save() {
    if (blocked || stale || missingVersion) return;
    setPending(true);
    setError(undefined);
    try {
      const next = await writeChangeRequirements(api, projectId, snapshot, draft);
      setSnapshot(next);
      setDraft(initial(next));
      setSaved(true);
      onSaved(next);
    } catch (reason) {
      setError(codeWorkError(reason));
    } finally {
      setPending(false);
    }
  }

  return (
    <details className="code-work-config">
      <summary>编辑需求约定</summary>
      <p className="muted">
        补充或调整本副本的验收标准、约束与范围。保存后旧验证和审核失效，请重新核对差异并验证。
      </p>
      {(stale || missingVersion) && (
        <p role="alert">副本或需求版本已变化，或缺少版本信息；请重新载入当前约定后保存。</p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label>
          修改名称
          <input
            value={draft.title}
            maxLength={160}
            required
            disabled={blocked}
            onChange={(event) => update('title', event.target.value)}
          />
        </label>
        <label>
          修改目标
          <textarea
            value={draft.goal}
            rows={3}
            maxLength={20000}
            required
            disabled={blocked}
            onChange={(event) => update('goal', event.target.value)}
          />
        </label>
        <label>
          验收标准（每行一条）
          <textarea
            value={draft.criteria}
            rows={3}
            maxLength={100000}
            disabled={blocked}
            onChange={(event) => update('criteria', event.target.value)}
          />
        </label>
        <label>
          实现约束
          <textarea
            value={draft.constraints}
            rows={2}
            maxLength={10000}
            disabled={blocked}
            onChange={(event) => update('constraints', event.target.value)}
          />
        </label>
        <label>
          允许修改的路径范围（每行一个相对 glob）
          <textarea
            value={draft.paths}
            rows={2}
            maxLength={200000}
            disabled={blocked}
            onChange={(event) => update('paths', event.target.value)}
          />
        </label>
        <small>路径留空表示项目内未排除文件；验收标准留空时仅可导出草稿。</small>
        <div className="code-work-actions">
          <Button type="submit" disabled={blocked || stale || missingVersion}>
            保存需求约定
          </Button>
          <Button
            type="button"
            disabled={blocked}
            onClick={() => {
              setSnapshot(change);
              setDraft(initial(change));
              setError(undefined);
              setSaved(false);
            }}
          >
            重新载入当前约定
          </Button>
        </div>
      </form>
      {saved && <p role="status">需求约定已保存，请重新验证。</p>}
      <ErrorText error={error} />
    </details>
  );
}
