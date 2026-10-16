import { Palette } from 'lucide-react';
import { appearanceModes, useAppearance } from '../lib/appearance';
import { cn } from '../../../shared/ui/ui';
import '../styles/appearance-switch.css';

export function AppearanceSwitch({ className }: { className?: string }) {
  const { mode, setMode } = useAppearance();
  const index = appearanceModes.findIndex((item) => item.id === mode);
  const current = appearanceModes[index];
  const next = appearanceModes[(index + 1) % appearanceModes.length];
  return (
    <button
      type="button"
      className={cn('appearance-switch', className)}
      aria-label="切换外观"
      title={`当前：${current.title}；点击切换为${next.title}`}
      onClick={() => setMode(next.id)}
    >
      <Palette size={17} aria-hidden="true" />
      <span className="nav-copy">外观 · {current.title}</span>
    </button>
  );
}
