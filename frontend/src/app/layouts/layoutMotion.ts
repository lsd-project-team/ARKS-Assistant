export type LayoutSizes = {
  navigation: number;
  chat: number;
  files: number;
  content: number;
  composer: number;
  contentOffset: number;
  composerOffset: number;
  composerInset: number;
};

const snapshots = new WeakMap<HTMLElement, LayoutSizes>();
const animations = new WeakMap<HTMLElement, () => void>();
const properties = {
  navigation: '--motion-navigation-width',
  chat: '--motion-chat-width',
  files: '--motion-file-width',
  content: '--motion-content-width',
  composer: '--motion-composer-width',
  contentOffset: '--motion-content-offset',
  composerOffset: '--motion-composer-offset',
  composerInset: '--motion-composer-inset',
} as const;

export function measureLayout(root: HTMLElement): LayoutSizes {
  const width = (selector: string) =>
    root.querySelector<HTMLElement>(selector)?.getBoundingClientRect().width || 0;
  const chat = root.querySelector<HTMLElement>('.chat-pane')!;
  const content = root.querySelector<HTMLElement>('.chat-content')!;
  const composer = root.querySelector<HTMLElement>('.composer-area')!;
  const scroll = root.querySelector<HTMLElement>('.chat-scroll')!;
  const scrollbar = scroll.offsetWidth - scroll.clientWidth;
  const gutter = getComputedStyle(scroll).scrollbarGutter.includes('both-edges')
    ? scrollbar / 2
    : scrollbar;
  return {
    navigation: width('.app-navigation'),
    chat: width('.chat-pane'),
    files: width('.file-explorer'),
    content: content.getBoundingClientRect().width,
    composer: composer.getBoundingClientRect().width,
    // 动画期间统一滚动条两侧留白，补偿起止布局原本不同的内边距。
    contentOffset:
      content.getBoundingClientRect().left - chat.getBoundingClientRect().left - gutter,
    composerOffset: composer.getBoundingClientRect().left - chat.getBoundingClientRect().left,
    composerInset: parseFloat(getComputedStyle(composer).paddingLeft),
  };
}

export function rememberLayout(root: HTMLElement) {
  snapshots.set(root, measureLayout(root));
}

export function takeLayoutSnapshot(root: HTMLElement) {
  const snapshot = snapshots.get(root);
  snapshots.delete(root);
  return snapshot;
}

export function stopLayoutMotion(root: HTMLElement) {
  animations.get(root)?.();
}

function layoutSettled(root: HTMLElement, complete: () => void) {
  complete();
  root.dispatchEvent(new Event('workspace-layout-settled'));
}

export function animateLayout(
  root: HTMLElement,
  from: LayoutSizes,
  to: LayoutSizes,
  complete: () => void = () => {},
) {
  stopLayoutMotion(root);
  const keys = Object.keys(properties) as (keyof LayoutSizes)[];
  if (
    matchMedia('(prefers-reduced-motion: reduce)').matches ||
    keys.every((key) => Math.abs(from[key] - to[key]) < 1)
  ) {
    layoutSettled(root, complete);
    return;
  }
  let frame = 0;
  const started = performance.now();
  const clear = () => {
    cancelAnimationFrame(frame);
    delete root.dataset.layoutMoving;
    keys.forEach((key) => root.style.removeProperty(properties[key]));
    animations.delete(root);
  };
  animations.set(root, clear);
  root.dataset.layoutMoving = 'true';
  const update = (now: number) => {
    // 拖动直接跟手；只有松手吸附和按钮开关使用短促的减速过渡。
    const progress = Math.min(1, (now - started) / 220);
    const eased = 1 - Math.pow(1 - progress, 3);
    keys.forEach((key) =>
      root.style.setProperty(properties[key], `${from[key] + (to[key] - from[key]) * eased}px`),
    );
    if (progress < 1) frame = requestAnimationFrame(update);
    else {
      clear();
      layoutSettled(root, complete);
    }
  };
  update(started);
}

export function settledWidth(
  requested: number,
  minimum: number,
  maximum: number,
  threshold: number,
) {
  return requested <= threshold ? null : constrainWidth(requested, minimum, maximum);
}

export function constrainWidth(requested: number, minimum: number, maximum: number) {
  return Math.min(Math.max(minimum, maximum), Math.max(minimum, requested));
}
