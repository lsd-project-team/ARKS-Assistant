import { useState } from 'react';
import { Plus, Trash2, Cable, ChevronDown } from 'lucide-react';
import type { McpProbeResult, McpServer, Settings } from '../../../shared/types/api';
import { parseMcpJson } from '../lib/settingsDraft';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { SecretFields } from './SecretFields';
import { Select } from '../../../shared/ui/Select';
import { useCurrentProject } from '../../projects/hooks/useProjects';

export function McpSettingsPanel({
  settings,
  onChange,
  busy,
  probes,
  onProbe,
  onAdvancedDirty,
}: {
  settings: Settings;
  onChange: (settings: Settings) => void;
  busy: boolean;
  probes: Record<string, { signature: string; result: McpProbeResult }>;
  onProbe: (server: McpServer) => void;
  onAdvancedDirty: (dirty: boolean) => void;
}) {
  const project = useCurrentProject();
  const [chosen, setChosen] = useState(settings.mcp_servers[0]?.id || '');
  const [advanced, setAdvanced] = useState<string>();
  const [error, setError] = useState<unknown>();
  const server = settings.mcp_servers.find((row) => row.id === chosen) || settings.mcp_servers[0];
  const tested = server && probes[server.id];
  const result = tested?.signature === JSON.stringify(server) ? tested.result : undefined;
  function change<K extends keyof McpServer>(key: K, value: McpServer[K]) {
    if (!server) return;
    onChange({
      ...settings,
      mcp_servers: settings.mcp_servers.map((row) =>
        row.id === server.id ? { ...row, [key]: value } : row,
      ),
    });
  }
  function applyJson() {
    try {
      const servers = parseMcpJson(advanced || '[]');
      onChange({ ...settings, mcp_servers: servers });
      setAdvanced(undefined);
      onAdvancedDirty(false);
      setError(undefined);
    } catch (reason) {
      setError(reason);
    }
  }
  return (
    <div className="mcp-settings-panel">
      <p className="muted">
        当前项目的 DeepWiki 仓库：{project.data?.deepwiki_repo || '未关联'}。
        可在项目设置中调整，切换项目时自动使用对应仓库。
      </p>
      <div className="mcp-server-list">
        {settings.mcp_servers.map((row) => (
          <div key={row.id} className={server?.id === row.id ? 'selected' : ''}>
            <button onClick={() => setChosen(row.id)}>
              <Cable size={14} />
              <span>
                {row.name}
                <small>
                  {row.transport === 'stdio'
                    ? '本地 stdio'
                    : row.transport === 'sse'
                      ? 'HTTP / SSE'
                      : 'Streamable HTTP'}
                </small>
              </span>
            </button>
            <label title={row.enabled ? '已启用' : '已停用'}>
              <input
                type="checkbox"
                aria-label={`启用 ${row.name}`}
                checked={row.enabled}
                onChange={(event) =>
                  onChange({
                    ...settings,
                    mcp_servers: settings.mcp_servers.map((item) =>
                      item.id === row.id ? { ...item, enabled: event.target.checked } : item,
                    ),
                  })
                }
              />
            </label>
          </div>
        ))}
      </div>
      <Button
        disabled={busy || settings.mcp_servers.length >= 20}
        onClick={() => {
          const id = `mcp_${crypto.randomUUID().slice(0, 8)}`;
          const row: McpServer = {
            id,
            name: '新知识服务',
            enabled: false,
            transport: 'streamable_http',
            url: '',
            command: '',
            args: [],
            headers: {},
            env: {},
          };
          onChange({ ...settings, mcp_servers: [...settings.mcp_servers, row] });
          setChosen(id);
        }}
      >
        <Plus size={14} />
        新增 MCP 服务
      </Button>
      {!server && <p className="muted">添加知识服务后，可以测试连接并查看它提供的工具。</p>}
      {server && (
        <div className="settings-fields mcp-server-fields">
          <label>
            服务名称
            <input
              maxLength={80}
              value={server.name}
              onChange={(event) => change('name', event.target.value)}
            />
          </label>
          <label>
            连接方式
            <Select
              aria-label="连接方式"
              disabled={busy}
              value={server.transport}
              onValueChange={(value) => change('transport', value as McpServer['transport'])}
            >
              <option value="streamable_http">HTTP / Streamable HTTP</option>
              <option value="sse">HTTP / SSE</option>
              <option value="stdio">本地 stdio</option>
            </Select>
          </label>
          {server.transport === 'stdio' ? (
            <>
              <label>
                本地命令
                <input
                  value={server.command}
                  onChange={(event) => change('command', event.target.value)}
                  placeholder="例如 python 或 npx"
                />
              </label>
              <label>
                参数（每行一个）
                <textarea
                  rows={3}
                  value={server.args.join('\n')}
                  onChange={(event) =>
                    change('args', event.target.value ? event.target.value.split('\n') : [])
                  }
                />
              </label>
              <SecretFields
                title="环境变量"
                values={server.env}
                onChange={(env) => change('env', env)}
              />
            </>
          ) : (
            <>
              <label>
                MCP 地址
                <input
                  value={server.url}
                  onChange={(event) => change('url', event.target.value)}
                  placeholder="https://mcp.deepwiki.com/mcp"
                />
              </label>
              <SecretFields
                title="请求头"
                values={server.headers}
                onChange={(headers) => change('headers', headers)}
              />
            </>
          )}
          <div className="button-row">
            <Button disabled={busy} onClick={() => onProbe(server)}>
              <Cable size={14} />
              测试此服务
            </Button>
            <Button
              disabled={busy}
              onClick={() =>
                onChange({
                  ...settings,
                  mcp_servers: settings.mcp_servers.filter((row) => row.id !== server.id),
                })
              }
            >
              <Trash2 size={14} />
              移除服务
            </Button>
          </div>
          {result && (
            <div className="mcp-tool-results">
              <p>
                {result.name} 已连接 · {result.tools.length} 个工具
              </p>
              {result.tools.map((tool) => (
                <details key={tool.name}>
                  <summary>
                    <ChevronDown size={12} />
                    <code>{tool.name}</code>
                  </summary>
                  <p>{tool.description || '未提供工具说明'}</p>
                  <details>
                    <summary>参数定义</summary>
                    <pre>{JSON.stringify(tool.schema, null, 2)}</pre>
                  </details>
                </details>
              ))}
            </div>
          )}
        </div>
      )}
      <details className="advanced-mcp">
        <summary>高级 JSON 配置</summary>
        <p className="muted">
          headers / env 中的掩码保留已保存值。修改 JSON 后，先应用到表单，再保存配置。
        </p>
        <textarea
          aria-label="高级 MCP JSON"
          className="json-editor"
          rows={8}
          spellCheck={false}
          value={advanced ?? JSON.stringify(settings.mcp_servers, null, 2)}
          onChange={(event) => {
            setAdvanced(event.target.value);
            onAdvancedDirty(true);
          }}
        />
        <div className="button-row">
          <Button disabled={busy || advanced === undefined} onClick={applyJson}>
            应用到表单
          </Button>
          <Button
            disabled={advanced === undefined}
            onClick={() => {
              setAdvanced(undefined);
              onAdvancedDirty(false);
              setError(undefined);
            }}
          >
            取消 JSON 修改
          </Button>
        </div>
        <ErrorText error={error} reveal />
      </details>
    </div>
  );
}
