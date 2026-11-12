import { useCallback, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { useWorkspace } from '../../../app/state/store';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { WorkEnvironment } from './types';
import './code-work.css';

export function CodeEnvironmentPanel({
  onDirtyChange,
}: {
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const cache = useQueryClient();
  const projectId = useWorkspace((state) => state.projectId);
  const key = ['code-work-environment', projectId ?? ''];
  const [saved, setSaved] = useState(false);
  const dirtyChanged = useCallback(
    (dirty: boolean) => {
      if (dirty) setSaved(false);
      onDirtyChange?.(dirty);
    },
    [onDirtyChange],
  );
  const query = useQuery({
    queryKey: key,
    queryFn: () => api<WorkEnvironment>('/settings/code-work'),
  });
  if (!query.data) return <ErrorText error={query.error} />;
  return (
    <EnvironmentForm
      key={query.data.version}
      environment={query.data}
      onDirtyChange={dirtyChanged}
      saved={saved}
      onSaved={(value) => {
        setSaved(true);
        cache.setQueryData(key, value);
        void cache.invalidateQueries({ queryKey: ['code-work'] });
      }}
    />
  );
}

function EnvironmentForm({
  environment,
  onSaved,
  onDirtyChange,
  saved,
}: {
  environment: WorkEnvironment;
  onSaved: (value: WorkEnvironment) => void;
  onDirtyChange?: (dirty: boolean) => void;
  saved: boolean;
}) {
  const [draft, setDraft] = useState(environment);
  const dirty =
    draft.source_root !== environment.source_root ||
    draft.msbuild !== environment.msbuild ||
    draft.timeout_seconds !== environment.timeout_seconds;
  useEffect(() => onDirtyChange?.(dirty), [onDirtyChange, dirty]);
  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);
  const save = useMutation({
    mutationFn: () =>
      api<WorkEnvironment>('/settings/code-work', {
        method: 'PUT',
        body: jsonBody({
          source_root: draft.source_root,
          msbuild: draft.msbuild,
          timeout_seconds: draft.timeout_seconds,
          version: draft.version,
        }),
      }),
    onSuccess: onSaved,
  });
  return (
    <details className="code-environment">
      <summary>管理员 · 编译与仿真环境</summary>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate();
        }}
      >
        <p className="muted">
          为当前项目单独绑定本机源码与编译环境，各项目互不继承。副本运行使用本机 Windows
          权限，需使用可信源码与依赖。
        </p>
        <label>
          仿真源码目录
          <input
            value={draft.source_root}
            onChange={(event) => setDraft({ ...draft, source_root: event.target.value })}
            placeholder="包含主工程的源码根目录"
          />
        </label>
        {environment.project && (
          <p className="muted">已识别主工程：{environment.project}</p>
        )}
        <label>
          MSBuild.exe
          <input
            value={draft.msbuild}
            onChange={(event) => setDraft({ ...draft, msbuild: event.target.value })}
            placeholder="留空自动查找 Visual Studio"
          />
        </label>
        <label>
          验证时限（秒）
          <input
            type="number"
            min={30}
            max={900}
            value={draft.timeout_seconds}
            onChange={(event) =>
              setDraft({ ...draft, timeout_seconds: Number(event.target.value) })
            }
          />
        </label>
        {!environment.windows && (
          <p className="muted">此服务器需要接入 Windows 执行环境后才能运行仿真。</p>
        )}
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? '正在保存…' : '保存执行环境'}
        </Button>
        {saved && (
          <p className="muted" role="status">
            执行环境已保存
          </p>
        )}
        <ErrorText error={save.error} />
      </form>
    </details>
  );
}
