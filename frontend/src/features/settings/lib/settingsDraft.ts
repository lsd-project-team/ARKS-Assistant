import type {
  AnalysisSettings,
  McpServer,
  ModelSettings,
  Settings,
} from '../../../shared/types/api.ts';

export const defaultAnalysis: AnalysisSettings = {
  mode: 'auto',
  standard_calls: 24,
  deep_calls: 64,
  verification_reserve: 8,
  long_output_tokens: 8192,
  max_continuations: 2,
};

export const emptyModel = (): ModelSettings => ({
  protocol: 'openai',
  base_url: '',
  model: '',
  api_key: '',
  context_tokens: 32768,
  output_tokens: 4096,
  temperature: 0.2,
  timeout_seconds: 120,
  summary_model: '',
});

export function normalizeSettings(settings: Settings): Settings {
  const profiles = settings.model_profiles?.length
    ? settings.model_profiles
    : [{ id: 'default', name: '默认模型', config: settings.model }];
  return {
    ...settings,
    model_profiles: profiles,
    active_profile_id: settings.active_profile_id || profiles[0].id,
    analysis: { ...defaultAnalysis, ...settings.analysis },
  };
}

export function settingsPayload(settings: Settings) {
  // model 是服务端为旧客户端保留的镜像，写入时以配置列表为准。
  const { model: _model, version: _version, ...payload } = settings;
  return {
    ...payload,
    model_profiles: payload.model_profiles.map(
      ({ capabilities: _capabilities, ...profile }) => profile,
    ),
  };
}

function invalidAddress(value: string) {
  try {
    const url = new URL(value);
    return (
      !['http:', 'https:'].includes(url.protocol) ||
      !url.hostname ||
      !!url.username ||
      !!url.password ||
      /\s/.test(value)
    );
  } catch {
    return true;
  }
}

export function validateSettings(settings: Settings): string[] {
  const errors: string[] = [];
  const analysis = { ...defaultAnalysis, ...settings.analysis };
  if (!['auto', 'standard', 'deep'].includes(analysis.mode)) errors.push('分析模式无效');
  for (const [key, min, max] of [
    ['standard_calls', 8, 128],
    ['deep_calls', 16, 192],
    ['verification_reserve', 2, 32],
    ['long_output_tokens', 1024, 65536],
    ['max_continuations', 0, 2],
  ] as const)
    if (!Number.isInteger(analysis[key]) || analysis[key] < min || analysis[key] > max)
      errors.push(`分析设置 ${key} 应为 ${min}–${max} 的整数`);
  if (analysis.deep_calls < analysis.standard_calls)
    errors.push('深度分析预算不能小于普通分析预算');
  if (analysis.verification_reserve >= Math.min(analysis.standard_calls, analysis.deep_calls))
    errors.push('复核预留次数必须小于工具调用预算');
  if (!settings.model_profiles.length || settings.model_profiles.length > 20)
    errors.push('模型配置数量应为 1–20');
  if (!settings.model_profiles.some((profile) => profile.id === settings.active_profile_id))
    errors.push('当前模型配置不存在，请重新选择');
  if (settings.mcp_servers.length > 20) errors.push('MCP 服务最多 20 个');
  const models = new Set<string>();
  for (const profile of settings.model_profiles) {
    const name = profile.name.trim() || '未命名配置';
    const config = profile.config;
    if (!profile.name.trim()) errors.push('模型配置名称不能为空');
    if (!/^[a-zA-Z0-9_-]{1,40}$/.test(profile.id) || models.has(profile.id))
      errors.push(`模型配置 ID 无效或重复：${profile.id}`);
    models.add(profile.id);
    if (config.base_url && invalidAddress(config.base_url))
      errors.push(`${name}：接口地址需要完整的 HTTP 或 HTTPS URL`);
    if (
      !Number.isInteger(config.context_tokens) ||
      config.context_tokens < 2048 ||
      config.context_tokens > 2000000
    )
      errors.push(`${name}：上下文容量应为 2048–2000000 的整数`);
    if (
      !Number.isInteger(config.output_tokens) ||
      config.output_tokens < 256 ||
      config.output_tokens > 65536
    )
      errors.push(`${name}：最大回复 token 应为 256–65536 的整数`);
    if (config.output_tokens >= config.context_tokens - 1024)
      errors.push(`${name}：需要为输入上下文预留至少 1024 token`);
    if (!Number.isFinite(config.temperature) || config.temperature < 0 || config.temperature > 2)
      errors.push(`${name}：温度应为 0–2`);
    if (
      !Number.isInteger(config.timeout_seconds) ||
      config.timeout_seconds < 10 ||
      config.timeout_seconds > 600
    )
      errors.push(`${name}：超时应为 10–600 秒的整数`);
  }
  const servers = new Set<string>();
  for (const server of settings.mcp_servers) {
    if (!server.name.trim()) errors.push('MCP 名称不能为空');
    if (!/^[a-zA-Z0-9_-]{1,40}$/.test(server.id) || servers.has(server.id))
      errors.push(`MCP ID 无效或重复：${server.id}`);
    servers.add(server.id);
    if (server.url && invalidAddress(server.url)) errors.push(`${server.name}：MCP 地址无效`);
    if (server.enabled && server.transport !== 'stdio' && !server.url.trim())
      errors.push(`${server.name}：请填写 MCP 地址`);
    if (server.enabled && server.transport === 'stdio' && !server.command.trim())
      errors.push(`${server.name}：请填写本地 MCP 命令`);
    if (Object.keys(server.headers).some((name) => !/^[!#$%&'*+.^_\x60|~0-9A-Za-z-]+$/.test(name)))
      errors.push(`${server.name}：请求头名称无效`);
    if (Object.values(server.headers).some((value) => /[\r\n]/.test(value)))
      errors.push(`${server.name}：请求头值不能包含换行`);
    if (Object.keys(server.env).some((name) => !/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)))
      errors.push(`${server.name}：环境变量名称无效`);
  }
  return errors;
}

export function parseMcpJson(text: string): McpServer[] {
  const rows: unknown = JSON.parse(text);
  if (!Array.isArray(rows) || rows.some((row) => !row || typeof row !== 'object'))
    throw new Error('MCP JSON 必须是服务器对象数组');
  for (const row of rows) {
    if (typeof row.id !== 'string' || typeof row.name !== 'string')
      throw new Error('每个 MCP 服务器都需要字符串 id 和 name');
    if (row.transport && !['streamable_http', 'sse', 'stdio'].includes(row.transport))
      throw new Error('MCP transport 必须是 streamable_http、sse 或 stdio');
    for (const field of ['url', 'command'])
      if (row[field] !== undefined && typeof row[field] !== 'string')
        throw new Error(`MCP ${field} 必须是字符串`);
    if (row.enabled !== undefined && typeof row.enabled !== 'boolean')
      throw new Error('MCP enabled 必须是布尔值');
    if (
      row.args !== undefined &&
      (!Array.isArray(row.args) || row.args.some((value: unknown) => typeof value !== 'string'))
    )
      throw new Error('MCP args 必须是字符串数组');
    for (const field of ['headers', 'env'])
      if (
        row[field] !== undefined &&
        (!row[field] ||
          Array.isArray(row[field]) ||
          typeof row[field] !== 'object' ||
          Object.values(row[field]).some((value) => typeof value !== 'string'))
      )
        throw new Error(`MCP ${field} 必须是字符串键值对象`);
  }
  return rows.map(
    (row) =>
      ({
        enabled: true,
        transport: 'streamable_http',
        url: '',
        command: '',
        args: [],
        headers: {},
        env: {},
        ...row,
      }) as McpServer,
  );
}
