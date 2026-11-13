import type { AnalysisSettings, Settings } from '../../../shared/types/api';
import { defaultAnalysis } from '../lib/settingsDraft';
import { Select } from '../../../shared/ui/Select';

export function AnalysisSettingsPanel({
  settings,
  onChange,
}: {
  settings: Settings;
  onChange: (settings: Settings) => void;
}) {
  const value = { ...defaultAnalysis, ...settings.analysis };
  const change = <K extends keyof AnalysisSettings>(key: K, next: AnalysisSettings[K]) =>
    onChange({ ...settings, analysis: { ...value, [key]: next } });
  return (
    <details className="analysis-settings">
      <summary>分析与回复完整性</summary>
      <label>
        分析模式
        <Select
          aria-label="分析模式"
          value={value.mode}
          onValueChange={(next) => change('mode', next as AnalysisSettings['mode'])}
        >
          <option value="auto">自动识别问题范围</option>
          <option value="standard">普通分析</option>
          <option value="deep">深度分析</option>
        </Select>
      </label>
    </details>
  );
}
