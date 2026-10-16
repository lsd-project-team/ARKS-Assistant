// use 引用需要独立 SVG 文件，避免构建成数据 URL 后无法显示。
import solarSprite from '../../shared/assets/navigation-icons/solar-broken.svg?url&no-inline';

export function NavigationIcon({ kind }: { kind: 'chat' | 'graphs' | 'modules' }) {
  // 图标使用 currentColor，沿用导航的外观、悬停和选中颜色。
  return (
    <svg width={18} height={18} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <use href={`${solarSprite}#${kind}`} />
    </svg>
  );
}
