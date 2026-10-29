import { Button, ErrorText } from '../../../shared/ui/ui';
import type { useAgentInstructions } from '../hooks/useAgentInstructions';
import { instructionBytes, MAX_AGENT_INSTRUCTION_BYTES } from '../lib/agentInstructionsDraft';

export function AgentInstructionsPanel({
  controller,
}: {
  controller: ReturnType<typeof useAgentInstructions>;
}) {
  return (
    <section className="agent-instructions-panel" aria-label="全局 agent.md">
      <p>写下希望 AI 长期遵循的回答习惯和工作约定，仅对你的账号生效，适用于所有项目和独立对话。</p>
      <p className="muted">
        保存后用于新启动的问答；正在进行的问答保留原版本。留空保存可停用自定义指令。
      </p>
      {controller.saved.isPending && <p className="muted">正在读取全局指令…</p>}
      {controller.draft && (
        <label>
          agent.md
          <textarea
            aria-label="全局 agent.md 内容"
            rows={17}
            disabled={controller.busy}
            value={controller.draft.content}
            onChange={(event) => controller.setContent(event.target.value)}
            placeholder="例如：默认用中文，先给出结论；需要分析时说明依据和适用条件。"
          />
          <span className="muted">
            {instructionBytes(controller.draft.content).toLocaleString()} /{' '}
            {MAX_AGENT_INSTRUCTION_BYTES.toLocaleString()} 字节
          </span>
        </label>
      )}
      {!!controller.validation && <p role="alert">{controller.validation}</p>}
      <ErrorText error={controller.error || controller.saved.error} reveal={!!controller.error} />
      {!!(controller.error || controller.saved.error) && (
        <Button disabled={controller.busy} onClick={controller.reload}>
          读取最新内容
        </Button>
      )}
      {!!controller.feedback && <p className="success-text">{controller.feedback}</p>}
    </section>
  );
}
