import { useEffect, useMemo, useRef, useState } from 'react';
import { parseDiffFromFile, type SelectedLineRange } from '@pierre/diffs';
import { FileDiff } from '@pierre/diffs/react';
import { useAppearance } from '../../settings/lib/appearance';
import { SOURCE_THEME, SOURCE_DARK_THEME } from '../../source_reader/lib/editorTheme';
import type { WorkDiff } from './types';

function parseReviewDiff(diff: WorkDiff, context: number) {
  return parseDiffFromFile(
    { name: diff.path, contents: diff.before, cacheKey: `${diff.version}:before:${context}` },
    { name: diff.path, contents: diff.after, cacheKey: `${diff.version}:after:${context}` },
    { context },
  );
}

export default function CodeDiffView({
  diff,
  split,
  onSelect,
  wrap = false,
}: {
  diff: WorkDiff;
  split: boolean;
  onSelect: (range: SelectedLineRange | null) => void;
  wrap?: boolean;
}) {
  const dark = useAppearance((state) => state.mode === 'dark');
  const root = useRef<HTMLDivElement>(null);
  const [context, setContext] = useState(3);
  const baseDiff = useMemo(() => parseReviewDiff(diff, 3), [diff]);
  useEffect(() => {
    const pane = root.current?.closest('.code-work-pane');
    const body = pane?.querySelector('.code-work-body');
    if (!body || !baseDiff.hunks.length) return;
    const resize = () => {
      const header = root.current
        ?.closest('.code-review-file')
        ?.querySelector('.code-review-file-header');
      const topbar = pane?.querySelector('.code-review-topbar');
      const host = root.current?.querySelector('diffs-container');
      const lineHeight = host ? parseFloat(getComputedStyle(host).lineHeight) || 20 : 20;
      const height = body.clientHeight - (header?.clientHeight || 0) - (topbar?.clientHeight || 0);
      const rows = Math.ceil(height / lineHeight);
      const visible = baseDiff.hunks.reduce(
        (sum, hunk) => sum + (split ? hunk.splitLineCount : hunk.unifiedLineCount),
        0,
      );
      // 少量修改用相邻源码填充阅读空间；长差异继续紧凑展示，限制展开量。
      setContext(
        Math.min(48, 3 + Math.max(0, Math.ceil((rows - visible) / (baseDiff.hunks.length * 2)))),
      );
    };
    resize();
    const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : undefined;
    observer?.observe(body);
    return () => observer?.disconnect();
  }, [baseDiff, split]);
  const fileDiff = useMemo(
    () => (context === 3 ? baseDiff : parseReviewDiff(diff, context)),
    [baseDiff, diff, context],
  );
  const options = useMemo(
    () => ({
      diffStyle: split ? ('split' as const) : ('unified' as const),
      theme: dark ? SOURCE_DARK_THEME : SOURCE_THEME,
      themeType: dark ? ('dark' as const) : ('light' as const),
      disableFileHeader: true,
      enableLineSelection: true,
      onLineSelected: onSelect,
      overflow: wrap ? ('wrap' as const) : ('scroll' as const),
      hunkSeparators: 'line-info' as const,
      lineDiffType: 'word-alt' as const,
    }),
    [split, dark, onSelect, wrap],
  );
  return (
    <div ref={root}>
      <FileDiff fileDiff={fileDiff} options={options} disableWorkerPool />
    </div>
  );
}
