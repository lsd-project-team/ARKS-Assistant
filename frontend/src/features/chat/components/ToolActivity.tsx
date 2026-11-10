import { Check, ChevronDown, LoaderCircle, CircleAlert, CircleMinus } from 'lucide-react';
import type { ToolEvent } from '../../../shared/types/api';
import { toolLabel } from '../lib/toolLabels';
import { toolState, toolSummary } from '../lib/runCompletion';

const stateLabels = { skipped: '未执行', failed: '执行失败', success: '已完成', pending: '进行中' };

export function ToolActivity({
  tools,
  showSummary = true,
}: {
  tools: ToolEvent[];
  showSummary?: boolean;
}) {
  if (!tools.length) return null;
  return (
    <div className="tool-activity">
      {showSummary && <p className="muted">{toolSummary(tools)}</p>}
      {tools.map((tool) => (
        <details key={tool.id} className="tool-call-card" data-state={toolState(tool)}>
          <summary>
            {toolState(tool) === 'skipped' ? (
              <CircleMinus size={12} />
            ) : toolState(tool) === 'failed' ? (
              <CircleAlert size={12} />
            ) : toolState(tool) === 'success' ? (
              <Check size={12} />
            ) : (
              <LoaderCircle size={12} className="spin" />
            )}
            <span className="tool-call-name" title={tool.name}>
              {toolLabel(tool.name)}
              {toolLabel(tool.name) !== tool.name && <small>{tool.name}</small>}
            </span>
            <span className="tool-call-status">{stateLabels[toolState(tool)]}</span>
            <ChevronDown size={12} />
          </summary>
          <div className="muted">
            {toolState(tool) === 'skipped'
              ? tool.skip_reason === 'verification_reserved'
                ? '未执行：剩余额度用于关键复核'
                : '未执行：达到检索上限'
              : toolState(tool) === 'failed'
                ? '执行失败'
                : toolState(tool) === 'success'
                  ? `已完成${tool.cached ? ' · 复用已读源码' : ''}`
                  : '进行中'}
          </div>
          <details>
            <summary className="muted">查看调用详情</summary>
            <p className="tool-detail-label">调用参数</p>
            <pre>{JSON.stringify(tool.arguments, null, 2) ?? '未提供参数'}</pre>
            {tool.result !== undefined && (
              <>
                <p className="tool-detail-label">执行结果</p>
                <pre>{tool.result || '（空结果）'}</pre>
              </>
            )}
          </details>
        </details>
      ))}
    </div>
  );
}
