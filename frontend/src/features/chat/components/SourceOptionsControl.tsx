import type { SourceOptions } from '../../../shared/types/api';
import { resolvedSources } from '../../settings/lib/sourceOptions';
import '../../settings/styles/source-options.css';

const choices = [
  ['use_deepwiki', 'DeepWiki', '查阅远端架构说明'],
  ['use_knowledge', '问题与经验', '检索历史问题、处理办法和经验记录'],
  ['use_memory', '长期记忆', '带入相关记忆，并允许按设置保存记忆'],
] as const;

export function SourceOptionsControl({
  value,
  onChange,
  disabled = false,
  legend = '本轮知识来源',
  description = '本地源码始终可读，选择要额外使用的资料。',
  compact = false,
}: {
  value?: Partial<SourceOptions>;
  onChange: (value: SourceOptions) => void;
  disabled?: boolean;
  legend?: string;
  description?: string;
  compact?: boolean;
}) {
  const selected = resolvedSources(value);
  return (
    <fieldset className="source-options" disabled={disabled}>
      <legend>{legend}</legend>
      {!compact && <p className="muted">{description}</p>}
      {choices.map(([key, label, description]) => (
        <label key={key} title={compact ? description : undefined}>
          <input
            type="checkbox"
            checked={selected[key]}
            onChange={(event) => onChange({ ...selected, [key]: event.target.checked })}
          />
          <span>
            {label}
            {!compact && <small>{description}</small>}
          </span>
        </label>
      ))}
      <div className="source-options-presets">
        <button
          type="button"
          onClick={() => onChange({ use_deepwiki: false, use_knowledge: false, use_memory: false })}
        >
          仅本地源码
        </button>
        <button
          type="button"
          onClick={() => onChange({ use_deepwiki: true, use_knowledge: true, use_memory: true })}
        >
          使用全部资料
        </button>
      </div>
    </fieldset>
  );
}
