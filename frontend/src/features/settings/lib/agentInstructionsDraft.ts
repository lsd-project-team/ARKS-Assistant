export const MAX_AGENT_INSTRUCTION_BYTES = 32 * 1024;

export interface AgentInstructions {
  name: string;
  owner_id: string | null;
  content: string;
  version: string;
  updated_at: string | null;
}

export function instructionBytes(content: string) {
  return new TextEncoder().encode(content).length;
}

export function validateAgentInstructions(content: string) {
  return instructionBytes(content) > MAX_AGENT_INSTRUCTION_BYTES
    ? '全局 agent.md 最多 32 KiB，请精简后保存'
    : '';
}
