import { useWorkspace } from '../lib/store';
import {
  FILES_COLLAPSE_WIDTH,
  FILES_MIN_WIDTH,
  WORKSPACE_COLLAPSE_WIDTH,
  paneWidthLimits,
  type PaneWidths,
} from '../lib/paneLayout';
import { constrainWidth } from '../lib/layoutMotion';
import { useDividerDrag } from '../hooks/useDividerDrag';

function paneWidth(divider: HTMLElement, kind: 'chat' | 'files') {
  return divider
    .parentElement!.querySelector(kind === 'chat' ? '.chat-pane' : '.file-explorer')!
    .getBoundingClientRect().width;
}
function requestedWidth(divider: HTMLElement, kind: 'chat' | 'files', clientX: number) {
  const parent = divider.parentElement!;
  const bounds = parent.getBoundingClientRect();
  return kind === 'chat'
    ? clientX - bounds.left - parent.clientLeft
    : bounds.left + parent.clientLeft + parent.clientWidth - clientX;
}
function widthLimits(divider: HTMLElement, kind: 'chat' | 'files', focused: boolean) {
  const parent = divider.parentElement!;
  const gap = divider.getBoundingClientRect().width;
  const explorer = parent.querySelector('.file-explorer');
  return paneWidthLimits({
    kind,
    parentWidth: parent.clientWidth,
    dividerWidth: gap,
    focused,
    filesOverlay: !!explorer && getComputedStyle(explorer).position === 'absolute',
    filesOpen: useWorkspace.getState().explorerOpen,
    codeOpen: useWorkspace.getState().codeOpen,
  });
}

export function PaneDivider({ kind = 'chat' }: { kind?: 'chat' | 'files' }) {
  const setLayout = useWorkspace((state) => state.setLayout);
  const collapsePane = useWorkspace((state) => state.collapsePane);
  const readingFocused = useWorkspace((state) => state.readingFocused);
  const drag = useDividerDrag();
  function resize(divider: HTMLElement, width: number, restore?: PaneWidths) {
    const parent = divider.parentElement!;
    const { minimum, maximum } = widthLimits(divider, kind, readingFocused);
    const threshold =
      kind === 'files'
        ? FILES_COLLAPSE_WIDTH
        : parent.clientWidth - divider.getBoundingClientRect().width - WORKSPACE_COLLAPSE_WIDTH;
    const collapse = kind === 'files' ? width <= threshold : width >= threshold;
    if (collapse) {
      collapsePane(kind, restore);
      requestAnimationFrame(() =>
        document
          .querySelector<HTMLButtonElement>(
            kind === 'files' && useWorkspace.getState().codeOpen
              ? '[aria-label="切换文件树"]'
              : '.chat-heading [aria-label="工作区"]',
          )
          ?.focus({ preventScroll: true }),
      );
      return;
    }
    const bounded = constrainWidth(width, minimum, maximum);
    setLayout(
      kind === 'chat'
        ? readingFocused
          ? { focusChatRatio: bounded / parent.clientWidth }
          : { chatRatio: bounded / parent.clientWidth }
        : { explorerWidth: bounded },
    );
  }
  return (
    <div
      className={`pane-divider ${kind === 'files' ? 'file-divider' : ''}`}
      role="separator"
      aria-label={kind === 'chat' ? '调整问答和源码宽度' : '调整文件树宽度'}
      aria-orientation="vertical"
      tabIndex={0}
      title="拖动或按方向键调整，继续向右并松手可收起；双击恢复默认宽度"
      onDoubleClick={() =>
        setLayout(
          kind === 'chat'
            ? readingFocused
              ? { focusChatRatio: 0.24 }
              : { chatRatio: 0.36 }
            : { explorerWidth: 0 },
        )
      }
      onPointerDown={(event) => {
        const divider = event.currentTarget;
        const root = divider.closest<HTMLElement>('.app-shell')!;
        const { chatRatio, focusChatRatio, explorerWidth } = useWorkspace.getState();
        const restore = { chatRatio, focusChatRatio, explorerWidth };
        drag.begin(
          event,
          paneWidth(divider, kind),
          requestedWidth(divider, kind, event.clientX),
          kind,
          (next) => {
            // 每帧按当前容器重新计算，窗口缩放也遵守阅读宽度边界。
            const limits = widthLimits(divider, kind, readingFocused);
            const bounded = constrainWidth(next, limits.minimum, limits.maximum);
            root.style.setProperty(
              kind === 'chat' ? '--drag-chat-width' : '--drag-file-width',
              `${bounded}px`,
            );
          },
          (next) => resize(divider, next, restore),
        );
      }}
      onPointerMove={(event) =>
        drag.move(event, requestedWidth(event.currentTarget, kind, event.clientX))
      }
      onPointerUp={(event) => drag.end(event)}
      onPointerCancel={(event) => drag.end(event, true)}
      onLostPointerCapture={(event) => drag.end(event, true)}
      onKeyDown={(event) => {
        if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
        event.preventDefault();
        const width = paneWidth(event.currentTarget, kind);
        const atRightLimit =
          kind === 'files'
            ? width <= FILES_MIN_WIDTH
            : width >= widthLimits(event.currentTarget, kind, readingFocused).maximum - 1;
        resize(
          event.currentTarget,
          event.key === 'ArrowRight' && atRightLimit
            ? kind === 'files'
              ? FILES_COLLAPSE_WIDTH
              : event.currentTarget.parentElement!.clientWidth
            : width + (event.key === 'ArrowLeft' ? -1 : 1) * (kind === 'chat' ? 24 : -24),
        );
      }}
    />
  );
}
