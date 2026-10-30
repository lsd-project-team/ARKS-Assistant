import type { ErrorFeedback } from '../../../shared/types/api';
import { Button } from '../../../shared/ui/ui';

export function RunFeedback({
  feedback,
  onSettings,
  onContext,
}: {
  feedback: ErrorFeedback;
  onSettings: (tab: 'model' | 'mcp') => void;
  onContext: () => void;
}) {
  return (
    <div
      className={`run-feedback ${feedback.code === 'mcp_connection' ? 'notice' : ''}`}
      role="alert"
    >
      <p>{feedback.text}</p>
      {feedback.hint && <small>{feedback.hint}</small>}
      {feedback.action === 'settings' && (
        <Button onClick={() => onSettings('model')}>检查模型设置</Button>
      )}
      {feedback.action === 'mcp_settings' && (
        <Button onClick={() => onSettings('mcp')}>检查 MCP 设置</Button>
      )}
      {feedback.action === 'context' && <Button onClick={onContext}>查看上下文</Button>}
    </div>
  );
}
