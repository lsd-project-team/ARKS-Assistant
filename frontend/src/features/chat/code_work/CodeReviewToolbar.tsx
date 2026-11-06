import {
  ArrowLeft,
  Columns2,
  FoldVertical,
  Play,
  RefreshCw,
  Square,
  UnfoldVertical,
  WrapText,
  X,
} from 'lucide-react';
import { Button } from '../../../shared/ui/ui';
import { CodeWorkMenu } from './CodeWorkMenu';
import { ReviewLineCounts } from './CodeReviewFile';
import { VerificationSummary } from './VerificationSummary';
import type { WorkStatus, WorkSummary } from './types';

export function CodeReviewToolbar({
  title,
  onBack,
  status,
  runId,
  onScope,
  summary,
  view,
  onView,
  allCollapsed,
  onToggleAll,
  onRefresh,
  onClose,
  onDetails,
  verifying,
  blocked,
  verifyPending,
  cancelPending,
  onVerify,
  onCancel,
  items,
}: {
  title?: string;
  onBack: () => void;
  status?: WorkStatus;
  runId: string;
  onScope: (id: string) => void;
  summary?: WorkSummary;
  view: { split: boolean; wrap: boolean };
  onView: (view: { split: boolean; wrap: boolean }) => void;
  allCollapsed: boolean;
  onToggleAll: () => void;
  onRefresh: () => void;
  onClose: () => void;
  onDetails: () => void;
  verifying: boolean;
  blocked: boolean;
  verifyPending: boolean;
  cancelPending: boolean;
  onVerify: () => void;
  onCancel: () => void;
  items: Parameters<typeof CodeWorkMenu>[0]['items'];
}) {
  // 历史按真实运行编号去重；没有逐轮记录时只提供累计修改，避免伪造“上一轮”。
  const turns = [...(status?.history || [])]
    .sort((a, b) => b.revision - a.revision)
    .filter(
      (turn, index, rows) =>
        turn.run_id && rows.findIndex((row) => row.run_id === turn.run_id) === index,
    );
  return (
    <div className="code-work-primary code-review-topbar">
      {title ? (
        <div className="code-review-page-title">
          <Button onClick={onBack} aria-label="返回变更" title="返回变更">
            <ArrowLeft size={15} />
          </Button>
          <strong>{title}</strong>
        </div>
      ) : (
        <div
          className="code-review-scope-pill"
          title={runId ? '历史快照，只读查看' : '当前副本的全部待合入修改'}
        >
          <select
            aria-label="变更范围"
            value={runId}
            onChange={(event) => onScope(event.target.value)}
          >
            <option value="">全部待合入</option>
            {turns.map((turn, index) => (
              <option key={turn.run_id} value={turn.run_id}>
                {index === 0 ? '上一轮' : `轮次 · 版本 ${turn.revision}`}
              </option>
            ))}
            {runId && !turns.some((turn) => turn.run_id === runId) && (
              <option value={runId}>本轮修改</option>
            )}
          </select>
          {summary && <ReviewLineCounts {...summary} />}
        </div>
      )}
      <div className="code-review-top-actions" role="group" aria-label="变更操作">
        <CodeWorkMenu items={items} />
        <button
          className="code-review-icon"
          type="button"
          aria-label="刷新变更"
          title="刷新变更"
          onClick={onRefresh}
        >
          <RefreshCw size={14} />
        </button>
        {!title && (
          <>
            <button
              className="code-review-icon"
              type="button"
              aria-label={allCollapsed ? '展开全部文件' : '收起全部文件'}
              title={allCollapsed ? '展开全部文件' : '收起全部文件'}
              onClick={onToggleAll}
            >
              {allCollapsed ? <UnfoldVertical size={15} /> : <FoldVertical size={15} />}
            </button>
            <button
              className="code-review-icon"
              type="button"
              aria-label="自动换行"
              title="自动换行"
              aria-pressed={view.wrap}
              onClick={() => onView({ ...view, wrap: !view.wrap })}
            >
              <WrapText size={15} />
            </button>
            <button
              className="code-review-icon"
              type="button"
              aria-label="左右对照"
              title={view.split ? '切换为统一差异' : '切换为左右对照'}
              aria-pressed={view.split}
              onClick={() => onView({ ...view, split: !view.split })}
            >
              <Columns2 size={15} />
            </button>
          </>
        )}
        {status?.exists && !runId && (
          <>
            <VerificationSummary inline status={status} onDetails={onDetails} />
            <button
              className="code-review-icon"
              type="button"
              aria-label="编译与仿真验证"
              title="编译与仿真验证"
              disabled={blocked || verifyPending}
              onClick={onVerify}
            >
              <Play size={14} />
            </button>
          </>
        )}
        {verifying && (
          <button
            className="code-review-icon"
            type="button"
            aria-label="停止验证"
            title="停止验证"
            disabled={cancelPending}
            onClick={onCancel}
          >
            <Square size={14} />
          </button>
        )}
        <button
          className="code-review-icon"
          type="button"
          aria-label="关闭代码变更"
          title="关闭代码变更"
          onClick={onClose}
        >
          <X size={15} />
        </button>
      </div>
    </div>
  );
}
