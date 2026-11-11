import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { Button, ErrorText } from '../../../shared/ui/ui';
import type { WorkSettings } from './types';

const toText = (commands: string[][]) => commands.map((row) => row.join(' ')).join('\n');
const toCommands = (value: string) =>
  value
    .split('\n')
    .map((line) => line.trim().split(/\s+/).filter(Boolean))
    .filter((row) => row.length);

export function WorkspaceEnvironmentPanel({
  onDirtyChange,
}: {
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ['workspace-work-settings'],
    queryFn: () => api<WorkSettings>('/workspace-work'),
  });
  const [root, setRoot] = useState('');
  const [autoApprove, setAutoApprove] = useState(false);
  const [approvalTimeout, setApprovalTimeout] = useState(120);
  const [commandTimeout, setCommandTimeout] = useState(300);
  const [commands, setCommands] = useState('');
  const [version, setVersion] = useState('');
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    const data = query.data;
    if (!data) return;
    setRoot(data.root);
    setAutoApprove(data.auto_approve);
    setApprovalTimeout(data.approval_timeout_seconds);
    setCommandTimeout(data.command_timeout_seconds);
    setCommands(toText(data.commands));
    setVersion(data.version);
    setDirty(false);
    onDirtyChange?.(false);
  }, [query.data, onDirtyChange]);
  const mark = () => {
    setDirty(true);
    onDirtyChange?.(true);
  };
  const save = useMutation({
    mutationFn: () =>
      api<WorkSettings>('/workspace-work', {
        method: 'PUT',
        body: jsonBody({
          root,
          auto_approve: autoApprove,
          approval_timeout_seconds: approvalTimeout,
          command_timeout_seconds: commandTimeout,
          commands: toCommands(commands),
          version,
        }),
      }),
    onSuccess: (data) => {
      setVersion(data.version);
      setDirty(false);
      onDirtyChange?.(false);
      void cache.invalidateQueries({ queryKey: ['workspace-work-settings'] });
    },
  });
  return (
    <div className="work-environment">
      <p className="muted">
        代码工作区直接读写该目录，不再创建副本，也没有合并确认步骤。命令必须命中白名单；默认逐条等待你在右侧面板批准。
      </p>
      <label>
        工作目录
        <input
          value={root}
          placeholder="本机绝对路径，例如 D:\\work\\my-project"
          onChange={(event) => {
            setRoot(event.target.value);
            mark();
          }}
        />
      </label>
      <label className="code-work-checkbox">
        <input
          type="checkbox"
          checked={autoApprove}
          onChange={(event) => {
            setAutoApprove(event.target.checked);
            mark();
          }}
        />
        白名单命令自动执行（不逐条等待批准）
      </label>
      <div className="work-environment-row">
        <label>
          审批超时（秒）
          <input
            type="number"
            min={30}
            max={900}
            value={approvalTimeout}
            onChange={(event) => {
              setApprovalTimeout(Number(event.target.value));
              mark();
            }}
          />
        </label>
        <label>
          命令超时（秒）
          <input
            type="number"
            min={10}
            max={1800}
            value={commandTimeout}
            onChange={(event) => {
              setCommandTimeout(Number(event.target.value));
              mark();
            }}
          />
        </label>
      </div>
      <label>
        命令白名单（每行一条，例如 <code>dotnet test</code>）
        <textarea
          className="work-environment-commands"
          rows={10}
          value={commands}
          spellCheck={false}
          onChange={(event) => {
            setCommands(event.target.value);
            mark();
          }}
        />
      </label>
      <div>
        <Button disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? '正在保存…' : '保存工作区配置'}
        </Button>
        {query.data && !query.data.windows && (
          <span className="muted"> 当前系统不是 Windows，命令与路径需自行核对。</span>
        )}
      </div>
      <ErrorText error={query.error || save.error} />
    </div>
  );
}
