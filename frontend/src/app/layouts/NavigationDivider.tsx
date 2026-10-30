import { useWorkspace } from '../state/store';
import {
  NAVIGATION_COLLAPSE_WIDTH,
  NAVIGATION_MIN_WIDTH,
  navigationLayout,
} from './navigationLayout';
import { constrainWidth, settledWidth } from './layoutMotion';
import { useDividerDrag } from './hooks/useDividerDrag';

export function NavigationDivider({
  width,
  maximumWidth,
}: {
  width: number;
  maximumWidth: number;
}) {
  const setLayout = useWorkspace((state) => state.setLayout);
  const drag = useDividerDrag();
  function resize(requested: number, restoreWidth = useWorkspace.getState().navigationWidth) {
    const result = settledWidth(
      requested,
      NAVIGATION_MIN_WIDTH,
      maximumWidth,
      NAVIGATION_COLLAPSE_WIDTH,
    );
    setLayout(
      result === null
        ? { collapsed: true, navigationWidth: restoreWidth }
        : { navigationWidth: result },
    );
  }
  const requested = (divider: HTMLElement, clientX: number) =>
    clientX - divider.parentElement!.getBoundingClientRect().left;
  return (
    <div
      className="navigation-divider"
      role="separator"
      aria-label="调整导航栏宽度"
      aria-orientation="vertical"
      aria-valuemin={NAVIGATION_MIN_WIDTH}
      aria-valuemax={maximumWidth}
      aria-valuenow={width}
      tabIndex={0}
      title="拖动调整宽度，向左拖并松手可收起；方向键调整，双击恢复默认宽度"
      onDoubleClick={() => setLayout({ navigationWidth: 0 })}
      onPointerDown={(event) => {
        const root = event.currentTarget.closest<HTMLElement>('.app-shell')!;
        const restoreWidth = useWorkspace.getState().navigationWidth;
        const actual = event.currentTarget.parentElement!.getBoundingClientRect().width;
        drag.begin(
          event,
          actual,
          requested(event.currentTarget, event.clientX),
          'navigation',
          (next) =>
            root.style.setProperty(
              '--drag-navigation-width',
              // 指针仍可越过收起阈值，但展开内容始终保留可读宽度。
              `${constrainWidth(next, NAVIGATION_MIN_WIDTH, navigationLayout(0, window.innerWidth).maximumWidth)}px`,
            ),
          (next) => resize(next, restoreWidth),
        );
      }}
      onPointerMove={(event) => drag.move(event, requested(event.currentTarget, event.clientX))}
      onPointerUp={(event) => drag.end(event)}
      onPointerCancel={(event) => drag.end(event, true)}
      onLostPointerCapture={(event) => drag.end(event, true)}
      onKeyDown={(event) => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        resize(
          event.key === 'Home' || (event.key === 'ArrowLeft' && width <= NAVIGATION_MIN_WIDTH)
            ? NAVIGATION_COLLAPSE_WIDTH
            : event.key === 'End'
              ? maximumWidth
              : width + (event.key === 'ArrowLeft' ? -24 : 24),
        );
      }}
    />
  );
}
