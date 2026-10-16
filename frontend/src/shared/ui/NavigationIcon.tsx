// use 引用需要独立 SVG 文件，避免构建成数据 URL 后无法显示。
import solarSprite from '../assets/navigation-icons/solar-broken.svg?url&no-inline';

export function NavigationIcon({
  kind,
  size = 18,
}: {
  kind: 'chat' | 'graphs' | 'modules';
  size?: number;
}) {
  // 导航与页面标题共用图形，通过 currentColor 和尺寸适配所在位置。
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <use href={`${solarSprite}#${kind}`} />
    </svg>
  );
}
