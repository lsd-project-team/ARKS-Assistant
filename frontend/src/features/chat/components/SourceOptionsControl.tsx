import type { SourceOptions } from '../../../shared/types/api';
import { resolvedSources } from '../../settings/lib/sourceOptions';
import '../../settings/styles/source-options.css';

const choices = [
  ['use_deepwiki', 'DeepWiki', '查阅远端架构说明'],
  ['use_knowledge', '知识资料', '检索交接资料、调试记录、项目文档与共享结论，以及已接入的流程说明'],
  ['use_memory', '长期记忆', '带入相关记忆，并允许按设置保存记忆'],
] as const;

export function SourceOptionsControl({
  value,
  onChange,
  disabled = false,
  legend = '本轮知识来源',
  description = '本地源码始终可读，选择要额外使用的资料。',
}: {
  value?: Partial<SourceOptions>;
  onChange: (value: SourceOptions) => void;
  disabled?: boolean;
  legend?: string;
  description?: string;
}) {
  const selected = resolvedSources(value);
  return (
    <fieldset className="source-options" disabled={disabled}>
      <legend>{legend}</legend>
      <p className="muted">{description}</p>
      {choices.map(([key, label, description]) => (
        <label key={key}>
          <input
            type="checkbox"
            checked={selected[key]}
            onChange={(event) => onChange({ ...selected, [key]: event.target.checked })}
          />
          <span>
            {label}
            <small>{description}</small>
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
