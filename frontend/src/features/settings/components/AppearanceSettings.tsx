import { Check } from 'lucide-react';
import { appearanceModes, useAppearance } from '../lib/appearance';

export function AppearanceSettings() {
  const { mode, setMode } = useAppearance();
  return (
    <section className="appearance-settings">
      <h3>外观视觉模式</h3>
      <p className="muted">选择适合你的阅读外观，切换后立即生效。</p>
      <div className="appearance-options" role="group" aria-label="外观视觉模式">
        {appearanceModes.map((item) => (
          <button
            key={item.id}
            className={`appearance-option ${item.id === mode ? 'selected' : ''}`}
            aria-pressed={item.id === mode}
            onClick={() => setMode(item.id)}
          >
            <span className={`appearance-preview ${item.id}`}>
              <i />
              <i />
              <i />
            </span>
            <strong>
              {item.title}
              {item.id === mode && <Check size={15} />}
            </strong>
            <span>{item.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
