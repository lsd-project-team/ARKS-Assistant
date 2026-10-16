import { Check, ChevronDown, LoaderCircle, CircleAlert, CircleMinus } from 'lucide-react';
import type { ToolEvent } from '../../../shared/types/api';
import { toolLabel } from '../lib/toolLabels';
import { toolState, toolSummary } from '../lib/runCompletion';

export function ToolActivity({ tools }: { tools: ToolEvent[] }) {
  if (!tools.length) return null;
  return (
    <div className="tool-activity">
      <p className="muted">{toolSummary(tools)}</p>
      {tools.map((tool) => (
        <details key={tool.id}>
          <summary>
            {toolState(tool) === 'skipped' ? (
              <CircleMinus size={12} />
            ) : toolState(tool) === 'failed' ? (
              <CircleAlert size={12} />
            ) : tool.result !== undefined ? (
              <Check size={12} />
            ) : (
              <LoaderCircle size={12} className="spin" />
            )}
            <span>{toolLabel(tool.name)}</span>
            <ChevronDown size={12} />
          </summary>
          <div className="muted">
            {toolState(tool) === 'skipped'
              ? tool.skip_reason === 'verification_reserved'
                ? '未执行：剩余额度用于关键复核'
                : '未执行：达到检索上限'
              : toolState(tool) === 'failed'
                ? '执行失败'
                : tool.result !== undefined
                  ? `已完成${tool.cached ? ' · 复用已读源码' : ''}`
                  : '进行中'}
          </div>
          <details>
            <summary className="muted">查看调用详情</summary>
            <pre>{JSON.stringify(tool.arguments, null, 2)}</pre>
            {tool.result && <pre>{tool.result}</pre>}
          </details>
        </details>
      ))}
    </div>
  );
}
