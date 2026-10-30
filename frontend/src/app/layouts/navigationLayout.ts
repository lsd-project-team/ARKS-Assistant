export const NAVIGATION_MIN_WIDTH = 220;
export const NAVIGATION_MAX_WIDTH = 360;
export const NAVIGATION_COLLAPSE_WIDTH = 180;

export function navigationLayout(savedWidth: number, viewport: number) {
  // 大窗口至少留出七成空间给正文；窄屏浮层沿用右侧留白。
  const maximumWidth = Math.max(
    NAVIGATION_MIN_WIDTH,
    Math.min(
      NAVIGATION_MAX_WIDTH,
      // 桌面三栏至少保留问答、源码各 320px 和文件栏 160px，以及两条分界线。
      viewport > 1100 ? Math.min(Math.floor(viewport * 0.3), viewport - 802) : viewport - 24,
    ),
  );
  const defaultWidth = viewport > 1100 && viewport <= 1400 ? 232 : 252;
  const width = Math.min(maximumWidth, Math.max(NAVIGATION_MIN_WIDTH, savedWidth || defaultWidth));
  return { width, maximumWidth };
}
