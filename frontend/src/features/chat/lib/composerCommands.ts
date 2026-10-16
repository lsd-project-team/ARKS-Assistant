export type ComposerCommand = 'context' | 'compact' | '记录问题';

export const composerCommands: ReadonlyArray<{
  id: ComposerCommand;
  label: string;
  description: string;
}> = [
  { id: 'context', label: '查看上下文', description: '查看用量、带入资料和压缩摘要' },
  { id: 'compact', label: '压缩上下文', description: '归纳当前对话，保留目标、结论和待办' },
  {
    id: '记录问题',
    label: '记录调试问题',
    description: '输入调试过程，由 AI 整理保存到交接工作台',
  },
];

export function matchingCommands(content: string) {
  const input = content.trim().toLowerCase();
  // 仅把独立的斜杠命令作为操作，包含正文或换行的文本仍按普通消息发送。
  if (!/^\/[a-z\u4e00-\u9fff]*$/.test(input)) return [];
  return composerCommands.filter((command) => `/${command.id}`.startsWith(input));
}

export function exactCommand(content: string): ComposerCommand | undefined {
  const input = content.trim().toLowerCase();
  return composerCommands.find((command) => input === `/${command.id}`)?.id;
}
