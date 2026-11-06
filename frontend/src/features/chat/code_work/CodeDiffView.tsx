import { useMemo } from 'react';
import { parseDiffFromFile, type SelectedLineRange } from '@pierre/diffs';
import { FileDiff } from '@pierre/diffs/react';
import { useAppearance } from '../../settings/lib/appearance';
import { SOURCE_THEME, SOURCE_DARK_THEME } from '../../source_reader/lib/editorTheme';
import type { WorkDiff } from './types';

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
  const fileDiff = useMemo(
    () =>
      parseDiffFromFile(
        { name: diff.path, contents: diff.before, cacheKey: `${diff.version}:before` },
        { name: diff.path, contents: diff.after, cacheKey: `${diff.version}:after` },
      ),
    [diff],
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
      // 随外层差异区延伸背景和滚动条，代码行仍保持自然行高。
      unsafeCSS: `
        :host { background: var(--diffs-bg); }
        [data-diff] { flex: 1 0 auto; }
        [data-code] { align-self: stretch; align-content: start; }
      `,
    }),
    [split, dark, onSelect, wrap],
  );
  return <FileDiff fileDiff={fileDiff} options={options} disableWorkerPool />;
}
