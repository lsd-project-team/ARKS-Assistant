import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { WorkRequirement, WorkStatus } from './types';

const empty = { id: '', version: '', name: '', expectation: '', code: '', enabled: true };
export function RequirementPanel({
  status,
  base,
  projectId,
  disabled,
  onChanged,
  onRequest,
}: {
  status: WorkStatus;
  base: string;
  projectId: string;
  disabled: boolean;
  onChanged: () => void;
  onRequest?: (text?: string) => void;
}) {
  const [draft, setDraft] = useState<WorkRequirement>(empty);
  const [deleting, setDeleting] = useState('');
  const save = useMutation({
    mutationFn: () =>
      api(`${base}/requirement`, { method: 'PUT', body: jsonBody(draft) }, projectId),
    onSuccess: () => {
      setDraft(empty);
      onChanged();
    },
  });
  const remove = useMutation({
    mutationFn: (test: WorkRequirement) =>
      api(
        `${base}/requirement/delete`,
        { method: 'POST', body: jsonBody({ id: test.id, version: test.version }) },
        projectId,
      ),
    onSuccess: () => {
      setDeleting('');
      onChanged();
    },
  });
  const desktop = useMutation({
    mutationFn: (enabled: boolean) =>
      api(
        `${base}/desktop-flow`,
        { method: 'PUT', body: jsonBody({ enabled, revision: status.revision }) },
        projectId,
      ),
    onSuccess: onChanged,
  });
  return (
    <div className="code-requirements">
      <div className="code-review-toolbar">
        <strong>本次需求验证</strong>
        {onRequest && (
          <Button
            disabled={disabled}
            onClick={() =>
              onRequest(
                '请先读取当前副本和实际差异，为本次需求添加能检出错误实现的C#断言测试（set_work_requirement），再运行验证；保留已有验收断言。',
              )
            }
          >
            让 AI 补需求测试
          </Button>
        )}
      </div>
      <p className="muted">
        基础编译和仿真继续执行。需求测试使用原业务对象与虚拟硬件，每个用例必须实际执行 Check 断言。
      </p>
      {(status.requirements || []).map((test) => (
        <div key={test.id} className="code-requirement-row">
          <div>
            <strong>{test.name}</strong>
            <span>{test.enabled ? '已启用' : '已停用'}</span>
            <p>{test.expectation}</p>
          </div>
          <Button disabled={disabled} onClick={() => setDraft(test)}>
            查看/编辑
          </Button>
          <Button disabled={disabled} onClick={() => setDeleting(test.id)}>
            删除
          </Button>
          {deleting === test.id && (
            <div role="alert">
              删除此需求测试后需要重新验证。
              <Button disabled={remove.isPending} onClick={() => remove.mutate(test)}>
                确认删除
              </Button>
              <Button onClick={() => setDeleting('')}>保留</Button>
            </div>
          )}
        </div>
      ))}
      <details key={draft.id || 'new'} open={!!draft.id || undefined}>
        <summary>{draft.id ? '编辑需求测试' : '手动添加需求测试'}</summary>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate();
          }}
        >
          <label>
            测试名称
            <input
              value={draft.name}
              maxLength={160}
              required
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          </label>
          <label>
            预期行为
            <textarea
              value={draft.expectation}
              maxLength={2000}
              required
              onChange={(event) => setDraft({ ...draft, expectation: event.target.value })}
            />
          </label>
          <label>
            C# 断言代码
            <textarea
              className="code-test-source"
              value={draft.code}
              maxLength={30000}
              required
              spellCheck={false}
              onChange={(event) => setDraft({ ...draft, code: event.target.value })}
              placeholder={'// 使用原业务对象执行操作后断言\nCheck(实际条件, "预期行为说明");'}
            />
          </label>
          <label className="code-work-checkbox">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
            />
            启用此测试
          </label>
          <div>
            <Button type="submit" disabled={disabled || save.isPending}>
              保存测试
            </Button>
            {draft.id && <Button onClick={() => setDraft(empty)}>取消编辑</Button>}
          </div>
        </form>
      </details>
      <label className="code-work-checkbox">
        <input
          type="checkbox"
          checked={!!status.desktop_flow}
          disabled={disabled || desktop.isPending}
          onChange={(event) => desktop.mutate(event.target.checked)}
        />
        同时验证原桌面界面：加载 → 复位 → 启动 → 暂停 → 继续 → 示例生产 → 停止
      </label>
      <p className="muted">使用独立 Simulation 进程，执行原主窗体按钮事件并保存状态断言和截图。</p>
      <ErrorText error={save.error || remove.error || desktop.error} />
    </div>
  );
}
