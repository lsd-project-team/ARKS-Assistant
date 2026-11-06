import { Component, lazy, Suspense, useCallback, useEffect, useState, type ReactNode } from 'react';
import type { SelectedLineRange } from '@pierre/diffs';
import { Button } from '../../../shared/ui/ui';
import type { WorkDiff, WorkHunk } from './types';

const CodeDiffView = lazy(() => import('./CodeDiffView'));
class DiffBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

export function ReviewDiff({
  diff,
  disabled,
  onRevertHunk,
  onReview,
}: {
  diff: WorkDiff;
  disabled?: boolean;
  onRevertHunk?: (hunk: WorkHunk) => void;
  onReview?: (request: string) => void;
}) {
  const [split, setSplit] = useState(false);
  const [selected, setSelected] = useState<SelectedLineRange | null>(null);
  const [comment, setComment] = useState('');
  const [confirm, setConfirm] = useState('');
  const [selectionHint, setSelectionHint] = useState('');
  const onSelect = useCallback((range: SelectedLineRange | null) => {
    const mixed = range?.endSide && range.endSide !== (range.side || 'additions');
    setSelected(mixed ? null : range);
    setSelectionHint(mixed ? '请在修改前或修改后的同一侧选择代码行。' : '');
  }, []);
  useEffect(() => {
    setSelected(null);
    setComment('');
    setConfirm('');
  }, [diff.path, diff.version, diff.run_id]);
  const fallback = <pre aria-label="代码差异">{diff.diff}</pre>;
  const requestReview = () => {
    if (!selected || !comment.trim() || !onReview) return;
    const start = Math.min(selected.start, selected.end),
      end = Math.max(selected.start, selected.end);
    const side = selected.side === 'deletions' ? '修改前' : '修改后';
    const content = (side === '修改前' ? diff.before : diff.after)
      .split('\n')
      .slice(start - 1, Math.min(end, start + 79))
      .join('\n');
    onReview(
      `请先读取当前副本核对后处理以下差异反馈。\n文件：${diff.path}\n所查看版本：${diff.version}${diff.run_id ? `（历史轮次 ${diff.run_id}）` : ''}\n${side}第 ${start}–${end} 行：\n\`\`\`csharp\n${content}\n\`\`\`\n要求：${comment.trim()}`,
    );
  };
  return (
    <>
      <div className="code-review-toolbar" role="group" aria-label="差异显示方式">
        <Button aria-pressed={!split} onClick={() => setSplit(false)}>
          统一差异
        </Button>
        <Button aria-pressed={split} onClick={() => setSplit(true)}>
          左右对照
        </Button>
        {diff.historical && <span className="muted">历史快照，只读查看</span>}
      </div>
      <div className="code-review-highlight" aria-label="带行号的代码差异">
        <DiffBoundary key={`${diff.path}:${diff.version}`} fallback={fallback}>
          <Suspense fallback={fallback}>
            <CodeDiffView diff={diff} split={split} onSelect={onSelect} />
          </Suspense>
        </DiffBoundary>
      </div>
      {!!diff.hunks?.length && (
        <div className="code-review-hunks" aria-label="修改块">
          {diff.hunks.map((hunk, index) => (
            <div key={hunk.id}>
              <span>
                修改块 {index + 1} · 新版 L{hunk.new_start}–
                {hunk.new_start + Math.max(1, hunk.new_lines) - 1}
              </span>
              {onReview && (
                <Button
                  onClick={() =>
                    onSelect(
                      hunk.new_lines
                        ? {
                            start: hunk.new_start,
                            end: hunk.new_start + hunk.new_lines - 1,
                            side: 'additions',
                          }
                        : {
                            start: hunk.old_start,
                            end: hunk.old_start + Math.max(1, hunk.old_lines) - 1,
                            side: 'deletions',
                          },
                    )
                  }
                >
                  反馈此处
                </Button>
              )}
              {onRevertHunk && !diff.historical && (
                <Button disabled={disabled} onClick={() => setConfirm(hunk.id)}>
                  撤销此块
                </Button>
              )}
              {confirm === hunk.id && (
                <span className="code-hunk-confirm" role="alert">
                  确认撤销这个修改块？
                  <Button
                    disabled={disabled}
                    onClick={() => {
                      onRevertHunk?.(hunk);
                      setConfirm('');
                    }}
                  >
                    确认撤销
                  </Button>
                  <Button onClick={() => setConfirm('')}>保留</Button>
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      {onReview && (
        <div className="code-review-comment">
          {selectionHint && <p className="muted">{selectionHint}</p>}
          <label>
            差异反馈
            {selected
              ? ` · ${selected.side === 'deletions' ? '修改前' : '修改后'} L${selected.start}–${selected.end}`
              : ' · 点击行号选择范围'}
            <textarea
              aria-label="差异反馈说明"
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              maxLength={2000}
              placeholder="说明这段代码需要如何调整"
            />
          </label>
          <Button disabled={!selected || !comment.trim()} onClick={requestReview}>
            带入聊天输入框
          </Button>
        </div>
      )}
    </>
  );
}
