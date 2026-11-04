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
}: {
  diff: WorkDiff;
  split: boolean;
  onSelect: (range: SelectedLineRange | null) => void;
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
      overflow: 'scroll' as const,
    }),
    [split, dark, onSelect],
  );
  return <FileDiff fileDiff={fileDiff} options={options} disableWorkerPool />;
}
