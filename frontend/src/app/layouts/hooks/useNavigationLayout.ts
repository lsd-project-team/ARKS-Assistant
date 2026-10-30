import { useEffect, useState } from 'react';
import { navigationLayout } from '../navigationLayout';

export function useNavigationLayout(savedWidth: number) {
  const [viewport, setViewport] = useState(window.innerWidth);
  useEffect(() => {
    const updateViewport = () => setViewport(window.innerWidth);
    window.addEventListener('resize', updateViewport);
    return () => window.removeEventListener('resize', updateViewport);
  }, []);
  // 缩小窗口只限制显示宽度，不覆盖用户在大窗口保存的偏好。
  return navigationLayout(savedWidth, viewport);
}
