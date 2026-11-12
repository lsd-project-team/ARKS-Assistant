export type ComposerCommand = 'context' | 'compact' | '记录问题';

export const composerCommands: ReadonlyArray<{
  id: ComposerCommand;
  label: string;
}> = [
  { id: 'context', label: '查看上下文' },
  { id: 'compact', label: '记录上下文' },
  {
    id: '记录问题',
    label: '记录问题与经验',
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
