import type { AnalysisSettings, Settings } from '../types';
import { defaultAnalysis } from '../lib/settingsDraft';
import { Select } from './Select';

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
      {(
        [
          ['standard_calls', '普通工具预算', 8, 128],
          ['deep_calls', '深度工具预算', 16, 192],
          ['verification_reserve', '关键源码复核预留', 2, 32],
          ['long_output_tokens', '深度分析回复 token 上限', 1024, 65536],
          ['max_continuations', '自动续写次数', 0, 2],
        ] as const
      ).map(([key, label, min, max]) => (
        <label key={key}>
          {label}
          <input
            type="number"
            min={min}
            max={max}
            value={value[key]}
            onChange={(event) => change(key, Number(event.target.value))}
          />
        </label>
      ))}
      <p className="muted">
        深度分析用于项目进度和完整流程。复核预留包含在总预算中，同版本已读源码复用不重复占用额度。回复达到长度上限时自动续写，最多两次。
      </p>
    </details>
  );
}
