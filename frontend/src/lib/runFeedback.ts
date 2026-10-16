import type { ErrorFeedback, Run } from '../types.ts';

export const runStages: Record<string, string> = {
  queued: '等待运行',
  connecting_model: '连接模型',
  connecting_mcp: '连接知识服务',
  thinking: '正在思考',
  reading_source: '读取源码',
  reading_debug: '检索调试记录',
  reading_materials: '检索资料正文',
  checking_sources: '核对源码引用',
  reading_wiki: '查阅 DeepWiki',
  reading_memory: '读取记忆与历史',
  compacting: '压缩上下文',
  generating: '生成回复',
  completed: '运行已结束',
  continuing_answer: '接着生成回复',
  partial_review: '部分核查完成',
  answer_incomplete: '回答未完整',
  answer_suspected_truncated: '回答可能被截断',
  failed: '运行失败',
  cancelled: '已停止',
  interrupted: '运行中断',
};

export function elapsedRun(run: Run, now = Date.now()) {
  const start = new Date(run.created_at || run.started_at || '').getTime();
  const end = new Date(run.finished_at || '').getTime();
  if (!Number.isFinite(start)) return '';
  const seconds = Math.max(0, Math.floor(((Number.isFinite(end) ? end : now) - start) / 1000));
  return seconds < 60 ? `${seconds} 秒` : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`;
}

const descriptions: Record<string, Pick<ErrorFeedback, 'hint' | 'action'>> = {
  authentication: { hint: '请检查 API 密钥、接口地址和访问权限。', action: 'settings' },
  configuration: { hint: '填写模型接口和密钥后再试。', action: 'settings' },
  rate_limit: { hint: '供应商限制了请求频率，请稍后重试。', action: 'retry' },
  timeout: { hint: '模型响应超时，可以重试或调整连接超时。', action: 'retry' },
  connection: { hint: '请检查网络和模型接口地址。', action: 'settings' },
  provider_unavailable: { hint: '模型服务暂时不可用，请稍后重试。', action: 'retry' },
  context_limit: { hint: '查看并压缩上下文后重试。', action: 'context' },
  mcp_connection: { hint: '本地源码仍可使用，可以在 MCP 设置中检查连接。', action: 'mcp_settings' },
};

export function persistedFeedback(run: Run): ErrorFeedback {
  return {
    text: run.error || '运行已中断，生成的内容保留。',
    code: run.error_code,
    ...descriptions[run.error_code || ''],
  };
}
